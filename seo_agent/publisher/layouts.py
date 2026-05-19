"""HTML layout renderers for different content types on GitHub Pages (flat layout)."""
from __future__ import annotations

SITE_NAME = "Real Estate Exam Prep"
SITE_URL = "https://dimaedwardsehk.github.io/pass-exam-usa"


def _base_html(title: str, meta_desc: str, body_html: str, json_ld: str | None = None) -> str:
    """Base HTML template for all generated pages."""
    ld_block = ""
    if json_ld:
        ld_block = f'<script type="application/ld+json">\n{json_ld}\n</script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{meta_desc}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:type" content="article">
    <link rel="canonical" href="{SITE_URL}">
    {ld_block}
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a2e; font-size: 2em; }}
        h2 {{ color: #16213e; margin-top: 2em; }}
        h3 {{ color: #0f3460; }}
        a {{ color: #e94560; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .nav {{ padding: 15px 0; border-bottom: 1px solid #eee; margin-bottom: 30px; }}
        .nav a {{ margin-right: 20px; font-weight: 500; }}
        .back-link {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}
        ul, ol {{ padding-left: 1.5em; }}
        li {{ margin-bottom: 0.5em; }}
        .faq-item {{ margin-bottom: 1.5em; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .faq-item h3 {{ margin-top: 0; color: #e94560; }}
    </style>
</head>
<body>
    <nav class="nav">
        <a href="{SITE_URL}/">Home</a>
        <a href="{SITE_URL}/blog/">Blog</a>
        <a href="{SITE_URL}/dictionary/">Dictionary</a>
        <a href="{SITE_URL}/faq/">FAQ</a>
    </nav>
    {body_html}
    <div class="back-link">
        <a href="{SITE_URL}/">&larr; Back to Home</a>
    </div>
</body>
</html>"""


def render_article(data: dict) -> tuple[str, str]:
    """Render article → (file_path, html_content)."""
    slug = data.get("slug", "untitled")
    title = data.get("title", "Article")
    meta_desc = data.get("meta_description", "")
    h1 = data.get("h1", title)
    content = data.get("content_html", "")

    body = f"<h1>{h1}</h1>\n{content}"
    html = _base_html(title, meta_desc, body)
    return f"blog/{slug}.html", html


def render_glossary(data: dict) -> tuple[str, str]:
    """Render glossary term → (file_path, html_content)."""
    slug = data.get("slug", "term")
    term = data.get("term", "Term")
    short_def = data.get("short_definition", "")
    long_def = data.get("long_definition", "")
    example = data.get("example", "")
    related = data.get("related_terms", [])

    body_parts = [
        f"<h1>{term}</h1>",
        f"<p><strong>{short_def}</strong></p>",
        f"<h2>Detailed Definition</h2>",
        f"<p>{long_def}</p>",
    ]
    if example:
        body_parts.append(f"<h2>Example</h2><p>{example}</p>")
    if related:
        links = ", ".join(f'<a href="/pass-exam-usa/dictionary/{r.lower().replace(" ", "-")}.html">{r}</a>' for r in related)
        body_parts.append(f"<h2>Related Terms</h2><p>{links}</p>")

    html = _base_html(f"{term} — Real Estate Definition", short_def, "\n".join(body_parts))
    return f"dictionary/{slug}.html", html


def render_faq(data: dict) -> tuple[str, str]:
    """Render FAQ page → (file_path, html_content)."""
    slug = data.get("slug", "faq")
    topic = data.get("topic", "FAQ")
    faqs = data.get("faqs", [])
    json_ld = data.get("json_ld")

    body_parts = [f"<h1>{topic} — Frequently Asked Questions</h1>"]
    for faq in faqs:
        body_parts.append(
            f'<div class="faq-item">'
            f'<h3>{faq["question"]}</h3>'
            f'<p>{faq["answer"]}</p>'
            f'</div>'
        )

    html = _base_html(f"{topic} FAQ", f"Answers to common questions about {topic}",
                      "\n".join(body_parts), json_ld=json_ld)
    return f"faq/{slug}.html", html


def render_html(data: dict) -> tuple[str, str]:
    """Route to the correct renderer based on content type."""
    content_type = data.get("type", "article")
    if content_type == "glossary":
        return render_glossary(data)
    elif content_type == "faq":
        return render_faq(data)
    else:
        return render_article(data)
