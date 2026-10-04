"""Export users' right/wrong ratings of answers (qa_messages.feedback) as evaluation data.

Each line of data/eval/feedback.jsonl is one rated answer with the question, the answer, the
rating and comment, the sources it was given and how it was produced. Wrong answers with a
comment are the best candidates for new golden-set questions.
"""

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

FEEDBACK_PATH = Path("data/eval/feedback.jsonl")


def export(db: Session, path: Path = FEEDBACK_PATH) -> dict:
    rows = db.execute(text("""
        SELECT a.id, a.created_at, a.feedback, a.feedback_comment, a.feedback_at, a.content AS answer,
               a.found, a.mode, a.model, a.max_volume, a.sources, a.usage, a.timings_ms,
               (SELECT q.content FROM qa_messages q
                WHERE q.conversation_id = a.conversation_id AND q.role = 'user' AND q.created_at <= a.created_at
                ORDER BY q.created_at DESC LIMIT 1) AS question
        FROM qa_messages a
        WHERE a.role = 'assistant' AND a.feedback IS NOT NULL
        ORDER BY a.feedback_at
    """)).mappings().all()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({
                "message_id": str(r["id"]),
                "question": r["question"],
                "answer": r["answer"],
                "rating": r["feedback"],
                "comment": r["feedback_comment"],
                "rated_at": r["feedback_at"].isoformat(),
                "found": r["found"],
                "mode": r["mode"],
                "model": r["model"],
                "max_volume": r["max_volume"],
                "cited": [
                    {"volume": s["volume"], "chapter": s["chapter"], "paragraphs": s["paragraphs"]}
                    for s in (r["sources"] or []) if s.get("cited")
                ],
                "usage": r["usage"],
                "timings_ms": r["timings_ms"],
            }, ensure_ascii=False) + "\n")
    right = sum(1 for r in rows if r["feedback"] == 1)
    return {"rated": len(rows), "right": right, "wrong": len(rows) - right,
            "with_comment": sum(1 for r in rows if r["feedback_comment"]), "path": str(path)}
