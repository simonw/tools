"""Render a classic Yahoo-style directory of tools grouped by tag.

Produces a static HTML fragment: tools grouped by topic ("what it does") and a
second grouping by browser feature. Output works with no JavaScript; the
homepage progressively enhances it with feature-filter chips.
"""

from __future__ import annotations

import html
from typing import Dict, List, Sequence


def _group(tools: Sequence[dict], namespace: str, vocab_group: Dict[str, str]):
    """Yield ``(slug, display_name, [tools])`` for each non-empty tag, in vocab order."""
    buckets: Dict[str, List[dict]] = {slug: [] for slug in vocab_group}
    for tool in tools:
        for tag in tool.get(namespace, []):
            buckets.setdefault(tag, []).append(tool)

    ordered = list(vocab_group) + [slug for slug in buckets if slug not in vocab_group]
    for slug in ordered:
        members = buckets.get(slug)
        if not members:
            continue
        display = vocab_group.get(slug, slug.replace("-", " ").title())
        members = sorted(members, key=lambda t: t.get("title", "").lower())
        yield slug, display, members


def _render_section(title: str, anchor_prefix: str, groups) -> str:
    blocks = []
    for slug, display, members in groups:
        anchor = f"{anchor_prefix}-{slug}"
        links = "\n".join(
            f'        <li><a href="{html.escape(tool.get("url", "#"))}">'
            f'{html.escape(tool.get("title", tool.get("slug", "")))}</a></li>'
            for tool in members
        )
        blocks.append(
            f"""    <div class="dir-cat" id="{html.escape(anchor)}">
      <h3>{html.escape(display)} <span class="dir-count">({len(members)})</span></h3>
      <ul>
{links}
      </ul>
    </div>"""
        )
    return (
        f'<h2 class="dir-heading">{html.escape(title)}</h2>\n'
        f'<div class="dir-grid">\n' + "\n".join(blocks) + "\n</div>"
    )


def render_directory(tools: Sequence[dict], vocab: dict) -> str:
    """Render the full directory HTML fragment from tools and the tag vocabulary."""
    topic_groups = list(_group(tools, "topics", vocab.get("topics", {})))
    feature_groups = list(_group(tools, "features", vocab.get("features", {})))

    feature_chips = "\n".join(
        f'    <a class="dir-chip" href="#feature-{html.escape(slug)}" '
        f'data-feature="{html.escape(slug)}">{html.escape(display)} '
        f'<span class="dir-count">({len(members)})</span></a>'
        for slug, display, members in feature_groups
    )

    topics_html = _render_section("Browse by category", "topic", topic_groups)
    features_html = _render_section(
        "Browse by browser feature", "feature", feature_groups
    )

    return f"""<div class="directory" data-directory>
<p class="dir-intro">A classic directory of every tool, sorted into categories.
Pick a category below, or filter by the browser features a tool uses.</p>
<div class="dir-chips" data-feature-chips>
{feature_chips}
</div>
{topics_html}
{features_html}
</div>"""
