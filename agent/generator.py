from __future__ import annotations

import json
import os
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

# --- Provider configuration -------------------------------------------------
# The agent rotates over a POOL of providers (the "revolver"). The pool can be
# configured in EITHER of two places (checked in this order):
#
#   1. data/providers.json  -- a plain JSON file committed to the repo. This is
#      the simplest option and needs NO GitHub Actions secrets and NO workflow
#      changes. Format: a JSON array of objects, e.g.
#        [
#          {"name": "groq", "base_url": "https://api.groq.com/openai/v1",
#           "model": "llama-3.3-70b-versatile", "api_key": "gsk_..."}
#        ]
#      NOTE: anything committed to a public repo is publicly visible. Use this
#      only for disposable/free keys, and rotate them if needed.
#
#   2. The AI_PROVIDERS environment variable (same JSON array format), typically
#      wired from a GitHub Actions secret.
#
# If neither is present, it falls back to a single provider built from
# AI_API_KEY / AI_BASE_URL / AI_MODEL.
#
# The code tries each provider in order and returns the first success. If a
# provider fails, its exact error is recorded and the next one is tried.
DEFAULT_BASE_URL = "https://api.pioneer.ai/v1"
DEFAULT_MODEL = "5a01010b-395b-48c7-b931-0ece022b1e12"
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
    canonical_base: str = "https://passexamusa.org/blog/",
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
        "Starting article generation keyword=%s source_text_length=%d",
        keyword_text,
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


def _coerce_providers(data: Any) -> list[dict[str, str]]:
    """Normalize a parsed JSON array into a clean provider list."""
    if not isinstance(data, list):
        raise RuntimeError("Providers config must be a JSON array of objects.")
    providers: list[dict[str, str]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        api_key = str(item.get("api_key") or item.get("key") or "").strip()
        if not api_key or api_key.startswith("$"):
            continue
        providers.append(
            {
                "name": str(item.get("name") or f"provider_{idx + 1}"),
                "api_key": api_key,
                "base_url": str(item.get("base_url") or DEFAULT_BASE_URL).strip(),
                "model": str(item.get("model") or DEFAULT_MODEL).strip(),
            }
        )
    return providers


def _load_providers() -> list[dict[str, str]]:
    """Build the ordered provider pool (the revolver).

    Priority:
      1. data/providers.json committed in the repo (a JSON array). Needs no
         GitHub Actions secret and no workflow expression syntax.
      2. The AI_PROVIDERS environment variable (a JSON array).
      3. Legacy single provider from AI_API_KEY / AI_BASE_URL / AI_MODEL.
    """
    # 1. Committed providers file.
    repo_root = Path(__file__).resolve().parent.parent
    providers_file = repo_root / "data" / "providers.json"
    if providers_file.exists():
        try:
            file_data = json.loads(providers_file.read_text(encoding="utf-8"))
            file_providers = _coerce_providers(file_data)
        except (json.JSONDecodeError, OSError, RuntimeError) as exc:
            logger.warning("Ignoring invalid data/providers.json: %s", exc)
            file_providers = []
        if file_providers:
            logger.info(
                "Loaded %d provider(s) from data/providers.json.",
                len(file_providers),
            )
            return file_providers

    # 2. AI_PROVIDERS env var (only treat as config if it looks like JSON).
    raw = os.getenv("AI_PROVIDERS")
    if raw and raw.strip().startswith("["):
        try:
            env_data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"AI_PROVIDERS is not valid JSON: {exc}")
        env_providers = _coerce_providers(env_data)
        if env_providers:
            return env_providers
        raise RuntimeError(
            "AI_PROVIDERS is set but contains no usable provider (each entry "
            "needs at least an 'api_key')."
        )

    # 3. Legacy single provider from individual env vars.
    legacy_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if legacy_key and legacy_key.strip() and not legacy_key.strip().startswith("$"):
        return [
            {
                "name": "legacy_env",
                "api_key": legacy_key.strip(),
                "base_url": (os.getenv("AI_BASE_URL") or DEFAULT_BASE_URL).strip(),
                "model": (os.getenv("AI_MODEL") or DEFAULT_MODEL).strip(),
            }
        ]

    raise RuntimeError(
        "No AI providers configured. Add data/providers.json (a JSON array) or "
        "set the AI_PROVIDERS secret."
    )


def _request_article(filled_prompt: str) -> str:
    """Rotate over the provider pool, returning the first successful response.

    Every provider's outcome is recorded so the failure log shows exactly what
    each key returned (auth ok / quota / billing / network), ending guesswork.
    """
    providers = _load_providers()
    results: list[str] = []

    for provider in providers:
        name = provider["name"]
        try:
            content = _request_from_provider(provider, filled_prompt)
            logger.info("Provider %s succeeded.", name)
            return content
        except Exception as exc:  # noqa: BLE001 - record and try the next key
            detail = f"[{name}] {type(exc).__name__}: {exc}"
            results.append(detail)
            logger.warning("Provider failed, rotating to next: %s", detail)
            continue

    raise RuntimeError(
        "All "
        + str(len(providers))
        + " provider(s) failed. Per-provider results:\n"
        + "\n".join(results)
    )


def _request_from_provider(provider: dict[str, str], filled_prompt: str) -> str:
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])
    model = provider["model"]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": filled_prompt},
                ],
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Response did not contain message content.")
            return content
        except (openai.AuthenticationError, openai.PermissionDeniedError):
            # Permanent for this key (bad key / billing not activated).
            # Do not retry - let the revolver move to the next provider.
            raise
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
                "Request failed on attempt %d/%d; retrying in %d seconds: %s",
                attempt,
                MAX_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)

    raise RuntimeError("Retry loop ended without returning a response.")


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
