"""CTA block builder for SEO articles."""

from __future__ import annotations

from html import escape

_HREFS = {
    "cdl": "https://dimaedwardsehk.github.io/pass-exam-usa/#cdl",
    "real_estate": "https://dimaedwardsehk.github.io/pass-exam-usa/#real-estate",
    "dmv": "https://dimaedwardsehk.github.io/pass-exam-usa/#dmv",
}

_CONTENT = {
    "cdl": {
        "headline": "Preparing for Your CDL Knowledge Test?",
        "headline_state": "Preparing for the {state} CDL Knowledge Test?",
        "bullets": [
            "Review core CDL rules, endorsements, and safety topics in one place.",
            "Practice with focused questions that match the structure of the exam.",
            "Track weak areas before you schedule your test appointment.",
        ],
        "button": "Start CDL Practice",
    },
    "real_estate": {
        "headline": "Studying for Your Real Estate Exam?",
        "headline_state": "Studying for the {state} Real Estate Exam?",
        "bullets": [
            "Build a working command of agency, contracts, finance, and property law.",
            "Use exam-style practice to connect definitions with real scenarios.",
            "Review state-specific topics without losing the national exam framework.",
        ],
        "button": "Start Real Estate Practice",
    },
    "dmv": {
        "headline": "Getting Ready for Your DMV Written Test?",
        "headline_state": "Getting Ready for the {state} DMV Written Test?",
        "bullets": [
            "Review traffic laws, road signs, and safe-driving rules by topic.",
            "Practice with clear explanations before taking the official test.",
            "Focus on the rules new drivers most often miss.",
        ],
        "button": "Start DMV Practice",
    },
}

_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def _format_state(state: str | None) -> str | None:
    """Convert state abbreviation to full name or return None."""
    if state is None:
        return None
    normalized = state.strip()
    if not normalized:
        return None
    return _STATE_NAMES.get(normalized.upper(), normalized)


def build_cta(category: str, state: str | None) -> str:
    """Build an HTML call-to-action block for an article category."""
    normalized_category = category.strip().lower()
    if normalized_category not in _CONTENT:
        raise ValueError(f"unsupported category: {category}")

    content = _CONTENT[normalized_category]
    state_name = _format_state(state)

    if state_name:
        headline = content["headline_state"].format(
            state=escape(state_name, quote=False),
        )
    else:
        headline = content["headline"]

    bullet_1, bullet_2, bullet_3 = content["bullets"]
    href = _HREFS[normalized_category]
    button = content["button"]
    category_attr = escape(normalized_category, quote=True)

    return "\n".join(
        [
            f'<aside class="cta" data-category="{category_attr}">',
            f"  <h3>{headline}</h3>",
            "  <ul>",
            f"    <li>{bullet_1}</li>",
            f"    <li>{bullet_2}</li>",
            f"    <li>{bullet_3}</li>",
            "  </ul>",
            '  <p class="cta-price">Get web access for $9.99.</p>',
            f'  <a class="cta-btn" href="{href}">{button}</a>',
            "</aside>",
        ],
    )
