from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.ingest.settings import MODEL_NAME
from src.models import User, get_db
from src.schemas.qa import AskRequest, AskResponse
from src.services import llm
from src.services.qa import answer_question

router = APIRouter(prefix="/qa", tags=["qa"])


# Signed-in users only: every call spends LLM quota
@router.post("", response_model=AskResponse)
def ask(
    body: AskRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    try:
        result = answer_question(db, body.question.strip(), body.top_k)
    except llm.LLMNotConfigured as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Question answering is not configured: {e}")
    except llm.LLMError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
    return AskResponse(**vars(result), embedding_model=MODEL_NAME)
