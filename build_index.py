#!/usr/bin/env python3
"""Generate index.html from README.md with recent additions and updates."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

try:
    import markdown
except ModuleNotFoundError as exc:  # pragma: no cover - dependency should be installed
    raise SystemExit(
        "The 'markdown' package is required to build index.html. "
        "Install it with 'pip install markdown'."
    ) from exc

README_PATH = Path("README.md")
TOOLS_JSON_PATH = Path("tools.json")
OUTPUT_PATH = Path("index.html")


def _ordinal(value: int) -> str:
    """Return the ordinal suffix for a day value."""
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _format_display_date(dt: datetime) -> str:
    return f"{_ordinal(dt.day)} {dt.strftime('%B %Y')}"


def _load_tools() -> List[dict]:
    if not TOOLS_JSON_PATH.exists():
        return []
    with TOOLS_JSON_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _select_recent(
    tools: Sequence[dict],
    *,
    key: str,
    limit: int,
    exclude_slugs: Iterable[str] | None = None,
) -> List[dict]:
    excluded = set(exclude_slugs or [])
    dated_tools = [
        (tool, _parse_iso_datetime(tool.get(key)))
        for tool in tools
        if tool.get(key)
    ]
    dated_tools = [item for item in dated_tools if item[1] is not None]
    dated_tools.sort(key=lambda item: item[1], reverse=True)

    selected: List[dict] = []
    for tool, parsed_date in dated_tools:
        if tool.get("slug") in excluded:
            continue
        entry = tool.copy()
        entry["parsed_date"] = parsed_date
        selected.append(entry)
        if len(selected) >= limit:
            break
    return selected


def _render_recent_section(recently_added: Sequence[dict], recently_updated: Sequence[dict]) -> str:
    def render_list(tools: Sequence[dict]) -> str:
        if not tools:
            return "<li>No entries available.</li>"
        items = []
        for tool in tools:
            slug = tool.get("slug", "")
            url = tool.get("url", "#")
            parsed_date = tool.get("parsed_date")
            if isinstance(parsed_date, datetime):
                formatted_date = _format_display_date(parsed_date)
            else:
                formatted_date = ""
            date_html = (
                f'<span class="recent-date"> — {formatted_date}</span>'
                if formatted_date
                else ""
            )
            items.append(
                f'<li><a href="{url}">{slug}</a>{date_html}</li>'
            )
        return "\n".join(items)

    section_html = f"""
<div class="recent-container">
  <div class="recent-column">
    <h2>Recently added</h2>
    <ul class="recent-list">
      {render_list(recently_added)}
    </ul>
  </div>
  <div class="recent-column">
    <h2>Recently updated</h2>
    <ul class="recent-list">
      {render_list(recently_updated)}
    </ul>
  </div>
</div>
"""
    return section_html


def build_index() -> None:
    if not README_PATH.exists():
        raise FileNotFoundError("README.md not found")

    markdown_content = README_PATH.read_text("utf-8")
    md = markdown.Markdown(extensions=["extra"])
    body_html = md.convert(markdown_content)

    tools = _load_tools()
    recently_added = _select_recent(tools, key="created", limit=5)
    added_slugs = [tool.get("slug") for tool in recently_added]
    recently_updated = _select_recent(
        tools, key="updated", limit=5, exclude_slugs=added_slugs
    )

    recent_section_html = _render_recent_section(recently_added, recently_updated)

    injection_marker = '<h2 id="image-and-media">Image and media</h2>'
    if injection_marker in body_html:
        body_html = body_html.replace(
            injection_marker, recent_section_html + injection_marker, 1
        )
    else:
        body_html = recent_section_html + body_html

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>tools.simonwillison.net</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 980px;
            margin: 0 auto;
            padding: 20px;
            color: #24292e;
        }}
        h1 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        h2 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            margin-top: 24px;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
            padding: 0.2em 0.4em;
        }}
        .recent-container {{
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        .recent-column {{
            flex: 1 1 300px;
        }}
        .recent-column h2 {{
            margin-top: 0;
        }}
        .recent-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}
        .recent-list li {{
            margin-bottom: 0.5em;
        }}
        .recent-date {{
            color: #6a737d;
        }}
    </style>
</head>
<body>
{body_html}
</body>
</html>
"""

    OUTPUT_PATH.write_text(full_html, "utf-8")
    print("index.html created successfully")


if __name__ == "__main__":
    build_index()
