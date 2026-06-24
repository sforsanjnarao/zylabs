"""Tavily web search helper.

Provides a configured search tool. Tavily reads its key from the
TAVILY_API_KEY environment variable, so we set it from our settings.
"""

import os

from langchain_tavily import TavilySearch

from app.core.config import settings


def get_search(max_results: int = 5) -> TavilySearch:
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
    return TavilySearch(max_results=max_results)
