"""Tavily web search helper.

Provides a configured search tool. Tavily reads its key from the
TAVILY_API_KEY environment variable, so we set it from our settings.

The helper supports a ``topic`` ("general" or "news") and an optional
``time_range`` so the recency-focused news query can favor fresh results.
"""

import logging
import os

from langchain_tavily import TavilySearch

from app.core.config import settings

logger = logging.getLogger("zylabs.workflow")


def get_search(
    max_results: int = 5,
    topic: str = "general",
    time_range: str | None = None,
) -> TavilySearch:
    """Return a configured Tavily search tool.

    ``topic="news"`` plus a ``time_range`` (e.g. "month") biases results
    toward recent events, which matters for the Business Signals section.
    Unsupported kwargs are dropped gracefully across langchain-tavily versions.
    """
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

    kwargs: dict = {"max_results": max_results}
    if topic:
        kwargs["topic"] = topic
    if time_range:
        kwargs["time_range"] = time_range

    try:
        return TavilySearch(**kwargs)
    except TypeError:
        # Older versions may not accept topic/time_range — fall back safely.
        logger.warning("TavilySearch rejected extra kwargs; using max_results only")
        return TavilySearch(max_results=max_results)
