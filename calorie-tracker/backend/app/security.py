import json
import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any


ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


class SecurityMiddleware:
    """Apply request-size limits, lightweight rate limiting, and security headers.

    The limiter is intentionally in-memory. It protects a single-process deployment
    without adding infrastructure and can later be replaced by a Redis-backed
    implementation when the application is scaled horizontally.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int,
        auth_limit: int,
        auth_window_seconds: int,
        analysis_limit: int,
        analysis_window_seconds: int,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.auth_limit = auth_limit
        self.auth_window_seconds = auth_window_seconds
        self.analysis_limit = analysis_limit
        self.analysis_window_seconds = analysis_window_seconds
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def _client_ip(scope: dict[str, Any]) -> str:
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        forwarded = headers.get(b"x-forwarded-for")
        if forwarded:
            return forwarded.decode("latin-1").split(",", 1)[0].strip()
        client = scope.get("client")
        return str(client[0]) if client else "unknown"

    def _rate_limit(self, scope: dict[str, Any]) -> tuple[str, int, int] | None:
        if scope.get("method") != "POST":
            return None

        path = scope.get("path", "")
        if path in {"/auth/login", "/auth/register"}:
            return "auth", self.auth_limit, self.auth_window_seconds
        if path in {"/me/meals", "/me/meals/text"} or path.endswith("/reanalyze"):
            return "analysis", self.analysis_limit, self.analysis_window_seconds
        return None

    def _is_rate_limited(self, scope: dict[str, Any]) -> tuple[bool, int]:
        rule = self._rate_limit(scope)
        if rule is None:
            return False, 0

        bucket_name, limit, window_seconds = rule
        if limit <= 0:
            return False, 0

        now = time.monotonic()
        key = (bucket_name, self._client_ip(scope))
        with self._lock:
            timestamps = self._requests[key]
            cutoff = now - window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                return True, retry_after
            timestamps.append(now)
        return False, 0

    @staticmethod
    async def _json_response(
        send: Callable[[dict[str, Any]], Awaitable[None]],
        status_code: int,
        detail: str,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]
        if extra_headers:
            headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _read_body(
        self,
        receive: Callable[[], Awaitable[dict[str, Any]]],
    ) -> bytes | None:
        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_body_bytes:
                return None
            chunks.append(chunk)
            if not message.get("more_body", False):
                return b"".join(chunks)

    @staticmethod
    def _secure_send(send: Callable[[dict[str, Any]], Awaitable[None]]):
        async def wrapped(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                names = {key.lower() for key, _ in headers}
                additions = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"SAMEORIGIN",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"camera=(self), microphone=(self), geolocation=()",
                    b"cache-control": b"no-store",
                }
                for key, value in additions.items():
                    if key not in names:
                        headers.append((key, value))
                message["headers"] = headers
            await send(message)

        return wrapped

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        secure_send = self._secure_send(send)
        limited, retry_after = self._is_rate_limited(scope)
        if limited:
            await self._json_response(
                secure_send,
                429,
                "Too many requests. Please try again later.",
                [(b"retry-after", str(retry_after).encode("ascii"))],
            )
            return

        if scope.get("method") in {"POST", "PUT", "PATCH"}:
            body = await self._read_body(receive)
            if body is None:
                await self._json_response(secure_send, 413, "Request body is too large.")
                return

            delivered = False

            async def replay_receive() -> dict[str, Any]:
                nonlocal delivered
                if delivered:
                    return {"type": "http.request", "body": b"", "more_body": False}
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay_receive, secure_send)
            return

        await self.app(scope, receive, secure_send)
