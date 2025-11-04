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
    """Return a comma-separated list of unique issue numbers (e.g., '#1234')."""
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
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

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

    range_input = sys.argv[1].strip()
    print(extract_issue_numbers(range_input))
