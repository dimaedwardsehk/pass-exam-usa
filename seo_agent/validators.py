"""Content validators — checks SEO compliance before publishing."""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ValidationReport:
    passed: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_error(self, msg: str):
        self.issues.append(ValidationIssue("error", msg))
        self.passed = False

    def add_warning(self, msg: str):
        self.issues.append(ValidationIssue("warning", msg))

    def summary(self) -> str:
        if self.passed and not self.issues:
            return "✓ All checks passed"
        lines = []
        for issue in self.issues:
            icon = "❌" if issue.severity == "error" else "⚠️"
            lines.append(f"{icon} {issue.message}")
        return "\n".join(lines)


def validate_article(data: dict) -> ValidationReport:
    """Validate a generated article."""
    report = ValidationReport()

    # Title length
    title = data.get("title", "")
    if len(title) > 60:
        report.add_error(f"Title too long: {len(title)} chars (max 60)")
    elif len(title) < 20:
        report.add_warning(f"Title very short: {len(title)} chars")

    # Meta description length
    desc = data.get("meta_description", "")
    if len(desc) > 160:
        report.add_error(f"Meta description too long: {len(desc)} chars (max 160)")
    elif len(desc) < 100:
        report.add_warning(f"Meta description short: {len(desc)} chars (aim for 140-155)")

    # Content exists and has substance
    content = data.get("content_html", "")
    if not content:
        report.add_error("No content_html generated")
    else:
        # Word count check
        text_only = re.sub(r"<[^>]+>", " ", content)
        words = text_only.split()
        word_count = len(words)
        if word_count < 800:
            report.add_warning(f"Content short: ~{word_count} words (target 900-1400)")
        elif word_count > 1600:
            report.add_warning(f"Content long: ~{word_count} words (target 900-1400)")

        # Keyword density check
        keywords = data.get("keywords", [])
        if keywords and word_count > 0:
            primary = keywords[0].lower()
            density = text_only.lower().count(primary) / word_count * 100
            if density > 2.5:
                report.add_error(f"Keyword '{primary}' density too high: {density:.1f}% (max 2.5%)")

    # H2 headings present
    if "<h2" not in content.lower():
        report.add_warning("No H2 headings found in content")

    return report


def validate_meta(data: dict) -> ValidationReport:
    """Validate meta tag generation."""
    report = ValidationReport()

    title = data.get("title", "")
    if len(title) > 60:
        report.add_error(f"Title too long: {len(title)} chars (max 60)")
    if not title:
        report.add_error("Missing title")

    desc = data.get("description", "")
    if len(desc) > 160:
        report.add_error(f"Description too long: {len(desc)} chars (max 160)")
    if not desc:
        report.add_error("Missing description")

    return report


def validate_faq(data: dict) -> ValidationReport:
    """Validate FAQ generation."""
    report = ValidationReport()

    faqs = data.get("faqs", [])
    if len(faqs) < 3:
        report.add_error(f"Too few FAQs: {len(faqs)} (minimum 5)")
    elif len(faqs) < 5:
        report.add_warning(f"Only {len(faqs)} FAQs (target 5-8)")

    for i, faq in enumerate(faqs):
        if not faq.get("question"):
            report.add_error(f"FAQ #{i+1}: missing question")
        if not faq.get("answer"):
            report.add_error(f"FAQ #{i+1}: missing answer")
        elif len(faq["answer"]) < 30:
            report.add_warning(f"FAQ #{i+1}: answer very short")

    if not data.get("json_ld"):
        report.add_warning("No JSON-LD schema generated")

    return report


def validate_glossary(data: dict) -> ValidationReport:
    """Validate glossary entry."""
    report = ValidationReport()

    if not data.get("term"):
        report.add_error("Missing term")
    if not data.get("short_definition"):
        report.add_error("Missing short_definition")
    elif len(data["short_definition"]) > 160:
        report.add_warning(f"Short definition too long for meta: {len(data['short_definition'])} chars")
    if not data.get("long_definition"):
        report.add_error("Missing long_definition")

    return report


def validate(data: dict) -> ValidationReport:
    """Route to correct validator based on content type."""
    content_type = data.get("type", "article")
    if content_type == "article":
        return validate_article(data)
    elif content_type == "meta":
        return validate_meta(data)
    elif content_type == "faq":
        return validate_faq(data)
    elif content_type == "glossary":
        return validate_glossary(data)
    else:
        report = ValidationReport()
        report.add_warning(f"Unknown content type: {content_type}")
        return report
