#!/usr/bin/env python3
"""Convert *.docs.md files to JSON files in meta/ directory."""

import json
import re
from pathlib import Path


def extract_description(content: str) -> str:
    """Extract the first paragraph (description) from docs.md content."""
    # Remove HTML comments
    if "<!--" in content:
        content = content.split("<!--", 1)[0]

    # Strip any markdown heading lines
    content_lines = [
        line for line in content.splitlines()
        if not line.lstrip().startswith("# ")
        and not line.lstrip().startswith("## ")
        and not line.lstrip().startswith("### ")
        and not line.lstrip().startswith("#### ")
        and not line.lstrip().startswith("##### ")
        and not line.lstrip().startswith("###### ")
    ]

    # Get first paragraph
    lines = []
    for line in content_lines:
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        lines.append(stripped)

    return " ".join(lines)


def extract_commit(content: str) -> str:
    """Extract the commit hash from the HTML comment."""
    match = re.search(r"<!-- Generated from commit: ([a-f0-9]+) -->", content)
    if match:
        return match.group(1)
    return ""


def main():
    # Create meta directory if it doesn't exist
    meta_dir = Path("meta")
    meta_dir.mkdir(exist_ok=True)

    # Find all docs.md files in the current directory
    docs_files = sorted(Path(".").glob("*.docs.md"))

    converted_count = 0

    for docs_file in docs_files:
        # Read the content
        content = docs_file.read_text("utf-8")

        # Extract description and commit
        description = extract_description(content)
        commit = extract_commit(content)

        # Determine output filename (e.g., ai-adoption.docs.md -> meta/ai-adoption.json)
        slug = docs_file.stem.replace(".docs", "")
        output_file = meta_dir / f"{slug}.json"

        # Create JSON object
        data = {
            "description": description,
            "commit": commit,
        }

        # Write to file with pretty printing
        output_file.write_text(json.dumps(data, indent=2) + "\n", "utf-8")
        converted_count += 1
        print(f"Converted {docs_file} -> {output_file}")

    print(f"\nConverted {converted_count} files to JSON in meta/")


if __name__ == "__main__":
    main()
