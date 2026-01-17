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


def _has_distinct_update(tool: dict) -> bool:
    """Return True if the tool has an update distinct from its creation."""

    updated = _parse_iso_datetime(tool.get("updated"))
    if updated is None:
        return False

    created = _parse_iso_datetime(tool.get("created"))
    if created is None:
        return True

    return updated > created


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
            filename = tool.get("filename", "")
            parsed_date = tool.get("parsed_date")
            if isinstance(parsed_date, datetime):
                formatted_date = _format_display_date(parsed_date)
            else:
                formatted_date = ""
            
            # Create colophon link for the date
            colophon_url = f"https://tools.simonwillison.net/colophon#{filename}" if filename else "#"
            date_html = (
                f'<span class="recent-date"> — <a href="{colophon_url}">{formatted_date}</a></span>'
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
    <p class="browse-all"><a href="/by-month">Browse all by month</a></p>
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
    tools_with_updates = [tool for tool in tools if _has_distinct_update(tool)]
    recently_updated = _select_recent(
        tools_with_updates, key="updated", limit=5, exclude_slugs=added_slugs
    )

    recent_section_html = _render_recent_section(recently_added, recently_updated)

    # Inject the recent section between the comment markers
    start_marker = '<!-- recently starts -->'
    end_marker = '<!-- recently stops -->'
    if start_marker in body_html and end_marker in body_html:
        # Replace content between markers
        start_idx = body_html.find(start_marker)
        end_idx = body_html.find(end_marker)
        if start_idx < end_idx:
            body_html = (
                body_html[:start_idx + len(start_marker)] +
                '\n' + recent_section_html +
                body_html[end_idx:]
            )
    else:
        # Fallback: inject before Image and media heading if markers not found
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
            font-family: "Helvetica Neue", helvetica, sans-serif;
            line-height: 1.4;
            margin: 0;
            padding: 0;
        }}
        h1 {{
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.4em;
        }}
        h2 {{
            margin-top: 1.5em;
        }}
        a {{
            color: #0066cc;
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
        nav {{
            text-align: left;
            background: linear-gradient(to bottom, rgb(154, 103, 175) 0%, rgb(96, 72, 129) 49%, rgb(100, 67, 130) 100%);
            color: white;
        }}
        nav p {{
            display: flex;
            justify-content: space-between;
            margin: 0;
            padding: 4px 2em;
        }}
        nav a:link,
        nav a:visited,
        nav a:hover,
        nav a:focus,
        nav a:active {{
            color: white;
            text-decoration: none;
        }}
        section.body {{
            padding: 0.5em 2em;
            max-width: 800px;
        }}
        @media (max-width: 600px) {{
            section.body {{
                padding: 0em 1em;
            }}
            nav p {{
                padding: 4px 1em;
            }}
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
            color: #666;
        }}
        .browse-all {{
            margin-top: 1em;
            padding-top: 0.5em;
            border-top: 1px solid #ccc;
            font-size: 0.9em;
        }}
        .settings-section {{
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #ccc;
        }}
        .settings-section h2 {{
            margin-top: 0;
        }}
        .toggle-container {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 1em 0;
        }}
        .toggle-switch {{
            position: relative;
            width: 50px;
            height: 26px;
            flex-shrink: 0;
        }}
        .toggle-switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .toggle-slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.3s;
            border-radius: 26px;
        }}
        .toggle-slider:before {{
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }}
        .toggle-switch input:checked + .toggle-slider {{
            background-color: #0066cc;
        }}
        .toggle-switch input:checked + .toggle-slider:before {{
            transform: translateX(24px);
        }}
        .toggle-label {{
            font-weight: 500;
        }}
        .toggle-description {{
            color: #666;
            font-size: 0.9em;
            margin-top: 0.5em;
        }}
    </style>
</head>
<body>
<nav>
    <p><a href="/">Simon Willison's Tools</a> <a href="https://simonwillison.net/">My blog</a></p>
</nav>
<section class="body">
{body_html}
<div class="settings-section">
    <h2>Settings</h2>
    <div class="toggle-container">
        <label class="toggle-switch">
            <input type="checkbox" id="page-weight-toggle">
            <span class="toggle-slider"></span>
        </label>
        <span class="toggle-label">Show page weight badge</span>
    </div>
    <p class="toggle-description">
        When enabled, a badge showing page weight and number of requests will appear
        in the bottom-right corner of every page on this site. Click the badge to see
        detailed information about resource sizes and load times.
    </p>
</div>
</section>
<script>
(function() {{
    const toggle = document.getElementById('page-weight-toggle');
    const STORAGE_KEY = 'PAGE_WEIGHT';

    // Initialize toggle state from localStorage
    toggle.checked = localStorage.getItem(STORAGE_KEY) !== null;

    toggle.addEventListener('change', function() {{
        if (this.checked) {{
            localStorage.setItem(STORAGE_KEY, '1');
        }} else {{
            localStorage.removeItem(STORAGE_KEY);
        }}
    }});
}})();
</script>
</body>
</html>
"""

    OUTPUT_PATH.write_text(full_html, "utf-8")
    print("index.html created successfully")


if __name__ == "__main__":
    build_index()
