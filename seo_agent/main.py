"""CLI entry point — run: python -m seo_agent.main"""
from __future__ import annotations
import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from .config import settings
from .llm import LLMClient
from .validators import validate
from .publisher import GitHubPublisher, render_html, generate_sitemap
from .publisher.github_client import FileToCommit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_topics(path: str) -> list[dict]:
    """Load topics from CSV (columns: topic, type, state, keywords)."""
    topics = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topics.append({
                "topic": row.get("topic", "").strip(),
                "type": row.get("type", "article").strip(),
                "state": row.get("state", "").strip() or None,
                "keywords": [k.strip() for k in row.get("keywords", "").split(";") if k.strip()],
            })
    return topics


def generate_one(client: LLMClient, item: dict) -> dict | None:
    """Generate one piece of content based on type."""
    from .generators import generate_article, generate_meta, generate_faq, generate_glossary

    topic = item["topic"]
    state = item["state"]
    content_type = item["type"]
    keywords = item.get("keywords", [])

    try:
        if content_type == "article":
            return generate_article(client, topic, state=state, keywords=keywords)
        elif content_type == "faq":
            return generate_faq(client, topic, state=state)
        elif content_type == "glossary":
            return generate_glossary(client, topic, state=state)
        elif content_type == "meta":
            return generate_meta(client, topic, topic, state=state)
        else:
            logger.warning(f"Unknown type '{content_type}', treating as article")
            return generate_article(client, topic, state=state, keywords=keywords)
    except Exception as e:
        logger.error(f"Generation failed for '{topic}': {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="SEO Agent — generate and publish content")
    parser.add_argument("--topics", required=True, help="Path to topics CSV file")
    parser.add_argument("--only", help="Generate only this type: article|faq|glossary|meta")
    parser.add_argument("--limit", type=int, help="Max items to generate")
    parser.add_argument("--publish", action="store_true", help="Publish to GitHub via PR")
    parser.add_argument("--dry-run-publish", action="store_true", help="Simulate publish (no API calls)")
    parser.add_argument("--skip-invalid", action="store_true", help="Skip items that fail validation")
    parser.add_argument("--output", default="output", help="Local output directory")
    args = parser.parse_args()

    # Validate config
    errors = settings.validate()
    if errors:
        logger.error(f"Config errors: {errors}")
        sys.exit(1)

    # Load topics
    topics = load_topics(args.topics)
    if args.only:
        topics = [t for t in topics if t["type"] == args.only]
    if args.limit:
        topics = topics[:args.limit]

    logger.info(f"Loaded {len(topics)} topics to process")

    # Init LLM client with rate limiter
    client = LLMClient(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        rpm=settings.llm_rpm,
        min_interval=settings.llm_min_interval,
    )

    # Generate content
    results: list[dict] = []
    for i, item in enumerate(topics, 1):
        logger.info(f"[{i}/{len(topics)}] Generating {item['type']}: {item['topic']}")
        data = generate_one(client, item)
        if data is None:
            continue

        # Validate
        report = validate(data)
        if not report.passed:
            logger.warning(f"Validation failed for '{item['topic']}':\n{report.summary()}")
            if args.skip_invalid:
                continue
        elif report.issues:
            logger.info(f"Warnings for '{item['topic']}':\n{report.summary()}")

        data["_validation"] = report.summary()
        results.append(data)

    logger.info(f"Generated {len(results)} items successfully")

    # Save locally
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for data in results:
        file_path, html = render_html(data)
        local_path = output_dir / file_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(html, encoding="utf-8")
        logger.info(f"Saved: {local_path}")

    # Publish
    if args.publish or args.dry_run_publish:
        if not args.dry_run_publish and not settings.github_token:
            logger.error("GITHUB_TOKEN required for publishing")
            sys.exit(1)

        # Prepare files for commit
        files_to_commit: list[FileToCommit] = []
        published_paths: list[str] = []

        for data in results:
            file_path, html = render_html(data)
            files_to_commit.append(FileToCommit(path=file_path, content=html))
            published_paths.append(file_path)

        # Generate and include sitemap
        sitemap_content = generate_sitemap(published_paths)
        files_to_commit.append(FileToCommit(path="sitemap.xml", content=sitemap_content))

        # Build PR body
        items_summary = "\n".join(
            f"- `{f.path}`" for f in files_to_commit
        )
        validation_notes = "\n".join(
            f"- **{r.get('title', r.get('term', 'item'))}**: {r.get('_validation', 'OK')}"
            for r in results
        )
        pr_body = (
            f"## SEO Content Update\n\n"
            f"**Generated {len(results)} items:**\n{items_summary}\n\n"
            f"### Validation\n{validation_notes}\n\n"
            f"---\n*Auto-generated by SEO Agent v1.0*"
        )

        if args.dry_run_publish:
            logger.info(f"[DRY RUN] Would publish {len(files_to_commit)} files")
            for f in files_to_commit:
                logger.info(f"  → {f.path}")
            logger.info(f"PR body preview:\n{pr_body}")
        else:
            publisher = GitHubPublisher(
                token=settings.github_token,
                owner=settings.publish_repo_owner,
                repo=settings.publish_repo_name,
                base_branch=settings.publish_base_branch,
            )
            result = publisher.publish(
                files=files_to_commit,
                title=f"SEO: Add {len(results)} content items",
                body=pr_body,
            )
            logger.info(f"✓ Published! PR: {result.pr_url}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
