"""Chat service: answer follow-up questions grounded in the report.

This shows how LLM "memory" really works: we rebuild the full message
list (system instructions + report context + prior turns + new question)
and send it on every call. The model itself stores nothing.
"""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models.db_models import ChatMessage, Report
from app.workflow.llm import get_llm

logger = logging.getLogger("zylabs.chat")


def _report_context(report: Report | None) -> str:
    if report is None:
        return "No report is available yet."
    data = {
        "overview": report.overview,
        "products": report.products,
        "customers": report.customers,
        "signals": report.signals,
        "risks": report.risks,
        "questions": report.questions,
        "outreach": report.outreach,
        "unknowns": report.unknowns,
        "sources": report.sources,
    }
    return json.dumps(data, indent=2)


def answer(db, session, user_message: str) -> str:
    """Generate an assistant reply grounded in the session's report,
    persist both the user and assistant messages, and return the reply."""
    report = db.query(Report).filter(Report.session_id == session.id).first()

    # 1) Save the user's message first.
    db.add(ChatMessage(session_id=session.id, role="user", content=user_message))
    db.commit()

    # 2) Build the message list (the "memory").
    messages = [
        SystemMessage(content=(
            f"You are a sales research assistant helping prepare for a meeting "
            f"with {session.company_name}. Answer using ONLY the research report "
            f"below. If the answer isn't in it, say so honestly.\n\n"
            f"RESEARCH REPORT:\n{_report_context(report)}"
        ))
    ]
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    for m in history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))

    # 3) Call the LLM.
    try:
        reply = get_llm(temperature=0.3).invoke(messages).content
    except Exception as e:
        logger.exception("chat failed")
        reply = "Sorry, I couldn't generate a response right now. Please try again."

    # 4) Save and return the assistant reply.
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
    db.commit()
    return reply
