"""Session API routes: create, list, and fetch research sessions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import ResearchSession
from app.schemas import SessionCreate, SessionDetail, SessionSummary

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionSummary, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """Create a new research session (F1)."""
    session = ResearchSession(
        company_name=payload.company_name,
        website=payload.website,
        objective=payload.objective,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db)):
    """List all sessions, newest first (session history)."""
    stmt = select(ResearchSession).order_by(ResearchSession.created_at.desc())
    return db.scalars(stmt).all()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Fetch one session with its report and workflow steps (detail page)."""
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
