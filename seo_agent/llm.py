"""LLM client with built-in rate limiter and retry logic."""
from __future__ import annotations
import json
import time
import threading
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket style rate limiter — enforces min interval between calls."""

    def __init__(self, rpm: int = 10, min_interval: float = 6.0):
        self.rpm = rpm
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call: float = 0.0
        self._calls_this_minute: list[float] = []

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            # Enforce min interval
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiter: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

            # Enforce RPM
            cutoff = time.time() - 60
            self._calls_this_minute = [t for t in self._calls_this_minute if t > cutoff]
            if len(self._calls_this_minute) >= self.rpm:
                wait_until = self._calls_this_minute[0] + 60
                sleep_time = wait_until - time.time()
                if sleep_time > 0:
                    logger.info(f"Rate limiter: RPM cap hit, sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)

            self._last_call = time.time()
            self._calls_this_minute.append(self._last_call)


class LLMClient:
    """OpenAI chat completions client with rate limiting and retries."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 temperature: float = 0.7, rpm: int = 10, min_interval: float = 6.0,
                 max_retries: int = 5):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install openai  — required for LLM calls")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self._limiter = RateLimiter(rpm=rpm, min_interval=min_interval)

    def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Generate a completion with rate limiting and exponential backoff retries."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, self.max_retries + 1):
            self._limiter.wait()
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                logger.debug(f"LLM response ({len(content)} chars)")
                return content
            except Exception as e:
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str or "too many" in error_str:
                    backoff = min(2 ** attempt * 5, 120)
                    logger.warning(f"Rate limited (attempt {attempt}/{self.max_retries}), backing off {backoff}s")
                    time.sleep(backoff)
                elif "500" in error_str or "502" in error_str or "503" in error_str:
                    backoff = min(2 ** attempt * 3, 60)
                    logger.warning(f"Server error (attempt {attempt}/{self.max_retries}), retrying in {backoff}s")
                    time.sleep(backoff)
                else:
                    logger.error(f"LLM error: {e}")
                    raise
        raise RuntimeError(f"LLM call failed after {self.max_retries} retries")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Generate and parse JSON response."""
        raw = self.generate(system_prompt, user_prompt, json_mode=True)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        return json.loads(cleaned)
