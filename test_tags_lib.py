"""Unit tests for tags_lib: parsing and rendering tag metadata in .docs.md files."""

import tags_lib


DESCRIPTION = (
    "View Mozilla Bugzilla bug reports directly in your browser. Paste an ID "
    "and the tool fetches and renders the report."
)

DOCS_WITH_TAGS = f"""{DESCRIPTION}

<!-- topics: developer-tools, data-json -->
<!-- features: clipboard, fetch-network -->
<!-- Generated from commit: abc123 -->"""

DOCS_LEGACY = f"""{DESCRIPTION}

<!-- Generated from commit: abc123 -->"""


def test_parse_tags_reads_topics_and_features():
    topics, features = tags_lib.parse_tags(DOCS_WITH_TAGS)
    assert topics == ["developer-tools", "data-json"]
    assert features == ["clipboard", "fetch-network"]


def test_parse_tags_missing_lines_returns_empty():
    topics, features = tags_lib.parse_tags(DOCS_LEGACY)
    assert topics == []
    assert features == []


def test_extract_description_strips_all_generated_comments():
    assert tags_lib.extract_description(DOCS_WITH_TAGS) == DESCRIPTION
    assert tags_lib.extract_description(DOCS_LEGACY) == DESCRIPTION


def test_extract_commit_hash():
    assert tags_lib.extract_commit_hash(DOCS_WITH_TAGS) == "abc123"
    assert tags_lib.extract_commit_hash("no marker here") is None


def test_render_docs_roundtrips():
    rendered = tags_lib.render_docs(
        DESCRIPTION,
        topics=["developer-tools", "data-json"],
        features=["clipboard", "fetch-network"],
        commit_hash="abc123",
    )
    topics, features = tags_lib.parse_tags(rendered)
    assert topics == ["developer-tools", "data-json"]
    assert features == ["clipboard", "fetch-network"]
    assert tags_lib.extract_description(rendered) == DESCRIPTION
    assert tags_lib.extract_commit_hash(rendered) == "abc123"


def test_render_docs_omits_empty_tag_lines():
    rendered = tags_lib.render_docs(DESCRIPTION, topics=[], features=[], commit_hash="abc123")
    assert "topics:" not in rendered
    assert "features:" not in rendered
    assert tags_lib.extract_description(rendered) == DESCRIPTION


def test_parse_tags_tolerates_extra_whitespace():
    content = "Desc\n\n<!--   topics:  a ,  b  -->\n<!--features:c-->\n"
    topics, features = tags_lib.parse_tags(content)
    assert topics == ["a", "b"]
    assert features == ["c"]
