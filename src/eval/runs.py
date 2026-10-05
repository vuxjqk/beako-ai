"""Saving evaluation runs together with the configuration that produced them."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import config
from src.ingest.settings import MODEL_NAME
from src.services import qa
from src.services.retrieval import RetrievalConfig

RUNS_DIR = Path("data/eval/runs")


def _commit() -> str | None:
    """HEAD commit read straight from .git (the backend image has no git binary)."""
    git = Path(".git")
    try:
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref: "):
            return head[:7]
        ref = head[5:]
        if (git / ref).exists():
            return (git / ref).read_text().strip()[:7]
        for line in (git / "packed-refs").read_text().splitlines():
            if line.endswith(" " + ref):
                return line[:7]
    except OSError:
        pass
    return None


def _code() -> dict:
    """The commit plus a hash of every file under src/, so uncommitted edits still tell runs apart."""
    h = hashlib.sha256()
    for path in sorted(Path("src").rglob("*.py")):
        h.update(str(path.as_posix()).encode() + b"\0" + path.read_bytes())
    return {"commit": _commit(), "src_sha256": h.hexdigest()[:12]}


def retrieval_config(db: Session, depth: int, cfg: RetrievalConfig) -> dict:
    chunkers = db.execute(text(
        "SELECT chunker_version, embedding_model, count(*) FROM book_chunks GROUP BY 1, 2 ORDER BY 1, 2"
    )).all()
    return {
        "method": cfg.label(),
        "settings": cfg.as_dict(),
        "embedding_model": MODEL_NAME,
        "qa_top_k": config.QA_TOP_K,
        "depth": depth,
        "chunks": [{"chunker_version": c, "embedding_model": m, "count": n} for c, m, n in chunkers],
    }


def generation_config(judge_model: str, mode: str) -> dict:
    from src.services import agent

    return {
        "qa_mode": mode,
        "qa_escalate": config.QA_ESCALATE if mode == "auto" else None,
        "agent": None if mode == "simple" else {
            "max_steps": config.AGENT_MAX_STEPS,
            "max_context_tokens": config.AGENT_MAX_CONTEXT_TOKENS,
            "system_prompt_sha256": hashlib.sha256(agent.SYSTEM_PROMPT.encode()).hexdigest()[:12],
        },
        "provider": config.LLM_PROVIDER,
        "model": config.LLM_MODEL,
        "temperature": config.LLM_TEMPERATURE,
        "max_output_tokens": config.LLM_MAX_OUTPUT_TOKENS,
        "reasoning_effort": config.LLM_REASONING_EFFORT or None,
        "system_prompt_sha256": hashlib.sha256(qa.SYSTEM_PROMPT.encode()).hexdigest()[:12],
        "system_prompt": qa.SYSTEM_PROMPT,
        "judge_provider": config.JUDGE_PROVIDER,
        "judge_model": judge_model,
    }


def new_run_dir(kind: str, label: str | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in (label or "")).strip("-")
    path = RUNS_DIR / f"{stamp}-{kind}{'-' + slug if slug else ''}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def header(kind: str, label: str | None, golden_sha: str, n_questions: int,
           golden_path: Path | None = None) -> dict:
    golden_set = {"sha256": golden_sha[:12], "questions": n_questions}
    if golden_path is not None:
        golden_set["path"] = golden_path.as_posix()
    return {
        "kind": kind,
        "label": label,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code": _code(),
        "golden_set": golden_set,
    }


def save(run_dir: Path, run: dict) -> Path:
    path = run_dir / "run.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def load_all(kind: str | None = None) -> list[dict]:
    runs = []
    for path in sorted(RUNS_DIR.glob("*/run.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        run["dir"] = path.parent.name
        if kind is None or run["kind"] == kind:
            runs.append(run)
    return runs
