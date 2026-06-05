# /// script
# requires-python = ">=3.12"
# ///

import os
import json
import subprocess
import glob
import argparse
from pathlib import Path

import tags_lib

PROMPT_TEMPLATE = """
Write or update documentation for this page, then tag it.

First write a paragraph of documentation as markdown.
Do not include any headings
Do not use words like just or simply.
Keep it to 2-3 sentences.

You may be given the full text of the previous description. Use that previous
description as the starting point, updating it only when the current HTML shows
user-facing behavior that should be reflected in the description. If no updates
are required, return the previous description unchanged.

Instead of starting with something like "This Bugzilla Bug Viewer is a web application for..."
start with "View Mozilla Bugzilla bug reports..." or similar

Then choose tags. Pick one or more "topic" tags describing what the tool does,
and zero or more "feature" tags naming the browser capabilities it actually uses
(read the HTML/JavaScript to confirm — do not guess at features that are not
present). Strongly prefer reusing an existing tag below; only coin a new
lower-case hyphenated slug when nothing existing fits.

{vocabulary}

Return exactly the description paragraph, then on its own final line:
TAGS: {{"topics": ["slug", ...], "features": ["slug", ...]}}
Return nothing else.
""".strip()


def build_system_prompt():
    return PROMPT_TEMPLATE.format(vocabulary=tags_lib.vocabulary_prompt_block())


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


def read_docs(docs_file_path):
    """Read a docs file's content, or return None if it does not exist."""
    if not os.path.exists(docs_file_path):
        return None
    with open(docs_file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_commit_hash_from_docs(docs_file_path):
    """Extract the commit hash from a documentation file if it exists."""
    content = read_docs(docs_file_path)
    return tags_lib.extract_commit_hash(content) if content else None


def extract_previous_description_from_docs(docs_file_path):
    """Extract the existing generated description without any comments."""
    content = read_docs(docs_file_path)
    if not content:
        return None
    return tags_lib.extract_description(content) or None


def docs_have_tags(docs_file_path):
    """Return True if the docs file already has at least one topic tag."""
    content = read_docs(docs_file_path)
    if not content:
        return False
    topics, _ = tags_lib.parse_tags(content)
    return bool(topics)


def parse_model_output(output):
    """Split model output into (description, topics, features).

    The model returns the description paragraph followed by a final
    ``TAGS: {json}`` line. A missing or malformed TAGS line yields empty tags.
    """
    topics, features = [], []
    lines = output.strip().splitlines()
    description_lines = lines
    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if stripped.upper().startswith("TAGS:"):
            try:
                payload = json.loads(stripped[len("TAGS:") :].strip())
                topics = [str(t).strip() for t in payload.get("topics", []) if str(t).strip()]
                features = [str(f).strip() for f in payload.get("features", []) if str(f).strip()]
            except (ValueError, AttributeError):
                pass
            description_lines = lines[:index]
        break
    return "\n".join(description_lines).strip(), topics, features


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
    """Generate documentation and tags for an HTML file using Claude.

    Returns ``(description, topics, features)`` or ``None`` on failure.
    """
    try:
        result = subprocess.run(
            ["llm", "-m", "claude-haiku-4.5", "--system", build_system_prompt()],
            input=build_llm_input(html_file_path, previous_description),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error generating documentation for {html_file_path}: {e}")
        return None

    description, topics, features = parse_model_output(result.stdout)
    if not description:
        return None
    return description, topics, features


def merge_new_tags(topics, features):
    """Add any newly coined tags to tags.json so the vocabulary persists."""
    vocab = tags_lib.load_vocabulary()
    changed = False
    for namespace, slugs in (("topics", topics), ("features", features)):
        bucket = vocab.setdefault(namespace, {})
        for slug in slugs:
            if slug not in bucket:
                bucket[slug] = slug.replace("-", " ").title()
                changed = True
    if changed:
        with tags_lib.TAGS_PATH.open("w", encoding="utf-8") as fp:
            json.dump(vocab, fp, indent=2, ensure_ascii=False)
            fp.write("\n")


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

        # Regenerate when the HTML changed, or when an up-to-date docs file is
        # still missing its tags (so existing tools get backfilled over time).
        if existing_hash == current_hash and docs_have_tags(docs_file):
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
        generated = generate_documentation(html_file, previous_description)
        if not generated:
            print(f"  Failed to generate documentation for {html_file}")
            skipped_count += 1
            continue

        description, topics, features = generated
        merge_new_tags(topics, features)
        doc_content = tags_lib.render_docs(
            description,
            topics=topics,
            features=features,
            commit_hash=current_hash,
        )

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
