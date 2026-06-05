"""Shared helpers for reading and writing tag metadata in ``*.docs.md`` files.

A generated docs file looks like::

    <description paragraph>

    <!-- topics: developer-tools, data-json -->
    <!-- features: clipboard, fetch-network -->
    <!-- Generated from commit: <hash> -->

The ``topics``/``features`` comment lines are optional so legacy docs files
(description + commit marker only) keep working unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

COMMIT_MARKER_RE = re.compile(r"<!-- Generated from commit: ([a-f0-9]+) -->")
TOPICS_RE = re.compile(r"<!--\s*topics:(.*?)-->", re.IGNORECASE | re.DOTALL)
FEATURES_RE = re.compile(r"<!--\s*features:(.*?)-->", re.IGNORECASE | re.DOTALL)

TAGS_PATH = Path(__file__).resolve().parent / "tags.json"


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_tags(content: str) -> Tuple[List[str], List[str]]:
    """Return ``(topics, features)`` parsed from a docs file's content."""
    topics_match = TOPICS_RE.search(content)
    features_match = FEATURES_RE.search(content)
    topics = _split_csv(topics_match.group(1)) if topics_match else []
    features = _split_csv(features_match.group(1)) if features_match else []
    return topics, features


def extract_description(content: str) -> str:
    """Return the human description with every generated comment removed."""
    return content.split("<!--", 1)[0].strip()


def extract_commit_hash(content: str):
    """Return the commit hash recorded in the docs file, or ``None``."""
    match = COMMIT_MARKER_RE.search(content)
    return match.group(1) if match else None


def render_docs(
    description: str,
    *,
    topics: List[str] | None = None,
    features: List[str] | None = None,
    commit_hash: str,
) -> str:
    """Render a complete docs file from its parts."""
    parts = [description.strip(), ""]
    if topics:
        parts.append(f"<!-- topics: {', '.join(topics)} -->")
    if features:
        parts.append(f"<!-- features: {', '.join(features)} -->")
    parts.append(f"<!-- Generated from commit: {commit_hash} -->")
    return "\n".join(parts)


def load_vocabulary() -> dict:
    """Load the canonical tag vocabulary from tags.json."""
    with TAGS_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def vocabulary_prompt_block() -> str:
    """Format the vocabulary as a prompt fragment listing existing tags."""
    vocab = load_vocabulary()
    topics = ", ".join(sorted(vocab.get("topics", {})))
    features = ", ".join(sorted(vocab.get("features", {})))
    return (
        f"Existing topic tags (prefer these): {topics}\n"
        f"Existing feature tags (prefer these): {features}"
    )
