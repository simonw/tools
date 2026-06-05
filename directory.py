"""Render a classic Yahoo-style directory of tools.

The directory has two levels: top-level categories (e.g. "Development & APIs")
each containing subcategories (e.g. "Developer Tools", "Code Sandboxes & REPLs"),
with the tools listed under each subcategory. A second section groups tools by
the browser feature they use. The output is static HTML that works with no
JavaScript; feature chips are anchor links into the feature section.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Dict, List, Sequence


def _bucket(tools: Sequence[dict], namespace: str) -> Dict[str, List[dict]]:
    """Group tools by each tag in the given namespace ('topics' or 'features')."""
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for tool in tools:
        for tag in tool.get(namespace, []):
            buckets[tag].append(tool)
    return buckets


def _display(vocab_group: Dict[str, str], slug: str) -> str:
    return vocab_group.get(slug, slug.replace("-", " ").title())


def _subcat_block(anchor: str, display: str, members: Sequence[dict]) -> str:
    members = sorted(members, key=lambda t: t.get("title", "").lower())
    links = "\n".join(
        f'        <li><a href="{html.escape(tool.get("url", "#"))}">'
        f'{html.escape(tool.get("title", tool.get("slug", "")))}</a></li>'
        for tool in members
    )
    return f"""    <div class="dir-cat" id="{html.escape(anchor)}">
      <h3>{html.escape(display)} <span class="dir-count">({len(members)})</span></h3>
      <ul>
{links}
      </ul>
    </div>"""


def _grid(blocks: Sequence[str]) -> str:
    return '<div class="dir-grid">\n' + "\n".join(blocks) + "\n</div>"


def _collect_categories(tools: Sequence[dict], vocab: dict):
    """Return ``[(category, [(sub_slug, sub_display, members), ...]), ...]``.

    Categories and subcategories with no tools are dropped. Any topic tag not
    assigned to a category (e.g. newly coined) is gathered under a "More"
    category at the end.
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


def _render_index(collected) -> str:
    """Render the compact Yahoo-style two-column category index."""
    entries = []
    for cat, subs in collected:
        cat_slug = html.escape(cat.get("slug", ""))
        cat_name = html.escape(cat.get("name", ""))
        total = sum(len(m) for _, _, m in subs)
        sub_links = ", ".join(
            f'<a href="#topic-{html.escape(slug)}">{html.escape(display)}</a>'
            for slug, display, _ in subs
        )
        entries.append(
            f"""  <div class="yh-cat">
    <h3><a href="#cat-{cat_slug}">{cat_name}</a> <span class="yh-xtra">[{total}]</span></h3>
    <p>{sub_links}</p>
  </div>"""
        )
    return '<div class="yh-index">\n' + "\n".join(entries) + "\n</div>"


def _render_detail(collected) -> str:
    """Render the full per-category tool listings beneath the index."""
    sections = []
    for cat, subs in collected:
        cat_slug = html.escape(cat.get("slug", ""))
        cat_name = html.escape(cat.get("name", ""))
        blocks = [
            _subcat_block(f"topic-{slug}", display, members)
            for slug, display, members in subs
        ]
        sections.append(
            f'<h3 class="dir-toplevel" id="cat-{cat_slug}">{cat_name}</h3>\n'
            + _grid(blocks)
        )
    return "\n".join(sections)


def _render_topics(tools: Sequence[dict], vocab: dict) -> str:
    collected = _collect_categories(tools, vocab)
    return (
        '<h2 class="dir-heading">Browse by category</h2>\n'
        + _render_index(collected)
        + '\n<h2 class="dir-heading">All tools by category</h2>\n'
        + _render_detail(collected)
    )


def _render_features(tools: Sequence[dict], vocab: dict) -> str:
    buckets = _bucket(tools, "features")
    features_map = vocab.get("features", {})
    ordered = [slug for slug in features_map if buckets.get(slug)]
    ordered += [slug for slug in buckets if slug not in features_map]

    chips = "\n".join(
        f'    <a class="dir-chip" href="#feature-{html.escape(slug)}">'
        f'{html.escape(_display(features_map, slug))} '
        f'<span class="dir-count">({len(buckets[slug])})</span></a>'
        for slug in ordered
    )
    blocks = [
        _subcat_block(f"feature-{slug}", _display(features_map, slug), buckets[slug])
        for slug in ordered
    ]
    return (
        '<h2 class="dir-heading">Browse by browser feature</h2>\n'
        f'<div class="dir-chips">\n{chips}\n</div>\n' + _grid(blocks)
    )


def render_directory(tools: Sequence[dict], vocab: dict) -> str:
    """Render the full directory HTML fragment from tools and the tag vocabulary."""
    return f"""<div class="directory" data-directory>
<p class="dir-intro">A classic directory of every tool, sorted into categories.
Pick a category below, or jump to the browser features a tool uses.</p>
{_render_topics(tools, vocab)}
{_render_features(tools, vocab)}
</div>"""
