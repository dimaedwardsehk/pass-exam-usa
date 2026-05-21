from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import openai
from openai import OpenAI
from slugify import slugify

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.4
MAX_TOKENS = 3500
MAX_ATTEMPTS = 3
RETRY_DELAYS = (1, 2, 4)
STOPWORDS = ["the", "a", "in", "of", "and"]
SYSTEM_MESSAGE = (
    "You are an expert SEO content writer. Follow the user prompt strictly "
    "and return only the required two-block format."
)
META_PATTERN = re.compile(r"--META--\s*(.*?)\s*--END-META--", re.DOTALL)
ARTICLE_PATTERN = re.compile(r"<article\b[^>]*>.*?</article>", re.DOTALL)
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def generate_article(
    keyword: dict[str, Any],
    source_text: str,
    cta_html: str,
    canonical_base: str = "https://dimaedwardsehk.github.io/pass-exam-usa/blog/",
) -> dict[str, str | None]:
    """Generate one SEO article and return parsed metadata plus HTML."""
    keyword_text = str(keyword["kw"])
    category = str(keyword["category"])
    state = keyword["state"]
    h1 = str(keyword["h1_pattern"])
    title = str(keyword["title_pattern"])
    meta_description = str(keyword["meta_pattern"])
    state_val = str(state) if state else "null"
    today_iso = datetime.now(timezone.utc).date().isoformat()
    provisional_slug = _build_slug(title)
    canonical_url = canonical_base + provisional_slug + ".html"

    logger.info(
        "Starting article generation keyword=%s model=%s source_text_length=%d",
        keyword_text,
        MODEL_NAME,
        len(source_text),
    )

    prompt_template = _read_prompt_template()
    filled_prompt = _fill_prompt(
        prompt_template=prompt_template,
        keyword_text=keyword_text,
        state_val=state_val,
        category=category,
        h1=h1,
        title=title,
        meta_description=meta_description,
        source_text=source_text,
        cta_html=cta_html,
        canonical_url=canonical_url,
        today_iso=today_iso,
    )

    response_text = _request_article(filled_prompt)
    parsed = _parse_model_response(response_text)
    final_title = _trim_to_words(str(parsed["title"]), 60)
    final_meta_description = _validate_and_trim_meta(
        str(parsed["meta_description"])
    )
    final_slug = _normalize_slug(str(parsed["slug"]), final_title)
    final_canonical_url = canonical_base + final_slug + ".html"
    html = str(parsed["html"]).replace(canonical_url, final_canonical_url, 1)

    logger.info(
        "Finished article generation html_length=%d slug=%s title=%s",
        len(html),
        final_slug,
        final_title,
    )

    return {
        "html": html,
        "title": final_title,
        "meta_description": final_meta_description,
        "slug": final_slug,
        "canonical_url": final_canonical_url,
        "category": category,
        "state": state,
        "keyword": keyword_text,
    }


def _read_prompt_template() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    prompt_path = repo_root / "prompts" / "article_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def _fill_prompt(
    prompt_template: str,
    keyword_text: str,
    state_val: str,
    category: str,
    h1: str,
    title: str,
    meta_description: str,
    source_text: str,
    cta_html: str,
    canonical_url: str,
    today_iso: str,
) -> str:
    replacements = {
        "{keyword}": keyword_text,
        "{state}": state_val,
        "{category}": category,
        "{h1}": h1,
        "{title}": title,
        "{meta_description}": meta_description,
        "{source_text}": source_text,
        "{cta_html}": cta_html,
        "{canonical_url}": canonical_url,
        "{today_iso}": today_iso,
    }
    filled_prompt = prompt_template
    for placeholder, value in replacements.items():
        filled_prompt = filled_prompt.replace(placeholder, value)
    return filled_prompt


def _request_article(filled_prompt: str) -> str:
    client = OpenAI()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": filled_prompt},
                ],
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI response did not contain message content.")
            return content
        except (
            openai.APIError,
            openai.RateLimitError,
            openai.APIConnectionError,
            httpx.TimeoutException,
        ) as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = RETRY_DELAYS[attempt - 1]
            logger.warning(
                "OpenAI request failed on attempt %d/%d; retrying in %d seconds: %s",
                attempt,
                MAX_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)

    raise RuntimeError("OpenAI retry loop ended without returning a response.")


def _parse_model_response(response_text: str) -> dict[str, str]:
    preview = response_text[:500]
    meta_match = META_PATTERN.search(response_text)
    if not meta_match:
        raise ValueError(
            "Model response is missing the --META-- block. "
            f"First 500 characters: {preview!r}"
        )

    try:
        meta = json.loads(meta_match.group(1).strip())
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Model response contains invalid JSON in the --META-- block. "
            f"First 500 characters: {preview!r}"
        ) from exc

    for field_name in ("title", "meta_description", "slug"):
        if field_name not in meta:
            raise ValueError(
                f"Model response meta block is missing {field_name!r}. "
                f"First 500 characters: {preview!r}"
            )

    article_match = ARTICLE_PATTERN.search(response_text)
    if not article_match:
        raise ValueError(
            "Model response is missing the <article>...</article> block. "
            f"First 500 characters: {preview!r}"
        )

    return {
        "title": str(meta["title"]),
        "meta_description": str(meta["meta_description"]),
        "slug": str(meta["slug"]),
        "html": article_match.group(0),
    }


def _validate_and_trim_meta(meta_description: str) -> str:
    clean_meta = " ".join(meta_description.strip().split())
    if len(clean_meta) < 120:
        raise ValueError(
            "Model meta_description is shorter than 120 characters: "
            f"{len(clean_meta)}"
        )
    if len(clean_meta) <= 155:
        return clean_meta

    trimmed_meta = _trim_to_words(clean_meta, 155)
    if len(trimmed_meta) < 120:
        raise ValueError(
            "Trimmed meta_description is shorter than 120 characters: "
            f"{len(trimmed_meta)}"
        )
    return trimmed_meta


def _normalize_slug(slug: str, title: str) -> str:
    clean_slug = slug.strip()
    if _is_valid_slug(clean_slug):
        return clean_slug
    rebuilt_slug = _build_slug(title)
    if not _is_valid_slug(rebuilt_slug):
        raise ValueError(f"Could not build a valid slug from title: {title!r}")
    return rebuilt_slug


def _trim_to_words(text: str, max_length: int) -> str:
    clean_text = " ".join(text.strip().split())
    if len(clean_text) <= max_length:
        return clean_text

    words: list[str] = []
    for word in clean_text.split():
        candidate = " ".join([*words, word])
        if len(candidate) > max_length:
            break
        words.append(word)
    return " ".join(words)


def _build_slug(title: str) -> str:
    return slugify(
        title,
        max_length=60,
        word_boundary=True,
        stopwords=STOPWORDS,
    )


def _is_valid_slug(slug: str) -> bool:
    return len(slug) <= 60 and SLUG_PATTERN.fullmatch(slug) is not None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    demo_keyword = {
        "kw": "cdl air brakes practice test",
        "state": None,
        "intent": "transactional",
        "category": "cdl",
        "h1_pattern": "CDL Air Brakes Practice Test Guide for 2026",
        "title_pattern": "CDL Air Brakes Practice Test (2026)",
        "meta_pattern": (
            "Study CDL air brakes for 2026 with practice questions, system "
            "vocabulary, inspection topics, and test-day review tips for drivers."
        ),
    }
    demo_source = (
        "Air brakes use compressed air to stop heavy vehicles. Pre-trip "
        "inspection includes checking the air compressor, governor, and brake "
        "pedal. Drivers must learn the difference between service brakes, "
        "parking brakes, and emergency brakes."
    )
    demo_cta = (
        '<aside class="cta"><h3>Ready to practice?</h3><p>Get web access to '
        'our CDL trainer for $9.99.</p><a href="https://dimaedwardsehk.github.io/'
        'pass-exam-usa/#cdl">Start Practicing</a></aside>'
    )
    result = generate_article(demo_keyword, demo_source, demo_cta)
    print("TITLE:", result["title"])
    print("META :", result["meta_description"])
    print("SLUG :", result["slug"])
    print("URL  :", result["canonical_url"])
    print("HTML head (500):", result["html"][:500])
