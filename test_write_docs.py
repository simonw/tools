"""Unit tests for write_docs model-output parsing."""

import write_docs


def test_parse_model_output_splits_description_and_tags():
    output = (
        "View bug reports directly in your browser.\n"
        "It fetches and renders them.\n"
        'TAGS: {"topics": ["developer-tools"], "features": ["clipboard", "fetch-network"]}'
    )
    description, topics, features = write_docs.parse_model_output(output)
    assert description == (
        "View bug reports directly in your browser.\nIt fetches and renders them."
    )
    assert topics == ["developer-tools"]
    assert features == ["clipboard", "fetch-network"]


def test_parse_model_output_without_tags_line():
    output = "A plain description with no tags."
    description, topics, features = write_docs.parse_model_output(output)
    assert description == "A plain description with no tags."
    assert topics == []
    assert features == []


def test_parse_model_output_malformed_tags_are_ignored():
    output = "Desc.\nTAGS: not json"
    description, topics, features = write_docs.parse_model_output(output)
    assert description == "Desc."
    assert topics == []
    assert features == []


def test_parse_model_output_trailing_blank_lines():
    output = 'Desc.\nTAGS: {"topics": ["games-fun"], "features": []}\n\n'
    description, topics, features = write_docs.parse_model_output(output)
    assert description == "Desc."
    assert topics == ["games-fun"]
    assert features == []
