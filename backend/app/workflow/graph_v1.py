"""LangGraph v1 - the simplest workflow that works end-to-end.

Flow:  START -> research -> report -> END

This is a learning/proof-of-concept graph. The real 5-node graph comes next.
Run it directly with:  python -m app.workflow.graph_v1
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.workflow.llm import get_llm


# 1) SHARED STATE: the "notebook" passed through every node.
class ResearchState(TypedDict):
    company: str          # input
    research_notes: str   # written by research_node
    report: str           # written by report_node


# 2) NODES: each is a function that reads state and returns updates.
def research_node(state: ResearchState) -> dict:
    llm = get_llm()
    prompt = (
        f"You are a business research assistant. Research the company "
        f"'{state['company']}'. List key facts about what they do, their "
        f"products, customers, and any notable business signals."
    )
    notes = llm.invoke(prompt).content
    return {"research_notes": notes}


def report_node(state: ResearchState) -> dict:
    llm = get_llm()
    prompt = (
        f"Using these research notes, write a concise sales briefing "
        f"about {state['company']}:\n\n{state['research_notes']}"
    )
    report = llm.invoke(prompt).content
    return {"report": report}


# 3) GRAPH: wire the nodes together.
def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("research", research_node)
    graph.add_node("report", report_node)
    graph.add_edge(START, "research")
    graph.add_edge("research", "report")
    graph.add_edge("report", END)
    return graph.compile()


# 4) Allow running this file directly to test the workflow.
if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"company": "Stripe"})
    print("\n=== RESEARCH NOTES ===\n")
    print(result["research_notes"])
    print("\n=== REPORT ===\n")
    print(result["report"])
