from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api import admin_usage, admin_users, auth, me, qa
from src.core import config
from src.models import get_db
from src.services.storage import UPLOAD_URL_PREFIX

app = FastAPI(title="Beako AI")
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(admin_users.router)
app.include_router(admin_usage.router)
app.include_router(qa.router)

Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount(UPLOAD_URL_PREFIX, StaticFiles(directory=config.UPLOAD_DIR), name="uploads")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
