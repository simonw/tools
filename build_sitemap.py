#!/usr/bin/env python3
"""Generate sitemap.xml for tools.simonwillison.net."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET


BASE_URL = "https://tools.simonwillison.net"
TOOLS_JSON_PATH = Path("tools.json")
OUTPUT_PATH = Path("sitemap.xml")
GENERATED_PAGES = {
    "index.html": "/",
    "by-month.html": "/by-month",
    "colophon.html": "/colophon",
}
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _parse_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _absolute_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"

    if path == "/":
        return f"{BASE_URL}/"

    return f"{BASE_URL}{quote(path)}"


def _load_tools() -> list[dict]:
    if not TOOLS_JSON_PATH.exists():
        raise FileNotFoundError("tools.json not found. Run gather_links.py first.")

    with TOOLS_JSON_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _latest_date(dates: list[str | None]) -> str | None:
    parsed_dates = [_parse_iso_date(date) for date in dates]
    valid_dates = [date for date in parsed_dates if date]
    if not valid_dates:
        return None
    return max(valid_dates)


def build_sitemap() -> None:
    tools = _load_tools()
    entries: dict[str, str | None] = {}

    for tool in tools:
        path = tool.get("url")
        if not path:
            continue

        lastmod = _parse_iso_date(tool.get("updated"))
        entries[path] = max(entries.get(path) or "", lastmod or "") or None

    latest_tool_date = _latest_date([tool.get("updated") for tool in tools])
    for filename, path in GENERATED_PAGES.items():
        if Path(filename).exists():
            entries.setdefault(path, latest_tool_date)

    ET.register_namespace("", SITEMAP_NAMESPACE)
    urlset = ET.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")

    def sort_key(item: tuple[str, str | None]) -> tuple[int, str]:
        path, _ = item
        return (0 if path == "/" else 1, path)

    for path, lastmod in sorted(entries.items(), key=sort_key):
        url = ET.SubElement(urlset, f"{{{SITEMAP_NAMESPACE}}}url")
        loc = ET.SubElement(url, f"{{{SITEMAP_NAMESPACE}}}loc")
        loc.text = _absolute_url(path)
        if lastmod:
            lastmod_element = ET.SubElement(url, f"{{{SITEMAP_NAMESPACE}}}lastmod")
            lastmod_element.text = lastmod

    ET.indent(urlset, space="  ")
    tree = ET.ElementTree(urlset)
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Generated {OUTPUT_PATH} with {len(entries)} URLs")


if __name__ == "__main__":
    build_sitemap()
