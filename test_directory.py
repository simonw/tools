"""Unit tests for the Yahoo-style directory renderer."""

import directory


VOCAB = {
    "topics": {"developer-tools": "Developer Tools", "games-fun": "Games & Fun"},
    "features": {"clipboard": "Clipboard", "canvas": "Canvas"},
}

TOOLS = [
    {
        "slug": "json-diff",
        "title": "JSON Diff Tool",
        "url": "/json-diff",
        "topics": ["developer-tools"],
        "features": ["clipboard"],
    },
    {
        "slug": "snake",
        "title": "Snake Game",
        "url": "/snake",
        "topics": ["games-fun", "developer-tools"],
        "features": ["canvas"],
    },
]


def test_groups_tools_under_each_topic():
    html = directory.render_directory(TOOLS, VOCAB)
    # developer-tools has both tools; games-fun has one
    assert "Developer Tools" in html
    assert "Games &amp; Fun" in html or "Games & Fun" in html
    # json-diff: 1 topic (developer-tools) + 1 feature (clipboard)
    assert html.count('href="/json-diff"') == 2
    # snake: 2 topics (games-fun, developer-tools) + 1 feature (canvas)
    assert html.count('href="/snake"') == 3


def test_counts_reflect_membership():
    html = directory.render_directory(TOOLS, VOCAB)
    assert "Developer Tools" in html and "(2)" in html
    assert "(1)" in html


def test_empty_categories_are_omitted():
    vocab = {
        "topics": {"developer-tools": "Developer Tools", "maps-geo": "Maps & Geography"},
        "features": {"clipboard": "Clipboard"},
    }
    html = directory.render_directory(TOOLS, vocab)
    assert "Maps &amp; Geography" not in html and "Maps & Geography" not in html


def test_escapes_titles():
    tools = [
        {
            "slug": "x",
            "title": "A & B <script>",
            "url": "/x",
            "topics": ["developer-tools"],
            "features": [],
        }
    ]
    html = directory.render_directory(tools, VOCAB)
    assert "<script>" not in html
    assert "A &amp; B" in html


def test_feature_section_present():
    html = directory.render_directory(TOOLS, VOCAB)
    assert "Browse by browser feature" in html
    assert "Clipboard" in html
    assert "Canvas" in html
