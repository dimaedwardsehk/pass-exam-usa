"""SEO Agent entry point: generates one article per run and publishes it."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from agent import generator, integrator, seo_check  # noqa: E402
from agent.cta import build_cta  # noqa: E402

LOGGER = logging.getLogger(__name__)
DATA_DIR = ROOT_DIR / "data"
KEYWORDS_PATH = DATA_DIR / "keywords.json"
SOURCES_PATH = DATA_DIR / "sources.json"
STATE_PATH = DATA_DIR / "state.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_state() -> dict[str, list[str]]:
    if not STATE_PATH.exists():
        return {"used": []}
    state = _load_json(STATE_PATH)
    used = state.get("used", [])
    if not isinstance(used, list):
        used = []
    return {"used": [str(item) for item in used]}


def _save_state(state: dict[str, list[str]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _flatten_keywords(keywords_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    keywords: list[dict[str, Any]] = []
    for category in ("real_estate", "cdl", "dmv"):
        for item in keywords_data.get(category, []):
            keyword = dict(item)
            keyword.setdefault("category", category)
            keywords.append(keyword)
    return keywords


def _select_source_key(
    keyword: Mapping[str, Any],
    category_sources: Mapping[str, Any],
) -> str:
    category = str(keyword.get("category", ""))
    keyword_text = str(keyword.get("kw", "")).lower()
    state = keyword.get("state")

    if category == "cdl":
        if "air brake" in keyword_text:
            return "air_brakes"
        if "passenger" in keyword_text:
            return "passenger"
        if "hazmat" in keyword_text:
            return "hazmat"
        return "general"

    if category == "real_estate":
        if state and str(state) in category_sources:
            return str(state)
        if "math" in keyword_text:
            return "math"
        return "glossary"

    if category == "dmv":
        if state and str(state) in category_sources:
            return str(state)
        return "CA"

    return ""


def _read_source_text(keyword: Mapping[str, Any]) -> str:
    sources = _load_json(SOURCES_PATH)
    category = str(keyword.get("category", ""))
    category_sources = sources.get(category, {})
    if not isinstance(category_sources, Mapping):
        category_sources = {}

    source_key = _select_source_key(keyword, category_sources)
    source_value = category_sources.get(source_key)

    if not source_value:
        LOGGER.warning("source not configured for %s:%s", category, source_key)
        return ""

    source_path = Path(str(source_value))
    if not source_path.is_absolute():
        source_path = ROOT_DIR / source_path

    if not source_path.exists():
        LOGGER.warning("source file not found: %s", source_path)
        return ""

    return source_path.read_text(encoding="utf-8")


def _is_critical_warning(warning: str) -> bool:
    return warning.startswith(
        ("title too long", "meta out of range", "missing FAQPage"),
    )


def _run_pipeline() -> int:
    keywords_data = _load_json(KEYWORDS_PATH)
    state = _load_state()
    used = state["used"]
    used_set = set(used)

    all_keywords = _flatten_keywords(keywords_data)
    remaining = [
        kw for kw in all_keywords if str(kw.get("kw", "")) not in used_set
    ]

    if not remaining:
        LOGGER.info("all keywords used, resetting")
        used = []
        state = {"used": used}
        remaining = all_keywords

    skipped = 0
    for keyword in remaining:
        source_text = _read_source_text(keyword)
        cta_html = build_cta(keyword["category"], keyword.get("state"))

        try:
            article = generator.generate_article(keyword, source_text, cta_html)
        except Exception:
            LOGGER.exception("article generation failed")
            return 1

        warnings = seo_check.validate(article, keyword)
        critical_warnings = [w for w in warnings if _is_critical_warning(w)]
        for w in warnings:
            if w in critical_warnings:
                LOGGER.error(w)
            else:
                LOGGER.warning(w)

        if critical_warnings:
            LOGGER.error(
                "skipping keyword due to critical SEO warnings: %s",
                keyword.get("kw"),
            )
            skipped += 1
            continue

        article_path = integrator.save_article(article)
        integrator.update_index(
            article_path, article["title"], article["category"]
        )
        integrator.update_blog_index()
        integrator.update_sitemap(article_path)

        used.append(str(keyword["kw"]))
        state["used"] = used
        _save_state(state)

        LOGGER.info("published %s", article_path)
        return 0

    LOGGER.error(
        "no publishable article found; %d keyword(s) failed SEO validation",
        skipped,
    )
    return 2


def main() -> int:
    """Run one deterministic article generation and publishing cycle."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    try:
        return _run_pipeline()
    except Exception:
        LOGGER.exception("unexpected pipeline failure")
        return 1


if __name__ == "__main__":
    sys.exit(main())
