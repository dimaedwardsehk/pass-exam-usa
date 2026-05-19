"""Meta tags generator — title ≤60, description 140-155 chars."""
from __future__ import annotations
from ..llm import LLMClient
from ..prompts import META_SYSTEM, BASE_GUARDRAILS, state_clause


def generate_meta(client: LLMClient, page_name: str, page_description: str,
                  state: str | None = None) -> dict:
    """Generate meta tags for a page."""
    system = META_SYSTEM.format(
        guardrails=BASE_GUARDRAILS,
        state_clause=state_clause(state),
    )
    user_prompt = (
        f"Page: {page_name}\n"
        f"Description: {page_description}\n"
        f"Generate optimized meta tags. Return valid JSON only."
    )
    result = client.generate_json(system, user_prompt)
    result.setdefault("type", "meta")
    result.setdefault("page_name", page_name)
    return result
