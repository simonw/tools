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
    linkified = re.sub(url_pattern, r'<a href="\1">\1</a>', escaped)

    # Linkify #123 style issue references
    issue_pattern = r"#(\d+)"
    linkified = re.sub(
        issue_pattern,
        r'<a href="https://github.com/simonw/tools/issues/\1">#\1</a>',
        linkified,
    )

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

    # Count the number of tools
    tool_count = len(sorted_pages)

    # Start building the HTML
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>tools.simonwillison.net colophon</title>
    <style>
        body {
            font-family: "Helvetica Neue", helvetica, sans-serif;
            line-height: 1.4;
            margin: 0;
            padding: 0;
        }
        h1 {
            font-family: Georgia, 'Times New Roman', Times, serif;
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
        a.hashref:link,
        a.hashref:visited,
        a.hashref:hover,
        a.hashref:focus,
        a.hashref:active {
            color: #666;
        }
        nav {
            text-align: left;
            background: linear-gradient(to bottom, rgb(154, 103, 175) 0%, rgb(96, 72, 129) 49%, rgb(100, 67, 130) 100%);
            color: white;
        }
        nav p {
            display: flex;
            justify-content: space-between;
            margin: 0;
            padding: 4px 2em;
        }
        nav a:link,
        nav a:visited,
        nav a:hover,
        nav a:focus,
        nav a:active {
            color: white;
            text-decoration: none;
        }
        section.body {
            padding: 0.5em 2em;
            max-width: 800px;
        }
        .tool {
            margin-bottom: 2rem;
            border-bottom: 1px solid #ccc;
            padding-bottom: 1rem;
        }
        .tool-name {
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .commit {
            background-color: #f8f9fa;
            padding: 1rem;
            margin: 0.75rem 0;
            border-radius: 4px;
            border-left: 3px solid #9e6bb5;
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
            margin-top: 1rem;
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
        /* Styles for the heading */
        .heading {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .main-text {
            font-size: 1.4rem;
            font-weight: bold;
            color: #0066cc;
        }
        .hash-text {
            font-size: 1.4rem;
            font-weight: bold;
            color: #666;
        }
        .code-text {
            font-size: 1rem;
            color: #666;
            position: relative;
            top: 1px;
        }
        .main-text a {
            color: #0066cc;
            text-decoration: none;
        }
        .code-text a {
            color: #666;
            text-decoration: none;
        }
        /* Styles for details/summary */
        details {
            margin-top: 1rem;
        }
        summary {
            cursor: pointer;
            padding: 0.5rem 0;
            color: #0066cc;
            font-weight: 500;
        }
        summary:hover {
            text-decoration: underline;
        }
        blockquote {
            margin: 1em 0;
            border-left: 0.75em solid #9e6bb52e;
            padding-left: 0.75em;
        }
        @media (max-width: 600px) {
            section.body {
                padding: 0em 1em;
            }
            nav p {
                padding: 4px 1em;
            }
            .commit {
                padding: 0.75rem;
            }
        }
    </style>
</head>
<body>
<nav>
    <p><a href="/">Simon Willison's Tools</a> <a href="https://simonwillison.net/">My blog</a></p>
</nav>
<section class="body">
    <h1>tools.simonwillison.net colophon</h1>
"""

    # Add the tool count to the existing paragraph
    html_content += f"""
    <p>The tools on <a href="https://tools.simonwillison.net/">tools.simonwillison.net</a> were mostly built using <a href="https://simonwillison.net/tags/ai-assisted-programming/">AI-assisted programming</a>. This page lists {tool_count} tools and their development history.</p>
    <p>This page lists the commit messages for each tool, many of which link to the LLM transcript used to produce the code.</p>
    <p>Here's <a href="https://simonwillison.net/2025/Mar/11/using-llms-for-code/#a-detailed-example">how I built this colophon page</a>. The descriptions for each of the tools were <a href="https://simonwillison.net/2025/Mar/13/tools-colophon/">generated using Claude Haiku 4.5</a>.</p>
"""

    # Modified tool heading HTML
    for page_name, page_data in sorted_pages:
        tool_url = f"https://tools.simonwillison.net/{page_name.replace('.html', '')}"
        github_url = f"https://github.com/simonw/tools/blob/main/{page_name}"
        commits = page_data.get("commits", [])

        # Reverse the commits list to show oldest first
        commits = list(reversed(commits))
        commit_count = len(commits)

        # Modified tool heading with the new structure
        html_content += f"""
    <div class="tool" id="{page_name}">
        <div class="tool-name">
            <h2 class="heading">
                <span class="hash-text"><a class="hashref" href="#{page_name}">#</a></span>
                <span class="main-text"><a href="{tool_url}">{page_name.replace('.html', '')}</a></span>
                <span class="code-text"><a href="{github_url}">code</a></span>
            </h2>
        </div>
"""
        # Check for corresponding meta JSON file
        slug = page_name.replace(".html", "")
        meta_file = Path("meta") / f"{slug}.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r") as f:
                    meta_data = json.load(f)
                    description = meta_data.get("description", "")
                    if description:
                        # Render markdown to HTML
                        docs_html = markdown.markdown(description)
                        # Add docs above commits
                        html_content += '<div class="docs">' + docs_html + "</div>"
            except Exception as e:
                print(f"Error reading {meta_file}: {e}")

        # Wrap commits in details/summary tags
        html_content += f"""
        <details>
            <summary>Development history ({commit_count} commit{"s" if commit_count > 1 else ""})</summary>
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
        # Close the details tag
        html_content += """
        </details>
    </div>
"""

    # Close the HTML with script that expands the correct tool
    html_content += """
    <script>
    document.addEventListener('DOMContentLoaded', () => {
        const hash = window.location.hash.slice(1);
        if (hash) {
            const element = document.getElementById(hash);
            if (element) {
                const details = element.querySelector('details');
                if (details) {
                    details.open = true;
                }
            }
        }
    });
    </script>
</section>
</body>
</html>
"""

    # Write the HTML to colophon.html
    with open("colophon.html", "w") as f:
        f.write(html_content)

    print("Colophon page built successfully as colophon.html")


if __name__ == "__main__":
    build_colophon()
