#!/usr/bin/env python3
"""Generate an Atom feed of recently added tools for tools.simonwillison.net."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from build_sitemap import BASE_URL, _absolute_url, _load_tools


OUTPUT_PATH = Path("atom.xml")
FEED_TITLE = "tools.simonwillison.net"
FEED_SUBTITLE = "New tools added to tools.simonwillison.net"
FEED_AUTHOR = "Simon Willison"
FEED_LIMIT = 30
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Atom requires a timezone offset on every date
    if parsed.tzinfo is None:
        return None
    return parsed


def _select_recently_added(tools: list[dict], limit: int) -> list[tuple[dict, datetime]]:
    dated_tools = []
    for tool in tools:
        path = tool.get("url")
        if not path or path == "/":
            continue
        created = _parse_iso_datetime(tool.get("created"))
        if created is None:
            continue
        dated_tools.append((tool, created))

    dated_tools.sort(key=lambda item: item[1], reverse=True)
    return dated_tools[:limit]


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrib: str) -> ET.Element:
    element = ET.SubElement(parent, f"{{{ATOM_NAMESPACE}}}{tag}", attrib)
    if text is not None:
        element.text = text
    return element


def build_feed() -> None:
    tools = _load_tools()
    entries = _select_recently_added(tools, FEED_LIMIT)

    ET.register_namespace("", ATOM_NAMESPACE)
    feed = ET.Element(f"{{{ATOM_NAMESPACE}}}feed")

    _sub(feed, "title", FEED_TITLE)
    _sub(feed, "subtitle", FEED_SUBTITLE)
    _sub(feed, "id", f"{BASE_URL}/")
    _sub(feed, "link", href=f"{BASE_URL}/", rel="alternate", type="text/html")
    _sub(feed, "link", href=_absolute_url(OUTPUT_PATH.name), rel="self", type="application/atom+xml")
    if entries:
        # Entries are sorted newest first
        feed_updated = entries[0][1]
    else:
        feed_updated = datetime(1970, 1, 1, tzinfo=timezone.utc)
    _sub(feed, "updated", feed_updated.isoformat())
    author = _sub(feed, "author")
    _sub(author, "name", FEED_AUTHOR)

    for tool, created in entries:
        url = _absolute_url(tool["url"])
        entry = _sub(feed, "entry")
        _sub(entry, "title", tool.get("title") or tool.get("slug") or tool["url"])
        _sub(entry, "id", url)
        _sub(entry, "link", href=url, rel="alternate", type="text/html")
        # Entries describe when each tool was added, so later edits to a tool
        # do not cause feed readers to resurface it as new
        _sub(entry, "published", created.isoformat())
        _sub(entry, "updated", created.isoformat())
        description = (tool.get("description") or "").strip()
        if description:
            _sub(entry, "summary", description, type="text")

    ET.indent(feed, space="  ")
    tree = ET.ElementTree(feed)
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Generated {OUTPUT_PATH} with {len(entries)} entries")


if __name__ == "__main__":
    build_feed()
