"""Serves avatars kept in the database (STORAGE_BACKEND=db) at the same URLs as on-disk files."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.models import AvatarFile, get_db
from src.services.storage import AVATAR_URL_PREFIX, avatar_id

router = APIRouter(tags=["uploads"])


@router.get(AVATAR_URL_PREFIX + "{name}", include_in_schema=False)
def get_avatar(name: str, db: Session = Depends(get_db)) -> Response:
    file_id = avatar_id(name)
    row = db.get(AvatarFile, file_id) if file_id else None
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    # Every upload gets a new name, so a URL's content never changes
    return Response(row.data, media_type=row.content_type,
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})
