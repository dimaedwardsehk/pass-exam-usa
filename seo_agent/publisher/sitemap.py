"""Sitemap.xml generator — auto-discovers published content and builds sitemap."""
from __future__ import annotations
import datetime
from .layouts import SITE_URL


def generate_sitemap(published_paths: list[str], base_url: str = SITE_URL) -> str:
    """Generate a sitemap.xml from a list of published file paths.
    
    Args:
        published_paths: List of paths like ["blog/slug.html", "dictionary/term.html"]
        base_url: Base URL of the site
    
    Returns:
        Complete sitemap.xml content as string
    """
    today = datetime.date.today().isoformat()

    urls = [
        # Homepage always included
        _url_entry(f"{base_url}/", today, "1.0", "weekly"),
    ]

    for path in sorted(published_paths):
        # Determine priority based on content type
        if path.startswith("blog/"):
            priority = "0.8"
            changefreq = "monthly"
        elif path.startswith("faq/"):
            priority = "0.7"
            changefreq = "monthly"
        elif path.startswith("dictionary/"):
            priority = "0.6"
            changefreq = "yearly"
        else:
            priority = "0.5"
            changefreq = "monthly"

        full_url = f"{base_url}/{path}"
        urls.append(_url_entry(full_url, today, priority, changefreq))

    xml_body = "\n".join(urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_body}
</urlset>"""


def _url_entry(loc: str, lastmod: str, priority: str, changefreq: str) -> str:
    return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
