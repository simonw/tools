"""Unit tests for the Yahoo-style hierarchical directory renderer."""

import directory


VOCAB = {
    "categories": [
        {
            "slug": "development",
            "name": "Development & APIs",
            "subcategories": ["developer-tools", "code-sandboxes"],
        },
        {
            "slug": "web-life",
            "name": "Web, Social & Fun",
            "subcategories": ["games-fun", "maps-geo"],
        },
    ],
    "topics": {
        "developer-tools": "Developer Tools",
        "code-sandboxes": "Code Sandboxes & REPLs",
        "games-fun": "Games & Fun",
        "maps-geo": "Maps & Geography",
    },
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
        "topics": ["games-fun"],
        "features": ["canvas"],
    },
    {
        "slug": "pyrepl",
        "title": "Python REPL",
        "url": "/pyrepl",
        "topics": ["code-sandboxes"],
        "features": [],
    },
]


def test_renders_top_level_categories_and_subcategories():
    html = directory.render_directory(TOOLS, VOCAB)
    # Top-level category headings (in the detail listing)
    assert 'id="cat-development"' in html
    assert "Development &amp; APIs" in html
    # Subcategory headings under them
    assert 'id="topic-developer-tools"' in html
    assert 'id="topic-code-sandboxes"' in html


def test_yahoo_index_lists_categories_with_inline_subcategory_links():
    html = directory.render_directory(TOOLS, VOCAB)
    assert 'class="yh-index"' in html
    # Category name links to its detail section
    assert 'href="#cat-development"' in html
    # Subcategories appear as inline links into their tool listings
    assert 'href="#topic-developer-tools"' in html
    assert 'href="#topic-code-sandboxes"' in html


def test_index_shows_tool_count_per_category():
    html = directory.render_directory(TOOLS, VOCAB)
    # development has json-diff (developer-tools) + pyrepl (code-sandboxes) = 2
    assert "[2]" in html


def test_empty_subcategories_are_omitted():
    # maps-geo has no tools -> should not render
    html = directory.render_directory(TOOLS, VOCAB)
    assert 'id="topic-maps-geo"' not in html


def test_empty_top_level_category_is_omitted():
    vocab = {
        "categories": [
            {"slug": "empty", "name": "Empty Cat", "subcategories": ["maps-geo"]},
            {"slug": "development", "name": "Development", "subcategories": ["developer-tools"]},
        ],
        "topics": {"developer-tools": "Developer Tools", "maps-geo": "Maps"},
        "features": {},
    }
    html = directory.render_directory(TOOLS, vocab)
    assert 'id="cat-empty"' not in html
    assert "Empty Cat" not in html


def test_uncategorized_topics_fall_under_more():
    tools = TOOLS + [
        {"slug": "x", "title": "X", "url": "/x", "topics": ["mystery-tag"], "features": []}
    ]
    html = directory.render_directory(tools, VOCAB)
    assert 'id="cat-more"' in html
    assert 'href="/x"' in html


def test_feature_section_present_with_chips():
    html = directory.render_directory(TOOLS, VOCAB)
    assert "Browse by browser feature" in html
    assert 'href="#feature-clipboard"' in html
    assert 'id="feature-canvas"' in html


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
