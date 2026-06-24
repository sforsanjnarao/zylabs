"""Chat API routes: follow-up Q&A grounded in the report (F4)."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import ChatMessage, ResearchSession
from app.schemas import ChatMessageOut, ChatRequest
from app.services.chat import answer

logger = logging.getLogger("zylabs.api")

router = APIRouter(prefix="/api/sessions", tags=["chat"])


@router.post("/{session_id}/chat", response_model=ChatMessageOut)
def post_chat(session_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    reply = answer(db, session, payload.message.strip())
    return ChatMessageOut(role="assistant", content=reply, created_at=datetime.now(timezone.utc))


@router.get("/{session_id}/chat", response_model=list[ChatMessageOut])
def get_chat(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
