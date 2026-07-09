"""AI Chatbot + Natural-Language / Semantic Search routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.assistant import AssistantQuery
from app.services.ai.assistant import chat, nl_search

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/search")
def search(body: AssistantQuery, db: Session = Depends(get_db)) -> dict:
    """Turn a plain-English query into filtered, ranked properties."""
    return nl_search(db, body.question)


@router.post("/chat")
def ask(body: AssistantQuery, db: Session = Depends(get_db)) -> dict:
    """Ask the AI chatbot a question; get a grounded answer + relevant listings."""
    return chat(db, body.question)
