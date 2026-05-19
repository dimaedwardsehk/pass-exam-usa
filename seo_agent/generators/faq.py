"""FAQ generator with JSON-LD FAQPage schema markup."""
from __future__ import annotations
import json
from ..llm import LLMClient
from ..prompts import FAQ_SYSTEM, BASE_GUARDRAILS, state_clause


def generate_faq(client: LLMClient, topic: str, state: str | None = None) -> dict:
    """Generate FAQ content with structured data markup."""
    system = FAQ_SYSTEM.format(
        guardrails=BASE_GUARDRAILS,
        state_clause=state_clause(state),
    )
    user_prompt = (
        f"Topic: {topic}\n"
        f"Generate 5-8 FAQ entries. Return valid JSON only."
    )
    result = client.generate_json(system, user_prompt)

    # Build JSON-LD FAQPage schema from the generated FAQs
    if "faqs" in result:
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"]
                    }
                }
                for faq in result["faqs"]
            ]
        }
        result["json_ld"] = json.dumps(schema, indent=2)

    result.setdefault("type", "faq")
    result.setdefault("state", state)
    return result
