"""Render the classic Yahoo-style tool directory.

The homepage shows a compact two-level category index (top-level categories with
their subcategories as inline links). Each subcategory links to its own standalone
page listing the tools; a single "All tools by category" page shows the whole
hierarchy plus a browse-by-browser-feature section.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Dict, List, Sequence

ALL_URL = "/categories"


def subcategory_filename(slug: str) -> str:
    return f"category-{slug}.html"


def subcategory_url(slug: str) -> str:
    return f"/category-{slug}"


def _bucket(tools: Sequence[dict], namespace: str) -> Dict[str, List[dict]]:
    """Group tools by each tag in the given namespace ('topics' or 'features')."""
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for tool in tools:
        for tag in tool.get(namespace, []):
            buckets[tag].append(tool)
    return buckets


def _display(vocab_group: Dict[str, str], slug: str) -> str:
    return vocab_group.get(slug, slug.replace("-", " ").title())


def _sorted(members: Sequence[dict]) -> List[dict]:
    return sorted(members, key=lambda t: t.get("title", "").lower())


def _tool_links(members: Sequence[dict]) -> str:
    return "\n".join(
        f'        <li><a href="{html.escape(tool.get("url", "#"))}">'
        f'{html.escape(tool.get("title", tool.get("slug", "")))}</a></li>'
        for tool in _sorted(members)
    )


def _subcat_block(slug: str, display: str, members: Sequence[dict]) -> str:
    heading = (
        f'<a href="{subcategory_url(slug)}">{html.escape(display)}</a> '
        f'<span class="dir-count">({len(members)})</span>'
    )
    return f"""    <div class="dir-cat" id="topic-{html.escape(slug)}">
      <h3>{heading}</h3>
      <ul>
{_tool_links(members)}
      </ul>
    </div>"""


def _grid(blocks: Sequence[str]) -> str:
    return '<div class="dir-grid">\n' + "\n".join(blocks) + "\n</div>"


def collect_categories(tools: Sequence[dict], vocab: dict):
    """Return ``[(category, [(sub_slug, sub_display, members), ...]), ...]``.

    Categories and subcategories with no tools are dropped. Topic tags not
    assigned to any category are gathered under a "More" category at the end.
    """
    buckets = _bucket(tools, "topics")
    topics_map = vocab.get("topics", {})
    placed = set()
    collected = []

    for cat in vocab.get("categories", []):
        subs = []
        for sub in cat.get("subcategories", []):
            placed.add(sub)
            members = buckets.get(sub)
            if members:
                subs.append((sub, _display(topics_map, sub), members))
        if subs:
            collected.append((cat, subs))

    leftover = sorted(slug for slug in buckets if slug not in placed)
    if leftover:
        more = {"slug": "more", "name": "More"}
        subs = [(s, _display(topics_map, s), buckets[s]) for s in leftover]
        collected.append((more, subs))

    return collected


def render_index(tools: Sequence[dict], vocab: dict) -> str:
    """Render the homepage category index (top-level categories + inline subs)."""
    collected = collect_categories(tools, vocab)
    entries = []
    for cat, subs in collected:
        cat_slug = html.escape(cat.get("slug", ""))
        cat_name = html.escape(cat.get("name", ""))
        total = sum(len(m) for _, _, m in subs)
        sub_links = ", ".join(
            f'<a href="{subcategory_url(slug)}">{html.escape(display)}</a>'
            for slug, display, _ in subs
        )
        entries.append(
            f"""  <div class="yh-cat">
    <h3><a href="{ALL_URL}#cat-{cat_slug}">{cat_name}</a> <span class="yh-xtra">[{total}]</span></h3>
    <p>{sub_links}</p>
  </div>"""
        )
    return (
        '<div class="directory" data-directory>\n'
        '<h2 class="dir-heading">Browse by category</h2>\n'
        '<div class="yh-index">\n' + "\n".join(entries) + "\n</div>\n"
        f'<p class="browse-all-link"><a href="{ALL_URL}">Browse all tools by category &raquo;</a></p>\n'
        "</div>"
    )


def _render_features(tools: Sequence[dict], vocab: dict) -> str:
    buckets = _bucket(tools, "features")
    features_map = vocab.get("features", {})
    ordered = [slug for slug in features_map if buckets.get(slug)]
    ordered += [slug for slug in buckets if slug not in features_map]

    blocks = []
    for slug in ordered:
        members = buckets[slug]
        blocks.append(
            f"""    <div class="dir-cat" id="feature-{html.escape(slug)}">
      <h3>{html.escape(_display(features_map, slug))} <span class="dir-count">({len(members)})</span></h3>
      <ul>
{_tool_links(members)}
      </ul>
    </div>"""
        )
    return (
        '<h2 class="dir-heading">Browse by browser feature</h2>\n' + _grid(blocks)
    )


def render_all_page_body(tools: Sequence[dict], vocab: dict) -> str:
    """Render the body of the standalone 'All tools by category' page."""
    collected = collect_categories(tools, vocab)
    sections = []
    for cat, subs in collected:
        cat_slug = html.escape(cat.get("slug", ""))
        cat_name = html.escape(cat.get("name", ""))
        blocks = [_subcat_block(slug, display, members) for slug, display, members in subs]
        sections.append(
            f'<h3 class="dir-toplevel" id="cat-{cat_slug}">{cat_name}</h3>\n' + _grid(blocks)
        )
    return (
        '<p class="breadcrumb"><a href="/">Home</a> &rsaquo; All tools by category</p>\n'
        "<h1>All tools by category</h1>\n"
        '<div class="directory">\n'
        + "\n".join(sections)
        + "\n"
        + _render_features(tools, vocab)
        + "\n</div>"
    )


def render_subcategory_body(slug: str, display: str, members: Sequence[dict], cat_name: str) -> str:
    """Render the body of a single subcategory page."""
    items = "\n".join(
        f'  <li><a href="{html.escape(t.get("url", "#"))}">{html.escape(t.get("title", t.get("slug", "")))}</a>'
        + (
            f'\n    <p class="tool-desc">{html.escape(t.get("description", ""))}</p>'
            if t.get("description")
            else ""
        )
        + "</li>"
        for t in _sorted(members)
    )
    return (
        '<p class="breadcrumb"><a href="/">Home</a> &rsaquo; '
        f'<a href="{ALL_URL}">All tools by category</a> &rsaquo; {html.escape(cat_name)}</p>\n'
        f"<h1>{html.escape(display)} <span class=\"dir-count\">({len(members)})</span></h1>\n"
        f'<ul class="tool-list">\n{items}\n</ul>'
    )


# Backwards-compatible alias used by build_index.
render_directory = render_index
