#!/usr/bin/env python3
"""Generate the 'All tools by category' page and one page per subcategory."""

from __future__ import annotations

import json
from pathlib import Path

import directory
import page_template
import tags_lib

TOOLS_JSON_PATH = Path("tools.json")


def _load_tools():
    if not TOOLS_JSON_PATH.exists():
        return []
    with TOOLS_JSON_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def build_categories() -> None:
    tools = _load_tools()
    vocab = tags_lib.load_vocabulary()

    # The combined "All tools by category" page.
    all_body = directory.render_all_page_body(tools, vocab)
    Path("categories.html").write_text(
        page_template.render_page("All tools by category", all_body), "utf-8"
    )

    # One standalone page per (non-empty) subcategory.
    count = 0
    for cat, subs in directory.collect_categories(tools, vocab):
        for slug, display, members in subs:
            body = directory.render_subcategory_body(
                slug, display, members, cat.get("name", "")
            )
            title = f"{display} — tools.simonwillison.net"
            Path(directory.subcategory_filename(slug)).write_text(
                page_template.render_page(title, body), "utf-8"
            )
            count += 1

    print(f"Built categories.html and {count} subcategory pages")


if __name__ == "__main__":
    build_categories()
