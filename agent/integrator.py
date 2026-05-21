"""SEO integrator: writes article files, updates index.html and sitemap.xml."""

from __future__ import annotations

import html
import logging
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://dimaedwardsehk.github.io/pass-exam-usa/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)

_TEMPLATE_DEFAULT = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<meta name="description" content="{{META}}">
<link rel="canonical" href="{{CANONICAL}}">
<link rel="stylesheet" href="../style.css">
<meta property="og:title" content="{{TITLE}}">
<meta property="og:description" content="{{META}}">
<meta property="og:type" content="article">
<meta property="og:url" content="{{CANONICAL}}">
</head>
<body>
<header><a href="../index.html">&larr; Back to Pass Exam USA</a></header>
<main data-category="{{CATEGORY}}">
{{ARTICLE_HTML}}
</main>
<footer><p>&copy; Pass Exam USA</p></footer>
</body>
</html>
"""

_BLOG_BLOCK_DEFAULT = (
    "<!-- BLOG_LIST_START -->\n"
    '<section class="blog-list" aria-label="Latest articles">\n'
    "  <h2>Latest articles</h2>\n"
    "  <ul></ul>\n"
    "</section>\n"
    "<!-- BLOG_LIST_END -->"
)


def _ensure_template() -> Path:
    """Return the path to blog/_template.html, creating it from default if missing."""
    template_path = ROOT / "blog" / "_template.html"
    if not template_path.exists():
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(_TEMPLATE_DEFAULT, encoding="utf-8")
        logger.info(
            "Created default template at %s",
            template_path.relative_to(ROOT).as_posix(),
        )
    return template_path


def _resolve_unique_path(slug: str) -> Path:
    """Return a non-existing blog/{slug}.html path, adding -2, -3, ... suffixes if needed."""
    blog_dir = ROOT / "blog"
    blog_dir.mkdir(parents=True, exist_ok=True)
    candidate = blog_dir / f"{slug}.html"
    counter = 2
    while candidate.exists():
        candidate = blog_dir / f"{slug}-{counter}.html"
        counter += 1
    return candidate


def save_article(article: dict) -> str:
    """Render the article via the blog template and save it under blog/, returning the relative path."""
    template_path = _ensure_template()
    template = template_path.read_text(encoding="utf-8")
    target = _resolve_unique_path(article["slug"])

    rendered = template
    rendered = rendered.replace("{{TITLE}}", html.escape(article["title"]))
    rendered = rendered.replace("{{META}}", html.escape(article["meta_description"]))
    rendered = rendered.replace("{{CANONICAL}}", article["canonical_url"])
    rendered = rendered.replace("{{CATEGORY}}", article["category"])
    rendered = rendered.replace("{{ARTICLE_HTML}}", article["html"])

    target.write_text(rendered, encoding="utf-8")
    rel = target.relative_to(ROOT).as_posix()
    logger.info("Saved article: %s", rel)
    return rel


def update_index(article_path: str, title: str, category: str) -> None:
    """Insert a new article link as the first <li> in index.html between blog list markers (max 20 items)."""
    index_path = ROOT / "index.html"

    if not index_path.exists():
        content = (
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            "<title>Pass Exam USA</title></head><body><main>\n"
            f"{_BLOG_BLOCK_DEFAULT}\n"
            "</main></body></html>"
        )
        index_path.write_text(content, encoding="utf-8")
        logger.info("Created index.html with blog list block")
    else:
        content = index_path.read_text(encoding="utf-8")

    if "<!-- BLOG_LIST_START -->" not in content or "<!-- BLOG_LIST_END -->" not in content:
        block = "\n" + _BLOG_BLOCK_DEFAULT + "\n"
        if "</main>" in content:
            content = content.replace("</main>", block + "</main>", 1)
        elif "</body>" in content:
            content = content.replace("</body>", block + "</body>", 1)
        else:
            content = content + "\n" + block
        logger.info("Inserted blog list markers into index.html")

    block_pattern = re.compile(
        r"(<!-- BLOG_LIST_START -->)(.*?)(<!-- BLOG_LIST_END -->)",
        re.DOTALL,
    )
    match = block_pattern.search(content)
    if match is None:
        logger.error("Blog list markers not found after insertion attempt; aborting index update")
        return

    block_inner = match.group(2)

    new_li = (
        f'<li class="blog-item" data-category="{html.escape(category)}">'
        f'<a href="{article_path}">{html.escape(title)}</a></li>'
    )

    li_pattern = re.compile(r"<li\b[^>]*>.*?</li>", re.DOTALL)
    existing_lis = li_pattern.findall(block_inner)
    new_lis = [new_li] + existing_lis
    if len(new_lis) > 20:
        new_lis = new_lis[:20]

    items_html = "\n    ".join(new_lis)

    ul_pattern = re.compile(r"(<ul[^>]*>)(.*?)(</ul>)", re.DOTALL)
    if ul_pattern.search(block_inner):
        new_inner = ul_pattern.sub(
            lambda m: f"{m.group(1)}\n    {items_html}\n  {m.group(3)}",
            block_inner,
            count=1,
        )
    else:
        new_inner = (
            '\n<section class="blog-list" aria-label="Latest articles">\n'
            "  <h2>Latest articles</h2>\n"
            f"  <ul>\n    {items_html}\n  </ul>\n"
            "</section>\n"
        )

    new_content = content[: match.start(2)] + new_inner + content[match.end(2) :]
    index_path.write_text(new_content, encoding="utf-8")
    logger.info("Updated index.html with link to %s", article_path)


def update_sitemap(article_path: str) -> None:
    """Add or refresh a <url> entry in sitemap.xml for the given article path."""
    sitemap_path = ROOT / "sitemap.xml"

    if sitemap_path.exists():
        try:
            tree = ET.parse(sitemap_path)
            root_elem = tree.getroot()
        except ET.ParseError as exc:
            logger.warning("sitemap.xml is malformed (%s); recreating", exc)
            root_elem = ET.Element(f"{{{SITEMAP_NS}}}urlset")
            tree = ET.ElementTree(root_elem)
    else:
        root_elem = ET.Element(f"{{{SITEMAP_NS}}}urlset")
        tree = ET.ElementTree(root_elem)
        logger.info("Creating new sitemap.xml")

    full_url = BASE_URL + article_path
    today_iso = date.today().isoformat()

    ns = {"sm": SITEMAP_NS}
    existing = None
    for url_elem in root_elem.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        if loc is not None and (loc.text or "").strip() == full_url:
            existing = url_elem
            break

    if existing is not None:
        lastmod = existing.find("sm:lastmod", ns)
        if lastmod is None:
            lastmod = ET.SubElement(existing, f"{{{SITEMAP_NS}}}lastmod")
        lastmod.text = today_iso
        logger.info("Refreshed lastmod for existing sitemap URL: %s", full_url)
    else:
        url_elem = ET.SubElement(root_elem, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}loc").text = full_url
        ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}lastmod").text = today_iso
        ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}changefreq").text = "monthly"
        ET.SubElement(url_elem, f"{{{SITEMAP_NS}}}priority").text = "0.7"
        logger.info("Added new sitemap URL: %s", full_url)

    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    fake = {
        "html": "<article><h1>Demo Article</h1><p>Lead paragraph for demo.</p><h2>Section</h2><p>Body.</p></article>",
        "title": "Demo Article About CDL Air Brakes",
        "meta_description": "Demo meta description for integrator self-test in 2026, long enough to satisfy the 120 to 155 character validation rule for SEO.",
        "slug": "demo-article-cdl-air-brakes",
        "canonical_url": "https://dimaedwardsehk.github.io/pass-exam-usa/blog/demo-article-cdl-air-brakes.html",
        "category": "cdl",
        "state": None,
        "keyword": "cdl air brakes practice test",
    }
    path = save_article(fake)
    update_index(path, fake["title"], fake["category"])
    update_sitemap(path)
    print("OK:", path)
    sys.exit(0)
