#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "markdown",
# ]
# ///

"""
Local Tools Collection Builder

This script builds a local browsing experience for Simon Willison's tools collection.
It creates an index.html with all tools and a colophon.html with development history.

The script:
1. Gathers commit history for HTML files
2. Creates a comprehensive table of contents
3. Builds an interactive index with multiple view options
4. Generates a detailed colophon with development history

Usage:
    uv run --no-project ./build_local_tools.py
"""

import json
import re
import os
import subprocess
from datetime import datetime
import html
from pathlib import Path
import markdown

def run_gather_links():
    """
    Run the gather_links.py script to create gathered_links.json
    
    Processes all HTML files in the current directory, extracts their commit 
    history, and identifies URLs from commit messages.
    
    Returns:
        dict: The gathered links data if successful, None if failed
    """
    print("Gathering links from commit history...")
    
    try:
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
        
        return results
    
    except Exception as e:
        print(f"Error gathering links: {e}")
        return None

def get_file_commit_details(file_path):
    """
    Get the commit details for a specific file.
    
    Args:
        file_path (str or Path): Path to the file
    
    Returns:
        list: List of dictionaries with hash, message, and date for each commit
    
    Raises:
        subprocess.CalledProcessError: If git command fails
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
    
    Args:
        text (str): Text to extract URLs from
    
    Returns:
        list: List of URLs found in the text
    """
    # Pattern for URLs that captures the full URL until whitespace or end of string
    url_pattern = r"(https?://[^\s]+)"
    return re.findall(url_pattern, text)

def format_commit_message(message):
    """
    Format commit message with line breaks and linkified URLs.
    
    Args:
        message (str): Commit message to format
    
    Returns:
        str: Formatted message with HTML links and line breaks
    """
    # Escape HTML entities
    escaped = html.escape(message)

    # Linkify URLs first (before adding breaks)
    url_pattern = r"(https?://[^\s]+)"
    linkified = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', escaped)

    # Then convert newlines to <br>
    return linkified.replace("\n", "<br>")

def build_colophon(data=None):
    """
    Build the colophon.html page with development history
    
    Creates a HTML page showing the commit history for all tools,
    along with their documentation.
    
    Args:
        data (dict, optional): The gathered links data. If None, load from file.
    
    Returns:
        bool: True if successful, False if failed
    """
    print("Building colophon page...")
    
    # Load the gathered_links.json file if not provided
    if data is None:
        try:
            with open("gathered_links.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print("Error: gathered_links.json not found. Run gather_links.py first.")
            return False

    pages = data.get("pages", {})
    if not pages:
        print("No pages found in gathered_links.json")
        return False

    # Get all HTML files in the directory
    all_html_files = [f.name for f in Path(".").glob("*.html")]
    
    # Create TOC entries for all pages, sorted alphabetically
    toc_entries = []
    
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
    <title>Tools Collection - Colophon</title>
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
        a.hashref:link,
        a.hashref:visited,
        a.hashref:hover,
        a.hashref:focus,
        a.hashref:active {
            color: #666;
            padding-left: 0.5em;
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
        .back-to-index {
            margin-top: 1rem;
            margin-bottom: 2rem;
            padding: 0.5rem 1rem;
            background-color: #f8f9fa;
            border-radius: 4px;
            display: inline-block;
        }
        .toc {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
        .toc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 0.5rem;
        }
        
        /* Collapsible TOC */
        .toc-header {
            cursor: pointer;
            padding: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 4px 4px 0 0;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #e0e0e0;
        }
        .toc-header h2 {
            margin: 0;
            border: none;
            padding: 0;
            flex-grow: 1;
            font-size: 1.2rem;
        }
        .toggle-icon {
            font-size: 1rem;
            transition: transform 0.3s ease;
        }
        .toc-header.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }
        .toc-content {
            overflow: hidden;
            max-height: 1000px;
            transition: max-height 0.3s ease;
        }
        .toc-content.collapsed {
            max-height: 0;
        }
    </style>
</head>
<body>
    <div class="back-to-index">
        <a href="index.html">← Back to Index</a>
    </div>

    <h1>Tools Collection - Colophon</h1>
    <p>This colophon shows the development history of each tool, many including links to the LLM transcript used to produce the code.</p>
    <p>The tools were mostly built using <a href="https://simonwillison.net/tags/ai-assisted-programming/">AI-assisted programming</a>.</p>
    <p>This page lists the commit messages for each tool, many of which link to the LLM transcript used to produce the code.</p>

    <p>The descriptions for each of the tools were generated using Claude 3.7 Sonnet.</p>
    
    <div class="toc">
        <div class="toc-header" onclick="toggleToc()">
            <h2>Table of Contents</h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div class="toc-content">
            <div class="toc-grid">
"""

    # Add TOC links for pages in gathered_links.json
    for page_name, _ in sorted(sorted_pages, key=lambda x: x[0].lower()):
        html_content += f'                <a href="#{page_name}">{page_name}</a>\n'

    html_content += """
            </div>
        </div>
    </div>
"""

    # Add each page with its commits
    for page_name, page_data in sorted_pages:
        tool_url = f"{page_name}"  # Local file reference
        commits = page_data.get("commits", [])

        # Reverse the commits list to show oldest first
        commits = list(reversed(commits))

        html_content += f"""
    <div class="tool" id="{page_name}">
        <h2 class="tool-name"><a href="{tool_url}">{page_name}</a> <a class="hashref" href="#{page_name}">#</a></h2>
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
                    html_content += f"""
        <div class="docs">
            {docs_html}
<!-- Generated from commit: {commits[-1].get('hash') if commits else ''} -->
        </div>
"""
            except Exception as e:
                print(f"Error reading {docs_file}: {e}")

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

        html_content += """
    </div>
"""

    # Close the HTML
    html_content += """
    <div class="back-to-index">
        <a href="index.html">← Back to Index</a>
    </div>
    
    <script>
        // Toggle TOC visibility
        function toggleToc() {
            const content = document.querySelector('.toc-content');
            content.classList.toggle('collapsed');
            document.querySelector('.toc-header').classList.toggle('collapsed');
        }
    </script>
</body>
</html>
"""

    # Write the HTML to colophon.html
    with open("colophon.html", "w") as f:
        f.write(html_content)

    print("Colophon page built successfully as colophon.html")
    return True

def extract_sections_from_readme(readme_path="README.md"):
    """
    Extract the categorized sections from the README.md file.
    
    Parses the README.md file to identify tool categories and their tools.
    
    Args:
        readme_path (str): Path to the README.md file
    
    Returns:
        dict: Dictionary of categories with their tools
    """
    if not os.path.exists(readme_path):
        print(f"Error: {readme_path} not found.")
        return {}

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract the sections after "## Tools" and before "## On Observable"
    match = re.search(r"## Tools\s+(.*?)(?=## On Observable)", content, re.DOTALL)
    if not match:
        print("Error: Could not find the Tools section in README.md")
        return {}

    tools_section = match.group(1).strip()
    
    # Find all categories and tools
    categories = {}
    current_category = "Uncategorized"
    
    # Extract LLM playgrounds section
    llm_section_match = re.search(r"## LLM playgrounds and debuggers\s+(.*?)(?=^## )", content, re.DOTALL | re.MULTILINE)
    if llm_section_match:
        categories["LLM Playgrounds and Debuggers"] = parse_tool_list(llm_section_match.group(1).strip())
    
    # Extract miscellaneous section
    misc_section_match = re.search(r"## Miscellaneous\s+(.*?)(?=^## |\Z)", content, re.DOTALL | re.MULTILINE)
    if misc_section_match:
        categories["Miscellaneous"] = parse_tool_list(misc_section_match.group(1).strip())
    
    # Extract main tools section
    categories["Tools"] = parse_tool_list(tools_section)
    
    return categories

def parse_tool_list(section_content):
    """
    Parse a list of tools from a section of the README
    
    Extracts tool information from Markdown format links and descriptions.
    
    Args:
        section_content (str): The content of a section to parse
    
    Returns:
        list: List of tool dictionaries with name, url, local_file, etc.
    """
    tools = []
    for line in section_content.strip().split("\n"):
        if line.startswith("- ["):
            # Extract the name and URL from markdown link format
            match = re.match(r"- \[(.*?)\]\((.*?)\)(.*)", line)
            if match:
                name, url, description = match.groups()
                # Clean up the description
                description = description.strip(" -")
                if description.startswith("- "):
                    description = description[2:]
                
                # Check if this is an external link
                is_external = url.startswith("http") and not url.startswith("https://tools.simonwillison.net/")
                
                if is_external:
                    # For external links, don't try to find a local file
                    tools.append({
                        "name": name,
                        "url": url,
                        "local_file": None,  # No local file
                        "description": description,
                        "is_external": True
                    })
                else:
                    # Extract the HTML file name from the URL
                    html_file = url.split("/")[-1]
                    if not html_file.endswith(".html"):
                        html_file += ".html"
                    
                    # Check if the file actually exists locally
                    if os.path.exists(html_file):
                        tools.append({
                            "name": name,
                            "url": url,
                            "local_file": html_file,
                            "description": description,
                            "is_external": False
                        })
                    else:
                        print(f"Warning: Referenced file '{html_file}' from README not found locally.")
    return tools

def load_all_tool_files():
    """
    Load all HTML files and their documentation
    
    Scans the current directory for HTML files and loads their 
    corresponding documentation from .docs.md files.
    
    Returns:
        list: List of tool dictionaries with name, local_file, docs
    """
    html_files = sorted(list(Path(".").glob("*.html")))
    tools = []
    
    for html_file in html_files:
        file_name = html_file.name
        # Skip if it's index.html or colophon.html
        if file_name in ["index.html", "colophon.html"]:
            continue
            
        docs_file = html_file.with_suffix(".docs.md")
        docs_content = ""
        
        if docs_file.exists():
            with open(docs_file, "r", encoding="utf-8") as f:
                docs_content = f.read().split("<!-- Generated from commit")[0].strip()
        
        tools.append({
            "name": file_name.replace(".html", ""),
            "local_file": file_name,
            "docs": docs_content
        })
    
    return tools

def load_docs_for_tools(categories):
    """
    Load documentation for each tool from .docs.md files
    
    Updates the tools in the categories dictionary with documentation content.
    
    Args:
        categories (dict): Dictionary of categories with their tools
    """
    for category, tools in categories.items():
        for tool in tools:
            # Skip tools with no local file (external links)
            if tool.get("local_file") is None:
                continue
                
            html_file = tool["local_file"]
            docs_file = html_file.replace(".html", ".docs.md")
            
            if os.path.exists(docs_file):
                with open(docs_file, "r", encoding="utf-8") as f:
                    tool["docs"] = f.read().split("<!-- Generated from commit")[0].strip()
            else:
                tool["docs"] = ""

def build_local_index():
    """
    Build a clean HTML index page with all tools
    
    Creates an index.html file with multiple viewing options and search functionality.
    Organizes tools by category based on README.md structure.
    
    Returns:
        bool: True if successful, False if failed
    """
    print("Building local index page...")
    
    # Load all tools from HTML files
    all_tools = load_all_tool_files()
    
    # Load categorized tools from README
    categories = extract_sections_from_readme()
    load_docs_for_tools(categories)
    
    # Create a set of tools that are already in categories
    categorized_tools = set()
    for category, tools in categories.items():
        for tool in tools:
            if tool.get("local_file") is not None:  # Only consider tools with local files
                categorized_tools.add(tool["local_file"])
    
    # Find tools that aren't in any category
    uncategorized_tools = []
    for tool in all_tools:
        if tool["local_file"] not in categorized_tools:
            uncategorized_tools.append(tool)
    
    # Sort alphabetically
    uncategorized_tools.sort(key=lambda x: x["name"])
    
    # Create a list of all tools for the TOC
    all_tool_names = []
    for category, tools in categories.items():
        for tool in tools:
            if tool.get("local_file") is not None:
                all_tool_names.append((tool["name"], tool["local_file"]))
                
    for tool in uncategorized_tools:
        all_tool_names.append((tool["name"], tool["local_file"]))
    
    # Sort alphabetically for the TOC
    all_tool_names.sort(key=lambda x: x[0].lower())
    
    # HTML header
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simon Willison's Tools Collection - Local Index</title>
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
            border-bottom: 1px solid #f0f0f0;
            padding-bottom: 0.5rem;
        }
        h3 {
            margin-top: 1.5rem;
            font-size: 1.2rem;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            background-color: #fff;
        }
        .card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .card-title {
            font-size: 1.1rem;
            font-weight: bold;
            margin-top: 0;
            margin-bottom: 0.5rem;
        }
        .category {
            margin-bottom: 2rem;
        }
        .nav {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        .nav-list {
            display: flex;
            flex-wrap: wrap;
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .nav-item {
            margin-right: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #f0f0f0;
            text-align: center;
            font-size: 0.9rem;
            color: #666;
        }
        .search-container {
            margin: 1rem 0;
        }
        .search-input {
            width: 100%;
            padding: 0.5rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        .external-link {
            display: inline-block;
            margin-left: 0.5rem;
            font-size: 0.8rem;
            color: #666;
        }
        
        /* Layout options */
        .view-toggles {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .view-toggle {
            padding: 0.5rem 1rem;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
            cursor: pointer;
        }
        .view-toggle.active {
            background-color: #0066cc;
            color: white;
        }
        
        /* Card Grid Layout */
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
        }
        
        /* Compact Layout */
        .compact-layout {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 0.5rem;
        }
        .compact-card {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 0.5rem;
            background-color: #fff;
            transition: all 0.2s ease;
            position: relative;
        }
        .compact-card:hover {
            background-color: #f8f9fa;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            z-index: 2;
        }
        .compact-card a {
            display: block;
            font-weight: bold;
        }
        .compact-card .tooltip {
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            z-index: 10;
            width: 250px;
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 0.75rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .compact-card:hover .tooltip {
            display: block;
        }
        
        /* Table Layout */
        .table-layout {
            width: 100%;
            border-collapse: collapse;
        }
        .table-layout th, .table-layout td {
            padding: 0.5rem;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        .table-layout th {
            font-weight: bold;
            background-color: #f8f9fa;
        }
        .table-layout tr:hover {
            background-color: #f8f9fa;
        }
        
        /* Category headers */
        .category-header {
            cursor: pointer;
            padding: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 4px;
            display: flex;
            align-items: center;
        }
        .category-header h2 {
            margin: 0;
            padding: 0;
            border: none;
            flex-grow: 1;
        }
        .toggle-icon {
            font-size: 1rem;
            transition: transform 0.3s ease;
        }
        .category-header.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }
        .category-content {
            overflow: hidden;
            max-height: 2000px;
            transition: max-height 0.5s ease-in-out;
        }
        .category-content.collapsed {
            max-height: 0;
            transition: max-height 0.3s ease-in-out;
        }
        
        /* TOC Grid */
        .toc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
            gap: 0.5rem;
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
        }
        .toc-grid a {
            padding: 0.25rem 0;
        }
        
        /* Collapsible TOC */
        .toc-header {
            cursor: pointer;
            padding: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 4px 4px 0 0;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #e0e0e0;
        }
        .toc-header h2 {
            margin: 0;
            border: none;
            padding: 0;
            flex-grow: 1;
            font-size: 1.2rem;
        }
        .toc-content {
            overflow: hidden;
            max-height: 1000px;
            transition: max-height 0.5s ease-in-out;
        }
        .toc-content.collapsed {
            max-height: 0;
            transition: max-height 0.3s ease-in-out;
        }
    </style>
</head>
<body>
    <h1>Simon Willison's Tools Collection</h1>
    <p>A local browsing version of <a href="https://tools.simonwillison.net/">tools.simonwillison.net</a>, a collection of HTML+JavaScript tools built with the assistance of LLMs.</p>
    
    <!-- TOC Collapsible Section -->
    <div>
        <div class="toc-header" onclick="toggleToc()">
            <h2>Alphabetical Tool Index</h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div class="toc-content">
            <div class="toc-grid">
"""

    # Add alphabetical TOC
    for name, file in all_tool_names:
        html_content += f'                <a href="{file}">{name}</a>\n'

    html_content += """
            </div>
        </div>
    </div>
    
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Search tools..." oninput="filterTools()">
    </div>
    
    <!-- View Toggle Buttons -->
    <div class="view-toggles">
        <button class="view-toggle active" onclick="switchView('compact-view')">Compact View</button>
        <button class="view-toggle" onclick="switchView('card-view')">Card View</button>
        <button class="view-toggle" onclick="switchView('table-view')">Table View</button>
    </div>
    
    <div class="nav">
        <h3>Categories</h3>
        <ul class="nav-list">
"""

    # Add navigation links
    for category in categories.keys():
        html_content += f'            <li class="nav-item"><a href="#{category.lower().replace(" ", "-")}">{category}</a></li>\n'
    
    if uncategorized_tools:
        html_content += f'            <li class="nav-item"><a href="#other-tools">Other Tools</a></li>\n'
    
    html_content += f'            <li class="nav-item"><a href="colophon.html">Colophon (Development History)</a></li>\n'
    
    html_content += """        </ul>
    </div>
"""

    # Add each category and its tools
    for i, (category, tools) in enumerate(categories.items()):
        category_id = category.lower().replace(" ", "-")
        html_content += f"""
    <div class="category" id="{category_id}">
        <div class="category-header" onclick="toggleCategory(this)">
            <h2>{category}</h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div class="category-content">
"""

        # Compact View
        html_content += f"""
            <div class="compact-layout tools-view" data-view="compact-view">
"""
        for tool in tools:
            # Handle external links differently
            if tool.get("is_external", False):
                # For external links, link directly to the external URL
                html_content += f"""
                <div class="compact-card" data-tool-name="{tool['name'].lower()}">
                    <a href="{tool['url']}" target="_blank">{tool['name']}</a>
                    <span class="external-link">(External)</span>
                    <div class="tooltip">{tool.get('description', 'External tool')}</div>
                </div>
"""
            else:
                # For local tools
                html_content += f"""
                <div class="compact-card" data-tool-name="{tool['name'].lower()}">
                    <a href="{tool['local_file']}">{tool['name']}</a>
                    <div class="tooltip">{tool.get('docs', 'No description available.')}</div>
                </div>
"""
        html_content += """
            </div>
"""

        # Card View (initially hidden)
        html_content += f"""
            <div class="card-grid tools-view" data-view="card-view" style="display: none;">
"""
        for tool in tools:
            # Handle external links differently
            if tool.get("is_external", False):
                # For external links, link directly to the external URL
                html_content += f"""
                <div class="card" data-tool-name="{tool['name'].lower()}">
                    <h3 class="card-title">
                        <a href="{tool['url']}" target="_blank">{tool['name']}</a>
                        <span class="external-link">(External)</span>
                    </h3>
                    <p class="card-description">{tool.get('description', 'External tool')}</p>
                </div>
"""
            else:
                # For local tools
                html_content += f"""
                <div class="card" data-tool-name="{tool['name'].lower()}">
                    <h3 class="card-title"><a href="{tool['local_file']}">{tool['name']}</a></h3>
                    <p class="card-description">{tool.get('docs', 'No description available.')}</p>
                </div>
"""
        html_content += """
            </div>
"""

        # Table View (initially hidden)
        html_content += """
            <div class="tools-view" data-view="table-view" style="display: none;">
                <table class="table-layout">
                    <thead>
                        <tr>
                            <th>Tool</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for tool in tools:
            # Handle external links differently
            if tool.get("is_external", False):
                # For external links, link directly to the external URL
                html_content += f"""
                        <tr data-tool-name="{tool['name'].lower()}">
                            <td><a href="{tool['url']}" target="_blank">{tool['name']} (External)</a></td>
                            <td>{tool.get('description', 'External tool')}</td>
                        </tr>
"""
            else:
                # For local tools
                html_content += f"""
                        <tr data-tool-name="{tool['name'].lower()}">
                            <td><a href="{tool['local_file']}">{tool['name']}</a></td>
                            <td>{tool.get('docs', 'No description available.')}</td>
                        </tr>
"""
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
"""

    # Add uncategorized tools section if any exist
    if uncategorized_tools:
        html_content += f"""
    <div class="category" id="other-tools">
        <div class="category-header" onclick="toggleCategory(this)">
            <h2>Other Tools</h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div class="category-content">
"""

        # Compact View
        html_content += f"""
            <div class="compact-layout tools-view" data-view="compact-view">
"""
        for tool in uncategorized_tools:
            html_content += f"""
                <div class="compact-card" data-tool-name="{tool['name'].lower()}">
                    <a href="{tool['local_file']}">{tool['name']}</a>
                    <div class="tooltip">{tool['docs'] if tool['docs'] else 'No description available.'}</div>
                </div>
"""
        html_content += """
            </div>
"""

        # Card View (initially hidden)
        html_content += f"""
            <div class="card-grid tools-view" data-view="card-view" style="display: none;">
"""
        for tool in uncategorized_tools:
            html_content += f"""
                <div class="card" data-tool-name="{tool['name'].lower()}">
                    <h3 class="card-title"><a href="{tool['local_file']}">{tool['name']}</a></h3>
                    <p class="card-description">{tool['docs'] if tool['docs'] else 'No description available.'}</p>
                </div>
"""
        html_content += """
            </div>
"""

        # Table View (initially hidden)
        html_content += """
            <div class="tools-view" data-view="table-view" style="display: none;">
                <table class="table-layout">
                    <thead>
                        <tr>
                            <th>Tool</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for tool in uncategorized_tools:
            html_content += f"""
                        <tr data-tool-name="{tool['name'].lower()}">
                            <td><a href="{tool['local_file']}">{tool['name']}</a></td>
                            <td>{tool['docs'] if tool['docs'] else 'No description available.'}</td>
                        </tr>
"""
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
"""

    # Add search and toggle scripts
    html_content += """
    <script>
        // Toggle TOC visibility
        function toggleToc() {
            const content = document.querySelector('.toc-content');
            content.classList.toggle('collapsed');
            document.querySelector('.toc-header').classList.toggle('collapsed');
        }
        
        // Toggle category sections 
        function toggleCategory(header) {
            const content = header.nextElementSibling;
            content.classList.toggle('collapsed');
            header.classList.toggle('collapsed');
        }
        
        // Switch between views
        function switchView(viewId) {
            // Get all view elements
            const views = document.querySelectorAll('.tools-view');
            
            // Hide all views
            views.forEach(view => {
                view.style.display = 'none';
            });
            
            // Show the selected view type
            const selectedViews = document.querySelectorAll(`.tools-view[data-view="${viewId}"]`);
            selectedViews.forEach(view => {
                if (viewId === 'compact-view' || viewId === 'card-view') {
                    view.style.display = 'grid';
                } else {
                    view.style.display = 'block';
                }
            });
            
            // Update active toggle button
            const toggles = document.querySelectorAll('.view-toggle');
            toggles.forEach(toggle => {
                toggle.classList.remove('active');
                if (toggle.textContent.toLowerCase().includes(viewId.split('-')[0])) {
                    toggle.classList.add('active');
                }
            });
            
            // Save preference to localStorage
            localStorage.setItem('preferredView', viewId);
        }
        
        // Filter tools based on search
        function filterTools() {
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            const toolElements = document.querySelectorAll('[data-tool-name]');
            
            toolElements.forEach(element => {
                const toolName = element.getAttribute('data-tool-name');
                const description = element.querySelector('.tooltip, .card-description, td:nth-child(2)');
                const descriptionText = description ? description.textContent.toLowerCase() : '';
                
                if (toolName.includes(searchText) || descriptionText.includes(searchText)) {
                    element.style.display = '';
                } else {
                    element.style.display = 'none';
                }
            });
            
            // Hide category headers if all tools in that category are hidden
            const categories = document.querySelectorAll('.category');
            categories.forEach(category => {
                // Count visible elements in the current view
                const currentView = document.querySelector('.tools-view:not([style*="display: none"])');
                if (!currentView) return;
                
                const viewType = currentView.getAttribute('data-view');
                const selector = viewType === 'table-view' ? 'tr:not([style*="display: none"])' : 
                                viewType === 'card-view' ? '.card:not([style*="display: none"])' : 
                                '.compact-card:not([style*="display: none"])';
                
                const visibleElements = category.querySelectorAll(selector).length;
                
                if (visibleElements === 0) {
                    category.style.display = 'none';
                } else {
                    category.style.display = '';
                }
            });
        }
        
        // Initialize sections and load previous view preference
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize all collapsible headers with the right toggle icon state
            document.querySelectorAll('.category-header.collapsed').forEach(header => {
                const content = header.nextElementSibling;
                if (content) {
                    content.classList.add('collapsed');
                }
            });
            
            // Load and apply the saved view preference
            const savedView = localStorage.getItem('preferredView');
            if (savedView) {
                switchView(savedView);
            }
        });
    </script>
"""

    # HTML footer
    html_content += """    
    <div class="footer">
        <p>These tools were created by <a href="https://simonwillison.net/">Simon Willison</a> and are available at <a href="https://github.com/simonw/tools">github.com/simonw/tools</a>.</p>
        <p>This is a local browsing version. For more details on how these tools were created, see the <a href="colophon.html">colophon</a>.</p>
    </div>
</body>
</html>
"""

    # Write the HTML to index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Local index page built successfully as index.html")
    return True

def main():
    """
    Main function to run the full build process
    
    Orchestrates the entire process:
    1. Gathers commit history and links
    2. Builds the colophon.html with development history
    3. Builds the index.html for browsing tools
    
    Returns:
        None
    """
    print("Starting local tools build process...")
    
    # Step 1: Run gather_links if needed
    try:
        if not os.path.exists("gathered_links.json"):
            print("gathered_links.json not found, gathering links...")
            data = run_gather_links()
        else:
            print("Using existing gathered_links.json")
            with open("gathered_links.json", "r") as f:
                data = json.load(f)
    except Exception as e:
        print(f"Error loading or gathering links: {e}")
        data = None
    
    # Step 2: Build the colophon
    if data:
        try:
            success = build_colophon(data)
            if not success:
                print("Failed to build colophon.html")
        except Exception as e:
            print(f"Error building colophon: {e}")
    
    # Step 3: Build the local index
    try:
        success = build_local_index()
        if not success:
            print("Failed to build index.html")
    except Exception as e:
        print(f"Error building index: {e}")
    
    print("\nBuild complete! You can now open index.html in your browser to explore the tools.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBuild process interrupted.")
    except Exception as e:
        print(f"\nBuild process failed with error: {e}")
