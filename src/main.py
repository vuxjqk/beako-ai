import logging
import threading
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api import admin_usage, admin_users, auth, me, qa, uploads
from src.core import config
from src.models import get_db
from src.services.storage import UPLOAD_URL_PREFIX

# Uvicorn only sets up its own loggers; without this the app's INFO logs (one line per question,
# agent steps) are dropped and only warnings reach the container log via Python's last resort
_app_log = logging.getLogger("beako")
if not _app_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
    _app_log.addHandler(_handler)
    _app_log.setLevel(config.LOG_LEVEL)
    _app_log.propagate = False

app = FastAPI(title="Beako AI")
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(admin_users.router)
app.include_router(admin_usage.router)
app.include_router(qa.router)

if config.STORAGE_BACKEND == "db":
    app.include_router(uploads.router)
else:
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    app.mount(UPLOAD_URL_PREFIX, StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

if config.PRELOAD_EMBEDDER:
    from src.services.qa import get_embedder

    # A sleeping free-plan host wakes up on a request; have the model ready for the first question
    threading.Thread(target=get_embedder, daemon=True, name="preload-embedder").start()


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
