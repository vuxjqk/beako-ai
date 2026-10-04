from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.models import get_db
from src.services import usage

router = APIRouter(
    prefix="/admin/usage",
    tags=["admin: usage"],
    dependencies=[Depends(require_admin)],
)


def _camel(value):
    """camelCase keys, like the CamelModel responses elsewhere in the API."""
    if isinstance(value, dict):
        return {to_camel(k): _camel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_camel(v) for v in value]
    return value


@router.get("")
def usage_report(
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict:
    """Question answering per day (questions, tokens, estimated cost, "not found" rate, 👎 rate,
    latency), today's spend against the daily budget, today's heaviest users, and why questions
    were refused or failed. Days start at midnight in QA_TIMEZONE."""
    return _camel(usage.report(db, days))
