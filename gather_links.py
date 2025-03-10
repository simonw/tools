#!/usr/bin/env python3
import json
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime


def get_file_commit_details(file_path):
    """
    Get the commit details for a specific file.
    Returns a list of dictionaries with hash, message, and date.
    """
    try:
        # Get each commit as a separate record with its hash, date, and message
        result = subprocess.run(
            ["git", "log", "--format=%H|%aI|%B%x00", "--", file_path],
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []
        # Split by NULL character which safely separates commits
        raw_commits = result.stdout.strip().split("\0")

        for raw_commit in raw_commits:
            if not raw_commit.strip():
                continue

            # Find the first pipe to extract commit hash
            first_pipe = raw_commit.find("|")
            if first_pipe == -1:
                continue

            commit_hash = raw_commit[:first_pipe]

            # Find the second pipe to extract date
            second_pipe = raw_commit.find("|", first_pipe + 1)
            if second_pipe == -1:
                continue

            commit_date = raw_commit[first_pipe + 1 : second_pipe]

            # The rest is the commit message
            commit_message = raw_commit[second_pipe + 1 :]

            commits.append(
                {"hash": commit_hash, "date": commit_date, "message": commit_message}
            )

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit history for {file_path}: {e}")
        return []


def extract_urls(text):
    """
    Extract URLs from text using regex pattern.
    Returns a list of URLs.
    """
    # Pattern for URLs that captures the full URL until whitespace or end of string
    url_pattern = r"(https?://[^\s]+)"
    return re.findall(url_pattern, text)


def main():
    # Get current directory
    current_dir = Path.cwd()

    # Find all HTML files
    html_files = list(current_dir.glob("*.html"))

    # Dictionary to store results
    results = {"pages": {}}

    # Process each HTML file
    for html_file in html_files:
        file_name = html_file.name
        print(f"Processing {file_name}...")

        # Get commit details for this file
        commits = get_file_commit_details(html_file)

        if not commits:
            continue

        # Extract URLs from commit messages
        all_urls = []
        for commit in commits:
            urls = extract_urls(commit["message"])
            all_urls.extend(urls)

        # Remove duplicates but preserve order
        unique_urls = []
        for url in all_urls:
            if url not in unique_urls:
                unique_urls.append(url)

        # Add to results if any commits were found
        if commits:
            results["pages"][file_name] = {"commits": commits, "urls": unique_urls}

    # Save results to JSON file
    with open("gathered_links.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Processed {len(html_files)} files")
    print(f"Found details for {len(results['pages'])} files")
    print("Results saved to gathered_links.json")


if __name__ == "__main__":
    main()
