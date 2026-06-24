"""Workflow runner.

Executes the LangGraph workflow for a session in a background thread,
streaming each node's output and persisting progress + the final report
to the database as it happens.
"""

import logging
import threading

from app.core.database import SessionLocal
from app.models.db_models import Report, ResearchSession, WorkflowStep
from app.workflow.graph import build_graph, initial_state

logger = logging.getLogger("project01.runner")


def _persist_step(db, session_id: str, step: dict) -> None:
    db.add(WorkflowStep(
        session_id=session_id,
        step_name=step.get("name", "?"),
        status=step.get("status", "done"),
        output=step,
    ))
    db.commit()


def _save_report(db, session_id: str, report: dict) -> None:
    """Create or replace the report row for this session."""
    existing = db.query(Report).filter(Report.session_id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.add(Report(
        session_id=session_id,
        overview=report.get("overview", ""),
        products=report.get("products", ""),
        customers=report.get("customers", ""),
        signals=report.get("signals", ""),
        risks=report.get("risks", ""),
        questions=report.get("questions", []),
        outreach=report.get("outreach", ""),
        unknowns=report.get("unknowns", []),
        sources=report.get("sources", []),
    ))
    db.commit()


def _run(session_id: str) -> None:
    """The actual work; runs inside a background thread with its own DB session."""
    db = SessionLocal()
    try:
        session = db.get(ResearchSession, session_id)
        if session is None:
            logger.error("run: session %s not found", session_id)
            return

        # Reset state for a fresh run.
        session.status = "running"
        session.error = ""
        db.query(WorkflowStep).filter(WorkflowStep.session_id == session_id).delete()
        db.commit()

        graph = build_graph()
        state = initial_state(session.company_name, session.website, session.objective)

        last_report, last_error = {}, ""

        # Stream node-by-node. Each update is {node_name: returned_delta}.
        for update in graph.stream(state):
            for _node, delta in update.items():
                for step in delta.get("steps", []):
                    _persist_step(db, session_id, step)
                if delta.get("report"):
                    last_report = delta["report"]
                if delta.get("error"):
                    last_error = delta["error"]

        if last_report:
            _save_report(db, session_id, last_report)

        session = db.get(ResearchSession, session_id)
        session.status = "completed" if last_report else "failed"
        session.error = last_error
        db.commit()
        logger.info("run finished for %s status=%s", session_id, session.status)

    except Exception as e:
        logger.exception("run crashed for %s", session_id)
        try:
            session = db.get(ResearchSession, session_id)
            if session:
                session.status = "failed"
                session.error = str(e)
                db.commit()
        except Exception:
            logger.exception("failed to mark session failed")
    finally:
        db.close()


def start_workflow(session_id: str) -> None:
    """Kick off the workflow in a daemon thread and return immediately."""
    thread = threading.Thread(target=_run, args=(session_id,), daemon=True)
    thread.start()
