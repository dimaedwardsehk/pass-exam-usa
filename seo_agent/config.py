"""Configuration — loaded from environment / .env file."""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Settings:
    # LLM
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))

    # Rate limiting
    llm_rpm: int = field(default_factory=lambda: int(os.getenv("LLM_RPM", "10")))
    llm_min_interval: float = field(default_factory=lambda: float(os.getenv("LLM_MIN_INTERVAL", "6.0")))

    # Publisher
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    publish_repo_owner: str = field(default_factory=lambda: os.getenv("PUBLISH_REPO_OWNER", ""))
    publish_repo_name: str = field(default_factory=lambda: os.getenv("PUBLISH_REPO_NAME", ""))
    publish_layout: str = field(default_factory=lambda: os.getenv("PUBLISH_LAYOUT", "flat"))
    publish_base_branch: str = field(default_factory=lambda: os.getenv("PUBLISH_BASE_BRANCH", "main"))

    # Output
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))

    def validate(self) -> list[str]:
        errors = []
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        return errors


settings = Settings()
