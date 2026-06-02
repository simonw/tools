# /// script
# requires-python = ">=3.12"
# ///

PROMPT = """
Write or update a paragraph of documentation for this page as markdown.
Do not include any headings
Do not use words like just or simply.
Keep it to 2-3 sentences.
Return only the final description text, with no extra commentary.

You may be given the full text of the previous description. Use that previous
description as the starting point, updating it only when the current HTML shows
user-facing behavior that should be reflected in the description. If no updates
are required, return the previous description unchanged.

Instead of starting with something like "This Bugzilla Bug Viewer is a web application for..."
start with "View Mozilla Bugzilla bug reports..." or similar
""".strip()

import os
import subprocess
import glob
import re
import argparse
from pathlib import Path

COMMIT_MARKER_RE = re.compile(r"<!-- Generated from commit: ([a-f0-9]+) -->")


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

    hash_match = COMMIT_MARKER_RE.search(content)
    if hash_match:
        return hash_match.group(1)

    return None


def extract_previous_description_from_docs(docs_file_path):
    """Extract the existing generated description without the commit marker."""
    if not os.path.exists(docs_file_path):
        return None

    with open(docs_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    description = COMMIT_MARKER_RE.sub("", content).strip()
    return description or None


def build_llm_input(html_file_path, previous_description=None):
    """Build the user prompt sent to the documentation model."""
    with open(html_file_path, "r", encoding="utf-8") as f:
        html = f.read()

    if previous_description:
        return f"""
Previous description:

```markdown
{previous_description}
```

Current HTML:

```html
{html}
```
""".strip()

    return f"""
No previous description exists. Write a new description for this HTML.

Current HTML:

```html
{html}
```
""".strip()


def generate_documentation(html_file_path, previous_description=None):
    """Generate documentation for an HTML file using Claude."""
    try:
        result = subprocess.run(
            ["llm", "-m", "claude-haiku-4.5", "--system", PROMPT],
            input=build_llm_input(html_file_path, previous_description),
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

        previous_description = extract_previous_description_from_docs(docs_file)
        doc_content = generate_documentation(html_file, previous_description)
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

        updated_count += 1

    print(
        f"Documentation process complete: {updated_count} files updated, {skipped_count} files skipped."
    )


if __name__ == "__main__":
    main()
