#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "markdown",
# ]
# ///

"""
Build a local index.html for browsing Simon's tools collection.

This script creates a simple index page for local browsing of the HTML tools,
using their .docs.md files for descriptions. It sorts tools both alphabetically
and by most recent commit date.

Usage:
    python build_local_index.py
    # or
    uv run --no-project ./build_local_index.py
"""

import json
import os
import re
import subprocess
from pathlib import Path
import markdown
from datetime import datetime
import html


def get_file_commit_details(file_path):
    """
    Get the commit details for a specific file from git.
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


def gather_links():
    """
    Gather commit histories and URLs for all HTML files in current directory.
    Returns a dictionary of file information.
    """
    print("Gathering information about HTML files...")
    
    # Get current directory
    current_dir = Path.cwd()

    # Find all HTML files
    html_files = list(current_dir.glob("*.html"))
    
    # Skip index.html and colophon.html if they exist
    html_files = [f for f in html_files if f.name not in ["index.html", "colophon.html"]]

    # Dictionary to store results
    results = {"pages": {}}

    # Process each HTML file
    for html_file in html_files:
        file_name = html_file.name
        print(f"Processing {file_name}...")

        # Get commit details for this file
        commits = get_file_commit_details(html_file)

        if not commits:
            print(f"  No commit history found for {file_name}")
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

        # Add to results
        results["pages"][file_name] = {"commits": commits, "urls": unique_urls}

    print(f"Processed {len(html_files)} files")
    print(f"Found details for {len(results['pages'])} files")
    
    return results


def load_docs_for_file(html_file):
    """
    Load documentation for a given HTML file from the corresponding .docs.md file.
    Returns the documentation content as a string.
    """
    docs_file = html_file.replace(".html", ".docs.md")
    
    if os.path.exists(docs_file):
        with open(docs_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Remove any "Generated from commit" comment at the end
            if "<!-- Generated from commit" in content:
                content = content.split("<!-- Generated from commit")[0].strip()
            return content
    return ""


def build_index_html(data):
    """
    Build the index.html file with all tools.
    """
    print("Building index.html...")
    
    # Get all HTML files in the directory (source of truth)
    all_html_files = [f for f in Path(".").glob("*.html") 
                     if f.name not in ["index.html", "colophon.html"]]
    
    # Load docs for each file
    tools = []
    for html_file in all_html_files:
        file_name = html_file.name
        name = file_name.replace(".html", "")
        docs = load_docs_for_file(file_name)
        
        # Get most recent commit date if available
        commit_date = None
        if file_name in data["pages"]:
            commits = data["pages"][file_name]["commits"]
            if commits:
                # First commit is the most recent since they're returned newest-first
                commit_date = commits[0]["date"]
                # Format date as YYYY-MM-DD
                try:
                    dt = datetime.fromisoformat(commit_date)
                    commit_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
        
        tools.append({
            "name": name,
            "file_name": file_name,
            "docs": docs,
            "commit_date": commit_date
        })
    
    # Sort tools by name (alphabetical)
    tools_by_name = sorted(tools, key=lambda x: x["name"].lower())
    
    # Also prepare a sort by date
    tools_by_date = sorted(
        [t for t in tools if t["commit_date"]],  # Only include tools with dates
        key=lambda x: x["commit_date"] if x["commit_date"] else "0",
        reverse=True  # Newest first
    )
    
    # Start building the HTML content
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simon Willison's Tools</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            max-width: 1000px;
            margin: 0 auto;
            padding: 1rem;
            color: #1a1a1a;
        }
        h1 {
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        p {
            margin: 1rem 0;
        }
        .search-container {
            margin: 1.5rem 0;
            position: sticky;
            top: 0;
            background-color: white;
            padding: 1rem 0;
            z-index: 10;
            width: 100%;
            border-bottom: 1px solid #f0f0f0;
        }
        .search-input {
            width: 100%;
            padding: 0.75rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-sizing: border-box;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: border-color 0.4s, box-shadow 0.4s;
        }
        .search-input:focus {
            border-color: #0066cc;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.2);
            outline: none;
        }
        .sort-options {
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
            align-items: center;
        }
        .sort-option {
            cursor: pointer;
            padding: 0.5rem 0.75rem;
            border-radius: 4px;
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            font-size: 0.9rem;
            transition: background-color 0.4s;
        }
        .sort-option:hover {
            background-color: #e9ecef;
        }
        .sort-option.active {
            background-color: #0066cc;
            color: white;
            font-weight: bold;
        }
        .tool-list {
            margin-top: 1rem;
            padding-bottom: 60px; /* Space for the back-to-top button */
        }
        .tool-item {
            margin-bottom: 1.5rem;
            padding: 1rem;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: box-shadow 0.4s ease-in-out;
        }
        .tool-item:hover {
            box-shadow: 2px 4px 8px rgba(0,0,0,0.2);
        }
        .tool-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .tool-name-date {
            flex: 1;
        }
        .tool-name {
            font-size: 1.2rem;
            font-weight: bold;
            margin: 0;
        }
        .tool-date {
            color: #666;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }
        .use-button {
            flex-shrink: 0;
            background-color: #0066cc;
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.5rem;
            box-sizing: border-box;
            cursor: pointer;
            font-size: 0.9rem;
            margin-left: 1rem;
            transition: background-color 0.4s, box-shadow 0.4s ease-in;
        }
        .use-button:hover {
            background-color: #0052a3;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.2);
        }
        .use-button:focus {
            outline: 2px solid #0066cc;
            outline-offset: 2px;
        }
        .tool-docs {
            margin-top: 0.5rem;
            text-align: left;
            display: none;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s ease-out;
        }
        .tool-docs.expanded {
            max-height: 1000px;
            transition: max-height 0.4s ease-in;
            display: block;
        }
        .toggle-docs {
            background: none;
            border: none;
            color: #0066cc;
            padding: 0.25rem 0;
            cursor: pointer;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            margin-top: 0.5rem;
        }
        .toggle-docs:hover {
            text-decoration: underline;
        }
        .toggle-docs .icon {
            margin-left: 0.25rem;
            transition: transform 0.4s;
        }
        .toggle-docs.expanded .icon {
            transform: rotate(180deg);
        }
        .footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #f0f0f0;
            text-align: center;
            font-size: 0.9rem;
            color: #666;
        }
        .no-results {
            padding: 2rem;
            text-align: center;
            color: #666;
            font-style: italic;
        }
        #backToTop {
            position: fixed;
            bottom: -60px;
            right: 30px;
            background-color: rgba(0, 102, 204, 0.8);
            color: white;
            border: none;
            border-radius: 50px;
            width: 50px;
            height: 50px;
            font-size: 24px;
            cursor: pointer;
            opacity: 0;
            transition: bottom 0.4s, opacity 0.4s;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        #backToTop.visible {
            bottom: 30px;
            opacity: 0.9;
        }
        #backToTop:hover {
            background-color: rgba(0, 82, 163, 0.9);
            opacity: 1;
        }
        #backToTop:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.3);
        }
        @media (max-width: 768px) {
            .sort-options {
                flex-wrap: wrap;
            }
            .sort-option {
                flex-grow: 1;
                text-align: center;
            }
            #toolsContainer .tool-item {
                text-align: center;
            }
            .tool-item .tool-header {
                float: none;
                text-align: start;
                flex-direction: column;
                align-items: flex-start;
            }
            .use-button {
                margin-left: 0;
                margin-top: 0.5rem;
                width: 100%;
                text-align: center;
            }
            #backToTop {
                width: 45px;
                height: 45px;
                right: 20px;
                font-size: 20px;
            }
            #backToTop.visible {
                bottom: 20px;
            }
        }
    </style>
</head>
<body>
    <h1>Simon Willison's Tools</h1>
    
    <p>This is a local browsing version of <a href="https://tools.simonwillison.net/" target="_blank">tools.simonwillison.net</a>, a collection of HTML+JavaScript tools mostly built with the assistance of LLMs.</p>
    
    <p>Click "Use Tool" to launch any tool directly in your browser, no server required. Each tool works entirely client-side using HTML, CSS, and JavaScript.</p>
    
    <div class="search-container">
        <div style="position: relative; width: 100%;">
            <input type="text" id="searchInput" class="search-input" placeholder="Press / to search all tools..." aria-label="Search tools" oninput="filterTools()">
            <button id="clearSearch" aria-label="Clear search" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; display: none; cursor: pointer; font-size: 1rem; color: #666; padding: 0.2rem 0.5rem;">␛ ×</button>
        </div>
    </div>
    
    <div class="sort-options">
        <span>Sort by: </span>
        <button class="sort-option active" onclick="sortTools('alpha')" aria-pressed="true">Alphabetical</button>
        <button class="sort-option" onclick="sortTools('date')" aria-pressed="false">Most Recent</button>
    </div>
    
    <!-- Tools content -->
    <div id="toolsContainer" class="tool-list">
"""

    # Add all tools by default (alphabetically)
    for tool in tools_by_name:
        date_str = ""
        if tool["commit_date"]:
            date_str = f"<div class='tool-date'>Last updated: {tool['commit_date']}</div>"
        
        docs_html = ""
        if tool["docs"]:
            docs_html = f"<div>{markdown.markdown(tool['docs'])}</div>"
        else:
            docs_html = "<div><em>No description available.</em></div>"
        
        html_content += f"""
        <div class="tool-item" data-name="{tool['name'].lower()}" data-date="{tool.get('commit_date', '')}">
            <div class="tool-header">
                <div class="tool-name-date">
                    <h2 class="tool-name">{tool['name']}</h2>
                    {date_str}
                </div>
                <a href="{tool['file_name']}" class="use-button" aria-label="Use {tool['name']} tool">Use Tool</a>
            </div>
            <button class="toggle-docs" onclick="toggleDocs(this)" aria-expanded="false">
                <span class="icon">▼</span> Show description
            </button>
            <div class="tool-docs" aria-hidden="true">
                {docs_html}
            </div>
        </div>
"""

    html_content += """
    </div>
    
    <div id="noResults" class="no-results" style="display: none;" aria-live="polite">
        No tools match your search.
    </div>
    
    <button id="backToTop" onclick="scrollToTop()" aria-label="Back to top">
        🔝
    </button>
    
    <div class="footer">
        <p>These tools were created by <a href="https://simonwillison.net/" target="_blank">Simon Willison</a> 
           and are available at <a href="https://github.com/simonw/tools" target="_blank">github.com/simonw/tools</a>.</p>
        <p>For development history and details about how these tools were created, see the <a href="colophon.html">colophon</a>.</p>
    </div>
    
    <script>
        // Toggle doc descriptions visibility
        function toggleDocs(button) {
            const toolItem = button.closest('.tool-item');
            const docsDiv = toolItem.querySelector('.tool-docs');
            
            docsDiv.classList.toggle('expanded');
            button.classList.toggle('expanded');
            
            const isExpanded = docsDiv.classList.contains('expanded');
            button.setAttribute('aria-expanded', isExpanded);
            docsDiv.setAttribute('aria-hidden', !isExpanded);
            
            button.innerHTML = isExpanded ? 
                '<span class="icon">▲</span> Hide description' : 
                '<span class="icon">▼</span> Show description';
        }
        // Filter tools based on search
        function filterTools() {
            const searchText = document.getElementById('searchInput').value.toLowerCase().trim();
            const toolItems = document.querySelectorAll('.tool-item');
            let foundAny = false;
                
            if (searchText === '') {
                // If search is empty, show all tools
                toolItems.forEach(item => {
                    item.style.display = '';

                    // Reset any highlighted text
                    const marks = item.querySelectorAll('mark');
                    marks.forEach(mark => {
                        const parent = mark.parentNode;
                        parent.replaceChild(document.createTextNode(mark.textContent), mark);
                        parent.normalize();
                    });
                });
                document.getElementById('noResults').style.display = 'none';
                return;
            }
            
            // Split search into terms for better matching
            const searchTerms = searchText.split(/\s+/);
            
            toolItems.forEach(item => {
                const toolName = item.getAttribute('data-name');
                const toolContent = item.textContent.toLowerCase();
                
                // Check if ALL search terms are found in either name or content
                const allTermsFound = searchTerms.every(term => 
                    toolName.includes(term) || toolContent.includes(term)
                );
                
                if (allTermsFound) {
                    item.style.display = '';
                    foundAny = true;
                    
                    // If we find a match and there's a description, expand it to show where the match is
                    if (searchTerms.some(term => !toolName.includes(term) && toolContent.includes(term))) {
                        const docsButton = item.querySelector('.toggle-docs');
                        const docsDiv = item.querySelector('.tool-docs');

                        if (!docsDiv.classList.contains('expanded')) {
                            docsButton.setAttribute('aria-expanded', 'true');
                            docsDiv.classList.add('expanded');
                            docsDiv.setAttribute('aria-hidden', 'false');
                            docsButton.innerHTML = 'Hide description <span class="icon">▲</span>';
                        }

                        // Highlight search terms in the description
                        if (searchTerms.length > 0 && searchTerms[0].length > 2) {
                            const descriptionParagraphs = docsDiv.querySelectorAll('p');
                            descriptionParagraphs.forEach(paragraph => {
                                const originalText = paragraph.innerHTML;
                                let highlightedText = originalText;

                                searchTerms.forEach(term => {
                                    if (term.length > 2) { // Only highlight terms with 3+ chars
                                        const regex = new RegExp('(' + term + ')', 'gi');
                                        highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
                                    }
                                });
                                
                                paragraph.innerHTML = highlightedText;
                            });
                        }
                    }
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Show/hide "No results" message
            document.getElementById('noResults').style.display = foundAny ? 'none' : 'block';
        }
        
        // Add clear search functionality
        document.getElementById('clearSearch').addEventListener('click', function() {
            document.getElementById('searchInput').value = '';
            this.style.display = 'none';
            filterTools();
            document.getElementById('searchInput').focus();
        });

        // Update filterTools to show/hide clear button
        const originalFilterTools = filterTools;
        filterTools = function() {
            const searchText = document.getElementById('searchInput').value.trim();
            document.getElementById('clearSearch').style.display = searchText ? 'block' : 'none';
            originalFilterTools();
        };

        // Sort tools by name or date
        function sortTools(sortBy) {
            // Update active sort option and aria-pressed state
            document.querySelectorAll('.sort-option').forEach(option => {
                option.classList.remove('active');
                option.setAttribute('aria-pressed', 'false');
            });
            event.target.classList.add('active');
            event.target.setAttribute('aria-pressed', 'true');
            
            const container = document.getElementById('toolsContainer');
            const toolItems = Array.from(container.querySelectorAll('.tool-item'));
            
            if (sortBy === 'alpha') {
                toolItems.sort((a, b) => {
                    return a.getAttribute('data-name').localeCompare(b.getAttribute('data-name'));
                });
            } else if (sortBy === 'date') {
                toolItems.sort((a, b) => {
                    const dateA = a.getAttribute('data-date') || '0';
                    const dateB = b.getAttribute('data-date') || '0';
                    return dateB.localeCompare(dateA); // Newest first
                });
            }
            
            // Remove all tool items
            toolItems.forEach(item => {
                container.removeChild(item);
            });
            
            // Add them back in the new order
            toolItems.forEach(item => {
                container.appendChild(item);
            });
        }
        
        // Back to top functionality
        window.onscroll = function() {
            const backToTopButton = document.getElementById('backToTop');
            if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
                backToTopButton.classList.add('visible');
            } else {
                backToTopButton.classList.remove('visible');
            }
        };
        
        function scrollToTop() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }

        // Handle keyboard navigation
        document.addEventListener('keydown', function(e) {
            // Clear search with Escape key
            if (e.key === 'Escape' && document.getElementById('searchInput').value) {
                document.getElementById('clearSearch').click();
            }
            
            // Focus search with / or /
            if (e.key === '/') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
            // If pressing Tab key and search is active
            if (e.key === 'Tab' && document.activeElement === document.getElementById('searchInput')) {
                // Get all visible tool items
                const visibleItems = Array.from(document.querySelectorAll('.tool-item')).filter(
                    item => item.style.display !== 'none'
                );
                
                // If there are visible items
                if (visibleItems.length > 0) {
                    // Find the first use button in a visible item
                    const firstButton = visibleItems[0].querySelector('.use-button');
                    if (firstButton && !e.shiftKey) {
                        // Set focus to it if Tab without Shift
                        e.preventDefault();
                        firstButton.focus();
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

    # Write to index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("Successfully created index.html")


def check_colophon_exists():
    """Check if colophon.html exists, try to build it if not."""
    if os.path.exists("colophon.html"):
        return True
        
    print("Note: colophon.html doesn't exist. Attempting to build it...")
    try:
        # Try running build_colophon.py directly
        if os.path.exists("build_colophon.py"):
            subprocess.run(["python", "build_colophon.py"], check=True)
            return True
        # Or try using UV if available
        subprocess.run(["uv", "run", "--no-project", "--with", "markdown", "./build_colophon.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to build colophon: {e}")
        return False


def main():
    """Main function to build the local index."""
    print("Building local index for Simon's tools collection...")
    
    # Step 1: Gather links and commit information
    data = gather_links()
    
    # Step 2: Build the index.html
    build_index_html(data)
    
    # Step 3: Check if colophon exists
    has_colophon = check_colophon_exists()
    
    print("\nDone! Open index.html in your browser to browse the tools collection.")
    if has_colophon:
        print("You can also view the development history in colophon.html.")
    else:
        print("To view development history, run build_colophon.py.")


if __name__ == "__main__":
    main()
