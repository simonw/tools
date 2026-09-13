#!/usr/bin/env python3
"""Extract unique issue numbers from git commit messages over a given range.

Usage:
  python extract_issues.py 1.0a19
  python extract_issues.py 1.0a19..1.0a20
"""

import re
import subprocess
import sys


def extract_issue_numbers(range_spec: str) -> str:
    """Return a comma-separated list of unique issue numbers (e.g., '#1234').

    Raises:
        ValueError: If range_spec contains invalid characters or is empty.
        RuntimeError: If git log fails.
    """
    # Validate input - reject null bytes
    if "\x00" in range_spec:
        raise ValueError("Input contains null bytes")

    # Validate range format: reject empty specs and flag-like inputs
    if ".." in range_spec:
        parts = range_spec.split("..", 1)
        if not all(part.strip() for part in parts):
            raise ValueError(f"Invalid range format: {range_spec}")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("-"):
                raise ValueError(f"Invalid git ref (looks like a flag): {stripped}")
    else:
        stripped = range_spec.strip()
        if not stripped:
            raise ValueError("Empty range specification")
        if stripped.startswith("-"):
            raise ValueError(f"Invalid git ref (looks like a flag): {stripped}")

    # Allow either a single tag (interpreted as TAG..HEAD) or an explicit range A..B
    git_range = range_spec if ".." in range_spec else f"{range_spec}..HEAD"

    try:
        # %B = raw body (subject + body), ensures we scan full commit messages
        result = subprocess.run(
            ["git", "log", git_range, "--pretty=%B"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else "git log failed"
        raise RuntimeError(f"git log failed: {err}") from e

    commit_messages = result.stdout

    # Find all issue numbers of the form #1234 anywhere in the message bodies
    issue_pattern = re.compile(r"#(\d+)")
    issue_numbers = issue_pattern.findall(commit_messages)

    # Remove duplicates and sort numerically
    unique_issues = sorted(set(issue_numbers), key=int)

    # Format as #1234, #1235, etc.
    return ", ".join(f"#{num}" for num in unique_issues)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_issues.py <tag> | <range A..B>", file=sys.stderr)
        sys.exit(2)

    try:
        range_input = sys.argv[1].strip()
        result = extract_issue_numbers(range_input)
        print(result)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
