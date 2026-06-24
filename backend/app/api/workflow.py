"""Workflow API routes: start a run, stream progress (SSE), fetch the report."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.database import SessionLocal, get_db
from app.models.db_models import Report, ResearchSession, WorkflowStep
from app.schemas import ReportOut
from app.services.runner import start_workflow

logger = logging.getLogger("project01.api")

router = APIRouter(prefix="/api/sessions", tags=["workflow"])


@router.post("/{session_id}/run")
def run_workflow(session_id: str, db: Session = Depends(get_db)):
    """Start the LangGraph workflow for a session (F2)."""
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "running":
        return {"status": "running", "detail": "Already running"}
    start_workflow(session_id)
    logger.info("workflow started for %s", session_id)
    return {"status": "running"}


@router.get("/{session_id}/stream")
async def stream_progress(session_id: str):
    """Stream workflow progress to the browser via Server-Sent Events."""

    async def event_generator():
        sent = 0
        while True:
            db = SessionLocal()
            try:
                session = db.get(ResearchSession, session_id)
                if session is None:
                    yield {"event": "error", "data": json.dumps({"detail": "Session not found"})}
                    return

                steps = (
                    db.query(WorkflowStep)
                    .filter(WorkflowStep.session_id == session_id)
                    .order_by(WorkflowStep.created_at)
                    .all()
                )
                for st in steps[sent:]:
                    yield {
                        "event": "step",
                        "data": json.dumps(
                            {"name": st.step_name, "status": st.status, "output": st.output}
                        ),
                    }
                sent = len(steps)

                if session.status in ("completed", "failed"):
                    yield {
                        "event": "done",
                        "data": json.dumps({"status": session.status, "error": session.error}),
                    }
                    return
            finally:
                db.close()
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/{session_id}/report", response_model=ReportOut)
def get_report(session_id: str, db: Session = Depends(get_db)):
    """Return the final structured report (F3)."""
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    report = db.query(Report).filter(Report.session_id == session_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not ready yet")
    return report
