"""LangGraph v3 - the multi-query research workflow.

Flow:
    START -> planner -> research -> analysis -> quality_check
                           ^                          |
                           |  (redo WEAK facets only) |
                           +--------------------------+
                                                      | (good OR maxed out)
                                                      v
                                                  report_gen -> END

Upgrades over v2:
  - planner emits a STRUCTURED plan: a disambiguation line + several targeted
    facet queries (overview, customers, funding, leadership, news, competitors)
  - research runs those queries CONCURRENTLY, numbers + de-duplicates sources,
    and uses a recency-biased news search
  - analysis writes inline [n] citations that point at numbered sources
  - quality is cheaper (structural checks + one LLM pass) and reports which
    facets are weak, so a redo only re-researches those facets

Still satisfies every mandatory LangGraph requirement (multiple nodes, shared
state, conditional routing, intermediate outputs, failure handling, bounded
recoverability).
"""

import logging
import operator
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field

from app.workflow.llm import get_llm
from app.workflow.search import get_search

logger = logging.getLogger("zylabs.workflow")

MAX_ATTEMPTS = 2

# The research facets the planner spreads queries across. Keeping this list
# fixed lets the quality node refer to facets by name for targeted redos.
FACETS = [
    "overview_products",
    "customers",
    "funding",
    "leadership_hiring",
    "news",
    "competitors_risks",
]

# Which facet should improve a given report section if it comes back weak.
SECTION_TO_FACET = {
    "overview": "overview_products",
    "products": "overview_products",
    "customers": "customers",
    "signals": "news",
    "risks": "competitors_risks",
}


# --------------------------------------------------------------------------
# Structured output shapes (what we force the LLM to return)
# --------------------------------------------------------------------------
class SearchQuery(BaseModel):
    """One targeted web search the planner wants to run."""
    facet: str = Field(description=f"One of: {', '.join(FACETS)}")
    query: str = Field(description="A specific, web-search-ready query string")


class ResearchPlan(BaseModel):
    """The planner's structured output."""
    disambiguation: str = Field(
        description="One sentence confirming exactly which company this is "
        "(use the website/domain to avoid same-name confusion)."
    )
    queries: list[SearchQuery] = Field(
        description="4-6 targeted queries spread across the research facets."
    )


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
    weak_facets: list[str] = Field(
        default_factory=list,
        description=f"Facets needing more research. Each must be one of: {', '.join(FACETS)}",
    )


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
    disambiguation: str
    queries: list  # list of {facet, query}
    # research output
    research_notes: str
    sources: list  # list of {n, title, url, facet, date}
    # analysis output (the report so far)
    report: dict
    # quality loop control
    quality_ok: bool
    quality_feedback: str
    weak_facets: list
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
    """Produce a structured, multi-query research plan."""
    try:
        llm = get_llm().with_structured_output(ResearchPlan)
        prompt = (
            f"You are planning sales research on '{state['company']}' "
            f"(website: {state.get('website') or 'n/a'}).\n"
            f"The user's objective: {state.get('objective') or 'general meeting prep'}.\n\n"
            f"Produce a research plan:\n"
            f"1) disambiguation: one sentence confirming exactly which company "
            f"this is, using the website/domain to avoid confusing it with "
            f"similarly named companies.\n"
            f"2) queries: 4-6 specific, web-search-ready queries spread across "
            f"these facets: {', '.join(FACETS)}. Always include one 'news' facet "
            f"query for recent events. Tailor queries to the objective."
        )
        plan: ResearchPlan = llm.invoke(prompt)

        # Keep only valid facets; cap at 6 to bound cost/latency.
        queries = [
            {"facet": q.facet, "query": q.query}
            for q in plan.queries
            if q.facet in FACETS and q.query.strip()
        ][:6]
        if not queries:
            # Fallback so research can still proceed.
            queries = [{
                "facet": "overview_products",
                "query": f"{state['company']} company overview products customers",
            }]

        plan_text = plan.disambiguation + "\n" + "\n".join(
            f"- ({q['facet']}) {q['query']}" for q in queries
        )
        logger.info("planner done for %s (%d queries)", state["company"], len(queries))
        return {
            "plan": plan_text,
            "disambiguation": plan.disambiguation,
            "queries": queries,
            "steps": [_step("planner", "done", f"{len(queries)} queries")],
        }
    except Exception as e:
        logger.exception("planner failed")
        fallback = [{
            "facet": "overview_products",
            "query": f"{state['company']} {state.get('objective', '')} overview products customers funding news",
        }]
        return {"plan": "", "disambiguation": "", "queries": fallback,
                "error": f"planner: {e}",
                "steps": [_step("planner", "failed", str(e))]}


def _search_one(facet: str, query: str) -> tuple[str, list]:
    """Run a single Tavily query for one facet (used concurrently)."""
    if facet == "news":
        search = get_search(max_results=5, topic="news", time_range="month")
    else:
        search = get_search(max_results=5)
    result = search.invoke({"query": query})
    results = result.get("results", []) if isinstance(result, dict) else []
    return facet, results


def research_node(state: GraphState) -> dict:
    """Run the planned queries concurrently; number + de-duplicate sources.

    On a redo (when quality flagged weak facets) we only re-research those
    facets, which keeps the retry cheap.
    """
    try:
        queries = state.get("queries") or []
        weak = state.get("weak_facets") or []
        # Targeted redo: only the weak facets. First pass: everything.
        to_run = [q for q in queries if q["facet"] in weak] if weak else queries
        if not to_run:
            to_run = queries or [{
                "facet": "overview_products",
                "query": f"{state['company']} overview products customers",
            }]

        # Run searches in parallel.
        gathered: list[tuple[str, list]] = []
        with ThreadPoolExecutor(max_workers=min(6, len(to_run))) as pool:
            futures = [pool.submit(_search_one, q["facet"], q["query"]) for q in to_run]
            for fut in futures:
                try:
                    gathered.append(fut.result())
                except Exception as e:  # noqa: BLE001 - one bad query shouldn't kill the run
                    logger.warning("a search query failed: %s", e)

        # Preserve good results across retries: keep prior sources + numbering.
        existing = list(state.get("sources", []) or [])
        seen = {s["url"] for s in existing}
        next_n = (max((s.get("n", 0) for s in existing), default=0)) + 1

        new_note_lines: list[str] = []
        for facet, results in gathered:
            for r in results:
                title = r.get("title", "")
                url = r.get("url", "")
                content = r.get("content", "")
                date = r.get("published_date", "") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                n = next_n
                next_n += 1
                existing.append({
                    "n": n, "title": title, "url": url,
                    "facet": facet, "date": date,
                })
                stamp = f" ({date})" if date else ""
                new_note_lines.append(f"[{n}] ({facet}){stamp} {title}: {content}")

        existing_notes = state.get("research_notes", "")
        new_notes = "\n".join(new_note_lines)
        notes = "\n".join(p for p in [existing_notes, new_notes] if p) or "No web results found."

        logger.info(
            "research done for %s (%d new, %d total sources, facets=%s)",
            state["company"], len(new_note_lines), len(existing),
            [q["facet"] for q in to_run],
        )
        detail = f"{len(existing)} sources" + (f" (redo: {', '.join(weak)})" if weak else "")
        return {
            "research_notes": notes,
            "sources": existing,
            "steps": [_step("research", "done", detail)],
        }
    except Exception as e:
        logger.exception("research failed")
        return {"research_notes": "", "sources": [], "error": f"research: {e}",
                "steps": [_step("research", "failed", str(e))]}


def analysis_node(state: GraphState) -> dict:
    """Turn numbered notes into 8 structured sections WITH inline [n] citations."""
    try:
        sources = state.get("sources", []) or []
        valid_ns = sorted(s["n"] for s in sources if "n" in s)
        llm = get_llm().with_structured_output(ReportSections)
        prompt = (
            f"Company: {state['company']}\n"
            f"Which company: {state.get('disambiguation') or 'n/a'}\n"
            f"Objective: {state.get('objective') or 'general meeting prep'}\n"
            f"Research plan:\n{state.get('plan') or 'n/a'}\n\n"
            f"Research notes from the web (each line is prefixed with its source "
            f"number in [brackets]):\n{state.get('research_notes', '')}\n\n"
            f"Available source numbers you may cite: {valid_ns}\n\n"
            f"Write the report sections based ONLY on these notes. "
            f"Add inline citations using the source numbers in square brackets "
            f"(e.g. 'raised a Series B [3]') for factual claims. "
            f"ONLY cite numbers from the available list above - never invent a "
            f"citation. If something is not in the notes, list it under "
            f"'unknowns' instead of guessing. Be specific and honest."
        )
        sections: ReportSections = llm.invoke(prompt)
        logger.info("analysis done for %s", state["company"])
        return {"report": sections.model_dump(), "steps": [_step("analysis", "done")]}
    except Exception as e:
        logger.exception("analysis failed")
        return {"report": {}, "error": f"analysis: {e}",
                "steps": [_step("analysis", "failed", str(e))]}


def _has_citation(report: dict) -> bool:
    """True if any text section contains an [n] style citation marker."""
    import re
    text = " ".join(str(report.get(k, "")) for k in
                     ["overview", "products", "customers", "signals", "risks", "outreach"])
    return bool(re.search(r"\[\d+\]", text))


def quality_node(state: GraphState) -> dict:
    """Cheap structural checks + one LLM pass; report weak facets for redo."""
    attempts = state.get("attempts", 0) + 1
    try:
        report = state.get("report", {})
        required = ["overview", "products", "customers", "signals", "risks", "outreach"]
        # Structural: empty or too-thin core sections.
        empty = [k for k in required if not report.get(k)]
        thin = [k for k in required if report.get(k) and len(str(report[k])) < 40]
        has_cite = _has_citation(report)

        llm = get_llm().with_structured_output(QualityVerdict)
        prompt = (
            f"Objective: {state.get('objective')}\n"
            f"Draft research report (JSON):\n{report}\n\n"
            f"Is this report complete and genuinely useful for the objective? "
            f"If sections are vague, generic, or empty, mark it not good and say "
            f"why. List the facets that need more research in 'weak_facets', "
            f"each chosen from: {', '.join(FACETS)}."
        )
        verdict: QualityVerdict = llm.invoke(prompt)

        is_good = verdict.is_good and not empty and not thin and has_cite

        # Determine weak facets for a targeted redo: combine the LLM's view with
        # facets derived from empty/thin sections.
        weak = {f for f in verdict.weak_facets if f in FACETS}
        for sec in empty + thin:
            if sec in SECTION_TO_FACET:
                weak.add(SECTION_TO_FACET[sec])
        if not is_good and not weak:
            weak = set(FACETS)  # nothing specific -> redo everything

        feedback = verdict.feedback
        notes = []
        if empty:
            notes.append(f"empty: {', '.join(empty)}")
        if thin:
            notes.append(f"thin: {', '.join(thin)}")
        if not has_cite:
            notes.append("no citations")
        if notes:
            feedback = f"[{'; '.join(notes)}] " + feedback

        logger.info("quality for %s: good=%s attempt=%d weak=%s",
                    state["company"], is_good, attempts, sorted(weak))
        return {
            "quality_ok": is_good,
            "quality_feedback": feedback,
            "weak_facets": [] if is_good else sorted(weak),
            "attempts": attempts,
            "steps": [_step("quality_check", "done",
                            "passed" if is_good else "needs work")],
        }
    except Exception as e:
        logger.exception("quality check failed")
        # On failure, accept what we have so we don't loop forever.
        return {"quality_ok": True, "quality_feedback": "", "weak_facets": [],
                "attempts": attempts, "error": f"quality: {e}",
                "steps": [_step("quality_check", "failed", str(e))]}


def _strip_dangling_citations(report: dict, valid_ns: set[int]) -> dict:
    """Remove [n] markers that don't point at a real source."""
    import re

    def clean(text: str) -> str:
        def repl(m: "re.Match") -> str:
            return m.group(0) if int(m.group(1)) in valid_ns else ""
        # Drop dangling markers, then tidy doubled spaces left behind.
        out = re.sub(r"\[(\d+)\]", repl, text)
        return re.sub(r"\s{2,}", " ", out).strip()

    cleaned = dict(report)
    for key in ["overview", "products", "customers", "signals", "risks", "outreach"]:
        if isinstance(cleaned.get(key), str):
            cleaned[key] = clean(cleaned[key])
    for key in ["questions", "unknowns"]:
        if isinstance(cleaned.get(key), list):
            cleaned[key] = [clean(str(x)) for x in cleaned[key]]
    return cleaned


def report_gen_node(state: GraphState) -> dict:
    """Finalize the report: strip dangling citations, attach numbered sources."""
    try:
        sources = state.get("sources", []) or []
        valid_ns = {s["n"] for s in sources if "n" in s}
        report = _strip_dangling_citations(dict(state.get("report", {})), valid_ns)
        report["sources"] = sources
        logger.info("report generated for %s (%d sources)", state["company"], len(sources))
        return {"report": report, "steps": [_step("report_gen", "done")]}
    except Exception as e:
        logger.exception("report_gen failed")
        return {"error": f"report_gen: {e}",
                "steps": [_step("report_gen", "failed", str(e))]}


# --------------------------------------------------------------------------
# Conditional routing
# --------------------------------------------------------------------------
def route_after_quality(state: GraphState) -> str:
    """Return 'finish' to move on, or 'redo' to research weak facets again."""
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
        "disambiguation": "",
        "queries": [],
        "research_notes": "",
        "sources": [],
        "report": {},
        "quality_ok": False,
        "quality_feedback": "",
        "weak_facets": [],
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
