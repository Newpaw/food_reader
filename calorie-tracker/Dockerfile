FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /uvx /bin/
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/nginx /var/run \
    && chown -R www-data:www-data /var/log/nginx /var/run

COPY pyproject.toml uv.lock README.md ./
# Resolve the exact Pillow security pin even when the checked-in lock file is from an older release.
RUN uv sync --no-install-project

COPY calorie-tracker ./calorie-tracker
RUN mkdir -p /app/calorie-tracker/backend/uploads \
    && chmod 700 /app/calorie-tracker/backend/uploads \
    && chmod +x /app/calorie-tracker/start.sh
RUN cp /app/calorie-tracker/nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000 8080
ENTRYPOINT ["/app/calorie-tracker/start.sh"]
