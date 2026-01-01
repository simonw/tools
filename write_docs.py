# /// script
# requires-python = ">=3.12"
# ///

PROMPT = """
Write a paragraph of documentation for this page as markdown.
Do not include any headings
Do not use words like just or simply.
Keep it to 2-3 sentences.

Instead of starting with something like "This Bugzilla Bug Viewer is a web application for..."
start with "View Mozilla Bugzilla bug reports..." or similar
""".strip()

import json
import os
import shlex
import subprocess
import glob
import re
import argparse
from pathlib import Path


def get_current_commit_hash(file_path):
    """Get the most recent commit hash for a specific file."""
    try:
        result = subprocess.run(
            ["git", "log", "-n", "1", "--pretty=format:%H", "--", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def extract_commit_hash_from_docs(docs_file_path):
    """Extract the commit hash from a documentation file if it exists."""
    if not os.path.exists(docs_file_path):
        return None

    with open(docs_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    hash_match = re.search(r"<!-- Generated from commit: ([a-f0-9]+) -->", content)
    if hash_match:
        return hash_match.group(1)

    return None


def extract_description_from_content(content: str) -> str:
    """Extract the first paragraph (description) from docs content."""
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


def write_meta_json(slug: str, description: str, commit_hash: str, path: str = "."):
    """Write the meta JSON file for a tool."""
    meta_dir = Path(path) / "meta"
    meta_dir.mkdir(exist_ok=True)

    meta_file = meta_dir / f"{slug}.json"
    data = {
        "description": description,
        "commit": commit_hash,
    }

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def generate_documentation(html_file_path):
    """Generate documentation for an HTML file using Claude."""
    try:
        result = subprocess.run(
            f"cat '{html_file_path}' | llm -m claude-haiku-4.5 --system {shlex.quote(PROMPT)}",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error generating documentation for {html_file_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation for HTML files in a repository"
    )
    parser.add_argument("--path", default=".", help="Path to the repository")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    # Find all HTML files in the repository
    html_files = glob.glob(f"{args.path}/**/*.html", recursive=True)

    if args.verbose:
        print(f"Found {len(html_files)} HTML files")

    updated_count = 0
    skipped_count = 0

    for html_file in html_files:
        html_path = Path(html_file)
        docs_file = html_path.with_suffix(".docs.md")

        if args.verbose:
            print(f"Processing {html_file}")

        if docs_file.name == "index.docs.md":
            continue

        # Get the current commit hash for the HTML file
        current_hash = get_current_commit_hash(html_file)
        if not current_hash:
            if args.verbose:
                print(f"  Skipping {html_file} - not in a git repository")
            skipped_count += 1
            continue

        # Get the commit hash from the existing docs file (if it exists)
        existing_hash = extract_commit_hash_from_docs(docs_file)

        # Check if documentation needs to be updated
        if existing_hash == current_hash:
            if args.verbose:
                print(f"  Documentation is up to date for {html_file}")
            skipped_count += 1
            continue

        if args.dry_run:
            print(f"Would generate documentation for {html_file}")
            updated_count += 1
            continue

        # Generate documentation
        if args.verbose:
            print(f"  Generating documentation for {html_file}")

        doc_content = generate_documentation(html_file)
        if not doc_content:
            print(f"  Failed to generate documentation for {html_file}")
            skipped_count += 1
            continue

        # Add the commit hash marker
        doc_content += f"\n\n<!-- Generated from commit: {current_hash} -->"

        # Write the documentation to file
        with open(docs_file, "w", encoding="utf-8") as f:
            f.write(doc_content)

        if args.verbose:
            print(f"  Documentation written to {docs_file}")

        # Also write the meta JSON file
        slug = html_path.stem
        description = extract_description_from_content(doc_content)
        write_meta_json(slug, description, current_hash, args.path)

        if args.verbose:
            print(f"  Meta JSON written to meta/{slug}.json")

        updated_count += 1

    print(
        f"Documentation process complete: {updated_count} files updated, {skipped_count} files skipped."
    )


if __name__ == "__main__":
    main()
