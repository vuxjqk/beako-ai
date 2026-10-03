"""Avatar file storage.

Files are kept on local disk under UPLOAD_DIR (inside the project for now) and served
by the app at /uploads. Swap these two functions out to move to S3/GCS/etc.
"""

import uuid
from pathlib import Path

from src.core import config

UPLOAD_URL_PREFIX = "/uploads"
AVATAR_SUBDIR = "avatars"
AVATAR_DIR = Path(config.UPLOAD_DIR) / AVATAR_SUBDIR
AVATAR_URL_PREFIX = f"{UPLOAD_URL_PREFIX}/{AVATAR_SUBDIR}/"


class InvalidImageError(Exception):
    pass


def detect_image_extension(data: bytes) -> str:
    """Identify the format from the file's magic bytes; the client's content type is not trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    raise InvalidImageError("Only JPEG, PNG, WebP or GIF images are allowed")


def save_avatar(data: bytes) -> str:
    """Store the image and return its public URL path."""
    extension = detect_image_extension(data)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    # A fresh name per upload so browsers/CDNs never serve a stale cached avatar
    filename = f"{uuid.uuid4().hex}.{extension}"
    (AVATAR_DIR / filename).write_bytes(data)
    return AVATAR_URL_PREFIX + filename


def delete_avatar(url: str | None) -> None:
    """Delete a stored avatar. External URLs (e.g. Google profile pictures) are ignored."""
    if not url or not url.startswith(AVATAR_URL_PREFIX):
        return
    path = (AVATAR_DIR / url.removeprefix(AVATAR_URL_PREFIX)).resolve()
    if path.parent != AVATAR_DIR.resolve():
        return
    path.unlink(missing_ok=True)
