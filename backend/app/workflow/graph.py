"""LangGraph v2 - the full research workflow.

Flow:
    START -> planner -> research -> analysis -> quality_check
                           ^                          |
                           |   (redo if weak, <2x)    |
                           +--------------------------+
                                                      | (good OR maxed out)
                                                      v
                                                  report_gen -> END

Satisfies every mandatory LangGraph requirement:
  - multiple meaningful nodes
  - shared graph state
  - conditional routing (quality loop)
  - intermediate outputs (each node appends a step)
  - failure handling (try/except per node)
  - recoverability (retry loop + bounded attempts)
"""

import logging
import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field

from app.workflow.llm import get_llm
from app.workflow.search import get_search

logger = logging.getLogger("zylabs.workflow")

MAX_ATTEMPTS = 2


# --------------------------------------------------------------------------
# Structured output shapes (what we force the LLM to return)
# --------------------------------------------------------------------------
class ReportSections(BaseModel):
    """The 8 LLM-generated report sections (sources are added separately)."""
    overview: str = Field(description="Concise company overview")
    products: str = Field(description="Products and services offered")
    customers: str = Field(description="Target customers / market segments")
    signals: str = Field(description="Business signals: funding, growth, hiring, news")
    risks: str = Field(description="Risks and challenges the company faces")
    questions: list[str] = Field(description="5-7 smart discovery questions for a sales call")
    outreach: str = Field(description="A suggested outreach strategy tailored to the objective")
    unknowns: list[str] = Field(description="Important things that could NOT be verified")


class QualityVerdict(BaseModel):
    is_good: bool = Field(description="True if the report is complete and useful")
    feedback: str = Field(description="What is missing or weak, if anything")


# --------------------------------------------------------------------------
# Shared state (the notebook)
# --------------------------------------------------------------------------
class GraphState(TypedDict):
    # inputs
    company: str
    website: str
    objective: str
    # planner output
    plan: str
    # research output
    research_notes: str
    sources: list
    # analysis output (the report so far)
    report: dict
    # quality loop control
    quality_ok: bool
    quality_feedback: str
    attempts: int
    # observability
    steps: Annotated[list, operator.add]  # append-only progress log
    error: str


def _step(name: str, status: str, detail: str = "") -> dict:
    """Build one progress-log entry."""
    return {"name": name, "status": status, "detail": detail}


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------
def planner_node(state: GraphState) -> dict:
    """Decide what to focus the research on, given the objective."""
    try:
        llm = get_llm()
        prompt = (
            f"You are planning sales research on '{state['company']}' "
            f"(website: {state.get('website') or 'n/a'}).\n"
            f"The user's objective: {state.get('objective') or 'general meeting prep'}.\n"
            f"Write a short, focused research plan (3-5 bullet points) describing "
            f"what to investigate to best serve this objective."
        )
        plan = llm.invoke(prompt).content
        logger.info("planner done for %s", state["company"])
        return {"plan": plan, "steps": [_step("planner", "done")]}
    except Exception as e:
        logger.exception("planner failed")
        return {"plan": "", "error": f"planner: {e}",
                "steps": [_step("planner", "failed", str(e))]}


def research_node(state: GraphState) -> dict:
    """Search the web (Tavily) and gather raw notes + sources."""
    try:
        search = get_search(max_results=5)
        # Steer the search with the user's objective so research targets what
        # matters for THIS meeting, not just a generic company lookup.
        base = f"{state['company']} company overview products customers funding news"
        query = f"{state['company']} {state['objective']} {base}" if state.get("objective") else base
        # On a redo, incorporate the quality feedback to dig deeper.
        if state.get("quality_feedback"):
            query += f" {state['quality_feedback']}"

        result = search.invoke({"query": query})
        results = result.get("results", []) if isinstance(result, dict) else []

        notes_parts, new_sources = [], []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            notes_parts.append(f"- {title}: {content}")
            if url:
                new_sources.append({"title": title, "url": url})

        # Preserve good results across retries: merge with what we already
        # have and de-duplicate by URL, so a poor redo never wipes them out.
        existing = state.get("sources", []) or []
        seen = {s["url"] for s in existing}
        merged_sources = existing + [s for s in new_sources if s["url"] not in seen]

        existing_notes = state.get("research_notes", "")
        new_notes = "\n".join(notes_parts)
        notes = "\n".join(p for p in [existing_notes, new_notes] if p) or "No web results found."

        logger.info("research done for %s (%d new, %d total sources)",
                    state["company"], len(new_sources), len(merged_sources))
        return {
            "research_notes": notes,
            "sources": merged_sources,
            "steps": [_step("research", "done", f"{len(merged_sources)} sources")],
        }
    except Exception as e:
        logger.exception("research failed")
        return {"research_notes": "", "sources": [], "error": f"research: {e}",
                "steps": [_step("research", "failed", str(e))]}


def analysis_node(state: GraphState) -> dict:
    """Turn raw notes into the 8 structured report sections."""
    try:
        llm = get_llm().with_structured_output(ReportSections)
        prompt = (
            f"Company: {state['company']}\n"
            f"Objective: {state.get('objective') or 'general meeting prep'}\n"
            f"Research plan (priorities to emphasize):\n{state.get('plan') or 'n/a'}\n\n"
            f"Research notes from the web:\n{state.get('research_notes', '')}\n\n"
            f"Based ONLY on the notes above, fill in the report sections, "
            f"prioritizing the angles called out in the research plan. "
            f"Be specific and honest. If something is not in the notes, list it "
            f"under 'unknowns' rather than guessing."
        )
        sections: ReportSections = llm.invoke(prompt)
        logger.info("analysis done for %s", state["company"])
        return {"report": sections.model_dump(), "steps": [_step("analysis", "done")]}
    except Exception as e:
        logger.exception("analysis failed")
        return {"report": {}, "error": f"analysis: {e}",
                "steps": [_step("analysis", "failed", str(e))]}


def quality_node(state: GraphState) -> dict:
    """Judge whether the report is good enough; drives the conditional loop."""
    attempts = state.get("attempts", 0) + 1
    try:
        report = state.get("report", {})
        # Cheap structural check: any empty core section?
        required = ["overview", "products", "customers", "signals", "risks", "outreach"]
        empty = [k for k in required if not report.get(k)]

        llm = get_llm().with_structured_output(QualityVerdict)
        prompt = (
            f"Objective: {state.get('objective')}\n"
            f"Here is a draft research report (JSON):\n{report}\n\n"
            f"Is this report complete and genuinely useful for the objective? "
            f"If sections are vague, generic, or empty, mark it not good and say why."
        )
        verdict: QualityVerdict = llm.invoke(prompt)
        is_good = verdict.is_good and not empty
        feedback = verdict.feedback
        if empty:
            feedback = f"Empty sections: {', '.join(empty)}. " + feedback

        logger.info("quality check for %s: good=%s attempt=%d",
                    state["company"], is_good, attempts)
        return {
            "quality_ok": is_good,
            "quality_feedback": feedback,
            "attempts": attempts,
            "steps": [_step("quality_check", "done",
                            "passed" if is_good else "needs work")],
        }
    except Exception as e:
        logger.exception("quality check failed")
        # On failure, accept what we have so we don't loop forever.
        return {"quality_ok": True, "quality_feedback": "", "attempts": attempts,
                "error": f"quality: {e}",
                "steps": [_step("quality_check", "failed", str(e))]}


def report_gen_node(state: GraphState) -> dict:
    """Finalize the report: attach sources to the structured sections."""
    try:
        report = dict(state.get("report", {}))
        report["sources"] = state.get("sources", [])
        logger.info("report generated for %s", state["company"])
        return {"report": report, "steps": [_step("report_gen", "done")]}
    except Exception as e:
        logger.exception("report_gen failed")
        return {"error": f"report_gen: {e}",
                "steps": [_step("report_gen", "failed", str(e))]}


# --------------------------------------------------------------------------
# Conditional routing
# --------------------------------------------------------------------------
def route_after_quality(state: GraphState) -> str:
    """Return 'finish' to move on, or 'redo' to research again."""
    if state.get("quality_ok") or state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "finish"
    return "redo"


# --------------------------------------------------------------------------
# Build the graph
# --------------------------------------------------------------------------
def build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(GraphState)
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("quality_check", quality_node)
    graph.add_node("report_gen", report_gen_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "analysis")
    graph.add_edge("analysis", "quality_check")
    graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {"redo": "research", "finish": "report_gen"},
    )
    graph.add_edge("report_gen", END)
    return graph.compile()


def initial_state(company: str, website: str = "", objective: str = "") -> dict:
    """Build the starting state for a run."""
    return {
        "company": company,
        "website": website,
        "objective": objective,
        "plan": "",
        "research_notes": "",
        "sources": [],
        "report": {},
        "quality_ok": False,
        "quality_feedback": "",
        "attempts": 0,
        "steps": [],
        "error": "",
    }


if __name__ == "__main__":
    import json

    app = build_graph()
    state = initial_state(
        company="Notion",
        website="https://notion.so",
        objective="Sell them an AI customer-support tool",
    )
    result = app.invoke(state)
    print("\n=== STEPS ===")
    for s in result["steps"]:
        print(f"  [{s['status']}] {s['name']} {s.get('detail','')}")
    print("\n=== REPORT ===")
    print(json.dumps(result["report"], indent=2))
