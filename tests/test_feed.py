import json
import xml.etree.ElementTree as ET

import build_feed

NS = {"atom": build_feed.ATOM_NAMESPACE}


def write_tools(tmp_path, tools):
    (tmp_path / "tools.json").write_text(json.dumps(tools), encoding="utf-8")


def parse_feed(tmp_path):
    return ET.parse(tmp_path / "atom.xml").getroot()


def test_build_feed_lists_newest_tools_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_tools(
        tmp_path,
        [
            {
                "filename": "index.html",
                "slug": "index",
                "title": "tools.simonwillison.net",
                "description": "",
                "created": "2026-01-01T00:00:00Z",
                "updated": "2026-01-01T00:00:00Z",
                "url": "/",
            },
            {
                "filename": "older-tool.html",
                "slug": "older-tool",
                "title": "Older Tool",
                "description": "Converts <b>things</b> & other stuff.",
                "created": "2025-03-01T10:00:00-08:00",
                "updated": "2025-11-19T12:30:00-08:00",
                "url": "/older-tool",
            },
            {
                "filename": "newer-tool.html",
                "slug": "newer-tool",
                "title": "Newer Tool",
                "description": "",
                "created": "2025-06-02T09:15:00Z",
                "updated": "2025-06-02T09:15:00Z",
                "url": "/newer-tool",
            },
            {
                "filename": "undated.html",
                "slug": "undated",
                "title": "Undated",
                "description": "",
                "created": None,
                "updated": None,
                "url": "/undated",
            },
        ],
    )

    build_feed.build_feed()

    feed = parse_feed(tmp_path)
    assert feed.tag == f"{{{build_feed.ATOM_NAMESPACE}}}feed"
    assert feed.findtext("atom:id", namespaces=NS) == "https://tools.simonwillison.net/"
    assert feed.findtext("atom:updated", namespaces=NS) == "2025-06-02T09:15:00+00:00"
    self_link = feed.find("atom:link[@rel='self']", NS)
    assert self_link.get("href") == "https://tools.simonwillison.net/atom.xml"
    assert feed.findtext("atom:author/atom:name", namespaces=NS) == "Simon Willison"

    entries = feed.findall("atom:entry", NS)
    assert [entry.findtext("atom:title", namespaces=NS) for entry in entries] == [
        "Newer Tool",
        "Older Tool",
    ]

    newer, older = entries
    assert newer.findtext("atom:id", namespaces=NS) == (
        "https://tools.simonwillison.net/newer-tool"
    )
    assert newer.find("atom:link", NS).get("href") == (
        "https://tools.simonwillison.net/newer-tool"
    )
    assert newer.find("atom:summary", NS) is None

    # Entries are dated by creation, so later edits do not resurface them
    assert older.findtext("atom:published", namespaces=NS) == "2025-03-01T10:00:00-08:00"
    assert older.findtext("atom:updated", namespaces=NS) == "2025-03-01T10:00:00-08:00"
    summary = older.find("atom:summary", NS)
    assert summary.get("type") == "text"
    assert summary.text == "Converts <b>things</b> & other stuff."


def test_build_feed_limits_number_of_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_feed, "FEED_LIMIT", 3)
    write_tools(
        tmp_path,
        [
            {
                "filename": f"tool-{day:02d}.html",
                "slug": f"tool-{day:02d}",
                "title": f"Tool {day}",
                "description": "",
                "created": f"2025-01-{day:02d}T00:00:00Z",
                "updated": f"2025-01-{day:02d}T00:00:00Z",
                "url": f"/tool-{day:02d}",
            }
            for day in range(1, 11)
        ],
    )

    build_feed.build_feed()

    entries = parse_feed(tmp_path).findall("atom:entry", NS)
    assert [entry.findtext("atom:title", namespaces=NS) for entry in entries] == [
        "Tool 10",
        "Tool 9",
        "Tool 8",
    ]


def test_build_feed_with_no_tools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_tools(tmp_path, [])

    build_feed.build_feed()

    feed = parse_feed(tmp_path)
    assert feed.findall("atom:entry", NS) == []
    assert feed.findtext("atom:updated", namespaces=NS) == "1970-01-01T00:00:00+00:00"
