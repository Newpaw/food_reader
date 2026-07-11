from __future__ import annotations

import io
import uuid
import warnings
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .settings import settings


ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
READ_CHUNK_SIZE = 1024 * 1024


async def _read_limited(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image is too large.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    return data


def _decode_and_normalize(data: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(io.BytesIO(data), formats=list(ALLOWED_FORMATS))
            source.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(status_code=400, detail="Unsupported or invalid image.") from exc

    if source.format not in ALLOWED_FORMATS:
        source.close()
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported.")

    width, height = source.size
    if width <= 0 or height <= 0 or width * height > settings.MAX_IMAGE_PIXELS:
        source.close()
        raise HTTPException(status_code=400, detail="Image dimensions are not allowed.")

    try:
        normalized = ImageOps.exif_transpose(source)
        if getattr(normalized, "is_animated", False):
            normalized.seek(0)
        normalized = normalized.convert("RGB")
        normalized.thumbnail(
            (settings.MAX_IMAGE_DIMENSION, settings.MAX_IMAGE_DIMENSION),
            Image.Resampling.LANCZOS,
        )
        return normalized.copy()
    finally:
        source.close()


async def store_private_meal_image(upload: UploadFile, user_id: int) -> str:
    declared_type = (upload.content_type or "").lower()
    if declared_type and declared_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported.")

    data = await _read_limited(upload)
    image = _decode_and_normalize(data)
    user_dir = settings.upload_dir_path / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    user_dir.chmod(0o700)
    output_path = user_dir / f"{uuid.uuid4().hex}.jpg"

    try:
        image.save(
            output_path,
            format="JPEG",
            quality=86,
            optimize=True,
            progressive=True,
            exif=b"",
        )
        output_path.chmod(0o600)
    except OSError as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unable to store the image.") from exc
    finally:
        image.close()

    if output_path.stat().st_size > settings.MAX_IMAGE_BYTES:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="Processed image is too large.")
    return str(output_path.resolve())


def safe_delete_image(path: str | None) -> None:
    if not path:
        return
    try:
        candidate = Path(path).resolve()
        upload_root = settings.upload_dir_path.resolve()
        if candidate.is_relative_to(upload_root):
            candidate.unlink(missing_ok=True)
    except OSError:
        return
