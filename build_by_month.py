#!/usr/bin/env python3
"""Generate by-month.html listing all tools grouped by creation month."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


GATHERED_LINKS_PATH = Path("gathered_links.json")
OUTPUT_PATH = Path("by-month.html")


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _get_first_n_words(text: str, n: int = 15) -> str:
    """Extract the first n words from text."""
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]) + "..."


def _extract_summary(docs_path: Path, word_limit: int = 30) -> str:
    """Extract the first paragraph of the docs file, limited to word_limit words."""
    if not docs_path.exists():
        return ""

    try:
        content = docs_path.read_text("utf-8").strip()
    except OSError:
        return ""

    # Remove HTML comments
    if "<!--" in content:
        content = content.split("<!--", 1)[0]

    # Get first paragraph (skip headings)
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        # Skip markdown headings
        if stripped.startswith("#"):
            continue
        lines.append(stripped)

    paragraph = " ".join(lines)
    return _get_first_n_words(paragraph, word_limit)


def _load_gathered_links() -> dict:
    if not GATHERED_LINKS_PATH.exists():
        return {}
    with GATHERED_LINKS_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def build_by_month() -> None:
    data = _load_gathered_links()
    pages = data.get("pages", {})

    if not pages:
        print("No pages found in gathered_links.json")
        return

    # Group tools by month of creation
    tools_by_month: dict[str, list[dict]] = defaultdict(list)

    for page_name, page_data in pages.items():
        commits = page_data.get("commits", [])
        if not commits:
            continue

        # Get the oldest commit (creation date) - commits are newest first
        oldest_commit = commits[-1]
        created_date = _parse_iso_datetime(oldest_commit.get("date"))

        if created_date is None:
            continue

        # Format month key for sorting (YYYY-MM) and display
        month_key = created_date.strftime("%Y-%m")

        # Get the docs summary
        slug = page_name.replace(".html", "")
        docs_path = Path(f"{slug}.docs.md")
        summary = _extract_summary(docs_path)

        tools_by_month[month_key].append({
            "filename": page_name,
            "slug": slug,
            "created": created_date,
            "summary": summary,
        })

    # Sort months in reverse chronological order
    sorted_months = sorted(tools_by_month.keys(), reverse=True)

    # Sort tools within each month by creation date (newest first)
    for month_key in sorted_months:
        tools_by_month[month_key].sort(key=lambda t: t["created"], reverse=True)

    # Count total tools
    tool_count = sum(len(tools) for tools in tools_by_month.values())

    # Build HTML
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tools by month - tools.simonwillison.net</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
            color: #1a1a1a;
        }
        h1 {
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }
        h2 {
            margin-top: 2rem;
            font-size: 1.4rem;
            border-bottom: 1px solid #f0f0f0;
            padding-bottom: 0.3rem;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        a.hashref:link,
        a.hashref:visited,
        a.hashref:hover,
        a.hashref:focus,
        a.hashref:active {
            color: #666;
            margin-right: 0.3rem;
        }
        .tool-list {
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .tool-item {
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #f8f8f8;
        }
        .tool-item:last-child {
            border-bottom: none;
        }
        .tool-name {
            font-weight: 600;
        }
        .tool-links {
            font-size: 0.9rem;
            color: #666;
        }
        .tool-summary {
            margin-top: 0.25rem;
            color: #444;
            font-size: 0.95rem;
        }
        .back-link {
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <p class="back-link"><a href="/">&larr; Back to tools.simonwillison.net</a></p>
    <h1>Tools by month</h1>
"""

    html_content += f"    <p>{tool_count} tools, grouped by the month they were created.</p>\n"

    for month_key in sorted_months:
        tools = tools_by_month[month_key]
        # Format month display (e.g., "November 2024")
        month_date = datetime.strptime(month_key, "%Y-%m")
        month_display = month_date.strftime("%B %Y")
        tool_word = "tool" if len(tools) == 1 else "tools"

        html_content += f'\n    <h2 id="{month_key}"><a class="hashref" href="#{month_key}">#</a>{month_display} ({len(tools)} {tool_word})</h2>\n'
        html_content += '    <ul class="tool-list">\n'

        for tool in tools:
            slug = tool["slug"]
            filename = tool["filename"]
            summary = tool["summary"]
            tool_url = f"https://tools.simonwillison.net/{slug}"
            colophon_url = f"https://tools.simonwillison.net/colophon#{filename}"

            html_content += f'        <li class="tool-item">\n'
            html_content += f'            <span class="tool-name"><a href="{tool_url}">{slug}</a></span>\n'
            html_content += f'            <span class="tool-links">(<a href="{colophon_url}">colophon</a>)</span>\n'
            if summary:
                html_content += f'            <div class="tool-summary">{summary}</div>\n'
            html_content += '        </li>\n'

        html_content += '    </ul>\n'

    html_content += """</body>
</html>
"""

    OUTPUT_PATH.write_text(html_content, "utf-8")
    print(f"by-month.html created successfully ({tool_count} tools)")


if __name__ == "__main__":
    build_by_month()
