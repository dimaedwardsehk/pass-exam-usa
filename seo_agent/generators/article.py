"""Blog article generator — 900-1400 words, H1/H2/H3, LSI keywords."""
from __future__ import annotations
from ..llm import LLMClient
from ..prompts import ARTICLE_SYSTEM, BASE_GUARDRAILS, state_clause


def generate_article(client: LLMClient, topic: str, state: str | None = None,
                     keywords: list[str] | None = None) -> dict:
    """Generate a full SEO blog article."""
    system = ARTICLE_SYSTEM.format(
        guardrails=BASE_GUARDRAILS,
        state_clause=state_clause(state),
    )
    user_parts = [f"Write a comprehensive article about: {topic}"]
    if state:
        user_parts.append(f"Target state: {state}")
    if keywords:
        user_parts.append(f"Must include these keywords naturally: {', '.join(keywords)}")
    user_parts.append("Return valid JSON only.")

    result = client.generate_json(system, "\n".join(user_parts))
    result.setdefault("type", "article")
    result.setdefault("state", state)
    return result
