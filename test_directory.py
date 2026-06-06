"""Unit tests for the Yahoo-style directory renderer and category pages."""

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
        "description": "Compare JSON documents side by side.",
        "topics": ["developer-tools"],
        "features": ["clipboard"],
    },
    {
        "slug": "snake",
        "title": "Snake Game",
        "url": "/snake",
        "description": "Play snake.",
        "topics": ["games-fun"],
        "features": ["canvas"],
    },
    {
        "slug": "pyrepl",
        "title": "Python REPL",
        "url": "/pyrepl",
        "description": "Run Python in the browser.",
        "topics": ["code-sandboxes"],
        "features": [],
    },
]


# --- Homepage index -------------------------------------------------------

def test_index_lists_categories_with_counts():
    html = directory.render_index(TOOLS, VOCAB)
    assert 'class="yh-index"' in html
    assert "Development &amp; APIs" in html
    assert "[2]" in html  # developer-tools + code-sandboxes


def test_index_subcategories_link_to_standalone_pages():
    html = directory.render_index(TOOLS, VOCAB)
    assert 'href="/category-developer-tools"' in html
    assert 'href="/category-code-sandboxes"' in html


def test_index_category_links_to_all_page_anchor():
    html = directory.render_index(TOOLS, VOCAB)
    assert 'href="/categories#cat-development"' in html


def test_index_has_browse_all_link():
    html = directory.render_index(TOOLS, VOCAB)
    assert 'href="/categories"' in html


def test_index_omits_empty_subcategories():
    html = directory.render_index(TOOLS, VOCAB)
    assert "category-maps-geo" not in html  # maps-geo has no tools


# --- All-tools-by-category page ------------------------------------------

def test_all_page_has_category_sections_and_feature_section():
    html = directory.render_all_page_body(TOOLS, VOCAB)
    assert 'id="cat-development"' in html
    assert 'id="topic-developer-tools"' in html
    assert "Browse by browser feature" in html
    assert 'id="feature-clipboard"' in html


def test_all_page_subcategory_heading_links_to_page():
    html = directory.render_all_page_body(TOOLS, VOCAB)
    assert 'href="/category-developer-tools"' in html


# --- Subcategory page -----------------------------------------------------

def test_subcategory_body_lists_tools_with_descriptions():
    html = directory.render_subcategory_body(
        "developer-tools", "Developer Tools", [TOOLS[0]], "Development & APIs"
    )
    assert 'href="/json-diff"' in html
    assert "Compare JSON documents side by side." in html
    assert "breadcrumb" in html
    assert "Development &amp; APIs" in html


def test_subcategory_filename_and_url():
    assert directory.subcategory_filename("developer-tools") == "category-developer-tools.html"
    assert directory.subcategory_url("developer-tools") == "/category-developer-tools"


# --- Uncategorized topics -------------------------------------------------

def test_uncategorized_topics_fall_under_more():
    tools = TOOLS + [
        {"slug": "x", "title": "X", "url": "/x", "description": "", "topics": ["mystery-tag"], "features": []}
    ]
    html = directory.render_all_page_body(tools, VOCAB)
    assert 'id="cat-more"' in html
    assert 'href="/category-mystery-tag"' in html


# --- Escaping -------------------------------------------------------------

def test_escapes_titles():
    tools = [
        {"slug": "x", "title": "A & B <script>", "url": "/x", "description": "d", "topics": ["developer-tools"], "features": []}
    ]
    html = directory.render_all_page_body(tools, VOCAB)
    assert "<script>" not in html
    assert "A &amp; B" in html
