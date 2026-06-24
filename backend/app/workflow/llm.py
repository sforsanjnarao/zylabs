"""Shared LLM factory.

Centralizes how we create the OpenAI chat model so every node uses the
same configuration (model name, temperature, retries).
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Return a configured chat model.

    temperature=0 keeps research factual and consistent; raise it for
    more creative sections like outreach ideas.
    """
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
        timeout=60,
        max_retries=2,
    )
