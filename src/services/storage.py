"""Avatar file storage.

STORAGE_BACKEND picks where images live:
- local (default): files on disk under UPLOAD_DIR, served by the app at /uploads
- db: rows in avatar_files, for hosts whose disk is wiped on every deploy or restart
  (e.g. Render's free plan), served by the route in src/api/uploads.py
Either way an avatar's URL is /uploads/avatars/<name>, so the frontend does not care.
"""

import uuid
from pathlib import Path

from src.core import config

UPLOAD_URL_PREFIX = "/uploads"
AVATAR_SUBDIR = "avatars"
AVATAR_DIR = Path(config.UPLOAD_DIR) / AVATAR_SUBDIR
AVATAR_URL_PREFIX = f"{UPLOAD_URL_PREFIX}/{AVATAR_SUBDIR}/"
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}


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


def _in_db() -> bool:
    return config.STORAGE_BACKEND == "db"


def save_avatar(data: bytes) -> str:
    """Store the image and return its public URL path."""
    extension = detect_image_extension(data)
    if _in_db():
        from src.models import AvatarFile, SessionLocal

        with SessionLocal() as db:
            row = AvatarFile(content_type=CONTENT_TYPES[extension], data=data)
            db.add(row)
            db.commit()
            return f"{AVATAR_URL_PREFIX}{row.id.hex}.{extension}"
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    # A fresh name per upload so browsers/CDNs never serve a stale cached avatar
    filename = f"{uuid.uuid4().hex}.{extension}"
    (AVATAR_DIR / filename).write_bytes(data)
    return AVATAR_URL_PREFIX + filename


def avatar_id(url_or_name: str) -> uuid.UUID | None:
    """The avatar_files id in "/uploads/avatars/<hex>.<ext>" (or just "<hex>.<ext>")."""
    name = url_or_name.removeprefix(AVATAR_URL_PREFIX)
    try:
        return uuid.UUID(hex=name.split(".", 1)[0])
    except ValueError:
        return None


def delete_avatar(url: str | None) -> None:
    """Delete a stored avatar. External URLs (e.g. Google profile pictures) are ignored."""
    if not url or not url.startswith(AVATAR_URL_PREFIX):
        return
    if _in_db():
        from src.models import AvatarFile, SessionLocal

        if (file_id := avatar_id(url)) is not None:
            with SessionLocal() as db:
                db.query(AvatarFile).filter(AvatarFile.id == file_id).delete()
                db.commit()
        return
    path = (AVATAR_DIR / url.removeprefix(AVATAR_URL_PREFIX)).resolve()
    if path.parent != AVATAR_DIR.resolve():
        return
    path.unlink(missing_ok=True)
