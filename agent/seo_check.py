"""SEO validation for generated articles."""

from __future__ import annotations

import re
from html import unescape

import textstat

_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_H2_RE = re.compile(r"<h2\b[^>]*>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_LD_JSON_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>'
    r".*?</script>",
    re.IGNORECASE | re.DOTALL,
)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _plain_text(html_content: str) -> str:
    """Strip HTML tags and decode entities."""
    return unescape(_HTML_TAG_RE.sub(" ", html_content))


def _keyword_count(text: str, keyword: str) -> int:
    """Count case-insensitive occurrences of keyword in text."""
    if not keyword:
        return 0
    return len(re.findall(re.escape(keyword), text, re.IGNORECASE))


def validate(article: dict, keyword: dict) -> list[str]:
    """Validate generated article SEO constraints and return warnings."""
    warnings: list[str] = []

    title = str(article["title"])
    if len(title) > 60:
        warnings.append(f"title too long: {len(title)} chars")

    meta_description = str(article["meta_description"])
    meta_length = len(meta_description)
    if meta_length < 120 or meta_length > 155:
        warnings.append(f"meta out of range: {meta_length} chars")

    html_content = str(article["html"])
    keyword_text = str(keyword["kw"]).strip()

    first_h1 = _H1_RE.search(html_content)
    if first_h1 is None:
        warnings.append("missing h1")
    else:
        h1_text = _plain_text(first_h1.group(1))
        h1_count = _keyword_count(h1_text, keyword_text)
        if h1_count > 1:
            warnings.append(f"keyword repeated in h1: {h1_count} times")

    keyword_total = _keyword_count(html_content, keyword_text)
    if keyword_total < 3:
        warnings.append("keyword underused")
    elif keyword_total > 7:
        warnings.append("keyword overused")

    h2_count = len(_H2_RE.findall(html_content))
    if h2_count < 4:
        warnings.append(f"not enough h2 tags: {h2_count}")

    faq_scripts = [
        script for script in _LD_JSON_RE.findall(html_content)
        if "FAQPage" in script
    ]
    if len(faq_scripts) != 1:
        warnings.append(f"missing FAQPage structured data: found {len(faq_scripts)}")

    clean_text = _plain_text(html_content)
    flesch_score = textstat.flesch_reading_ease(clean_text)
    if flesch_score < 50 or flesch_score > 75:
        warnings.append(f"flesch reading ease out of range: {flesch_score:.1f}")

    slug = str(article["slug"])
    if len(slug) > 60:
        warnings.append(f"slug too long: {len(slug)} chars")
    if _SLUG_RE.fullmatch(slug) is None:
        warnings.append(f"invalid slug: {slug}")

    return warnings
