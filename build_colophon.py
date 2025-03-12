#!/usr/bin/env python3
import json
import re
from datetime import datetime
import html
from pathlib import Path
import markdown


def format_commit_message(message):
    """Format commit message with line breaks and linkified URLs."""
    # Escape HTML entities
    escaped = html.escape(message)

    # Linkify URLs first (before adding breaks)
    url_pattern = r"(https?://[^\s]+)"
    linkified = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', escaped)

    # Then convert newlines to <br>
    return linkified.replace("\n", "<br>")


def build_colophon():
    # Load the gathered_links.json file
    try:
        with open("gathered_links.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: gathered_links.json not found. Run gather_links.py first.")
        return

    pages = data.get("pages", {})
    if not pages:
        print("No pages found in gathered_links.json")
        return

    # Sort pages by most recent commit date (newest first)
    def get_most_recent_date(page_data):
        commits = page_data.get("commits", [])
        if not commits:
            return "0000-00-00T00:00:00"

        # Find the most recent commit date
        dates = [commit.get("date", "0000-00-00T00:00:00") for commit in commits]
        return max(dates) if dates else "0000-00-00T00:00:00"

    sorted_pages = sorted(
        pages.items(), key=lambda x: get_most_recent_date(x[1]), reverse=True
    )

    # Start building the HTML
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>tools.simonwillison.net colophon</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
            color: #1a1a1a;
        }
        h1 {
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }
        h2 {
            margin-top: 2rem;
            font-size: 1.4rem;
        }
        h3 {
            margin-top: 1.5rem;
            font-size: 1.2rem;
        }
        a {
            color: #0066cc;
            text-decoration: none;
            overflow-wrap: break-word;
        }
        a:hover {
            text-decoration: underline;
        }
        .tool {
            margin-bottom: 2rem;
            border-bottom: 1px solid #f0f0f0;
            padding-bottom: 1rem;
        }
        .tool-name {
            font-weight: bold;
        }
        .commit {
            background-color: #f8f9fa;
            padding: 1rem;
            margin: 0.75rem 0;
            border-radius: 4px;
            border-left: 3px solid #ddd;
        }
        .commit-hash {
            font-family: monospace;
            color: #666;
            font-size: 0.85rem;
        }
        .commit-date {
            color: #666;
            font-size: 0.85rem;
            margin-left: 0.5rem;
        }
        .commit-message {
            margin-top: 0.5rem;
        }
        .docs {
            margin-top: 1.5rem;
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
        }
        .docs pre {
            white-space: pre-wrap;
            overflow-wrap: break-word;
            font-size: 0.9rem;
            line-height: 1.4;
        }
        .urls {
            margin-top: 1rem;
        }
        @media (max-width: 600px) {
            body {
                padding: 0.5rem;
            }
            .commit {
                padding: 0.75rem;
            }
        }
    </style>
</head>
<body>
    <h1>tools.simonwillison.net colophon</h1>
    <p>The tools on <a href="https://tools.simonwillison.net/">tools.simonwillison.net</a> were mostly built using <a href="https://simonwillison.net/tags/ai-assisted-programming/">AI-assisted programming</a>.</p>
    <p>This page lists the commit messages for each tool, many of which link to the LLM transcript used to produce the code.</p>
"""

    # Add each page with its commits
    for page_name, page_data in sorted_pages:
        tool_url = f"https://tools.simonwillison.net/{page_name.replace('.html', '')}"
        commits = page_data.get("commits", [])

        # Reverse the commits list to show oldest first
        commits = list(reversed(commits))

        html_content += f"""
    <div class="tool" id="{page_name}">
        <h2 class="tool-name"><a href="{tool_url}">{page_name}</a></h2>
"""

        # Add each commit
        for commit in commits:
            commit_hash = commit.get("hash", "")
            short_hash = commit_hash[:7] if commit_hash else "unknown"
            commit_date = commit.get("date", "")

            # Format the date with time
            formatted_date = ""
            if commit_date:
                try:
                    dt = datetime.fromisoformat(commit_date)
                    formatted_date = dt.strftime("%B %d, %Y %H:%M")
                except ValueError:
                    formatted_date = commit_date

            commit_message = commit.get("message", "")
            formatted_message = format_commit_message(commit_message)
            commit_url = f"https://github.com/simonw/tools/commit/{commit_hash}"

            html_content += f"""
        <div class="commit" id="commit-{short_hash}">
            <div>
                <a href="{commit_url}" class="commit-hash">{short_hash}</a>
                <span class="commit-date">{formatted_date}</span>
            </div>
            <div class="commit-message">{formatted_message}</div>
        </div>
"""

        # Check for corresponding docs.md file
        docs_file = page_name.replace(".html", ".docs.md")
        if Path(docs_file).exists():
            try:
                with open(docs_file, "r") as f:
                    docs_content = f.read()
                    # Render markdown to HTML
                    docs_html = markdown.markdown(docs_content)
                    # Add docs above commits
                    html_content = html_content.replace(
                        f'<h2 class="tool-name"><a href="{tool_url}">{page_name}</a></h2>',
                        f"""<h2 class="tool-name"><a href="{tool_url}">{page_name}</a></h2>
        <div class="docs">
            {docs_html}
        </div>""",
                    )
            except Exception as e:
                print(f"Error reading {docs_file}: {e}")

        html_content += """
    </div>
"""

    # Close the HTML
    html_content += """
</body>
</html>
"""

    # Write the HTML to colophon.html
    with open("colophon.html", "w") as f:
        f.write(html_content)

    print("Colophon page built successfully as colophon.html")


if __name__ == "__main__":
    build_colophon()
