"""Glossary term generator — short + long definitions, examples, related terms."""
from __future__ import annotations
from ..llm import LLMClient
from ..prompts import GLOSSARY_SYSTEM, BASE_GUARDRAILS, state_clause


def generate_glossary(client: LLMClient, term: str, state: str | None = None) -> dict:
    """Generate a glossary entry for a real estate term."""
    system = GLOSSARY_SYSTEM.format(
        guardrails=BASE_GUARDRAILS,
        state_clause=state_clause(state),
    )
    user_prompt = (
        f"Term: {term}\n"
        f"Generate a comprehensive glossary entry. Return valid JSON only."
    )
    result = client.generate_json(system, user_prompt)
    result.setdefault("type", "glossary")
    result.setdefault("state", state)
    return result
