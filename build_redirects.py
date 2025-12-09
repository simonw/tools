#!/usr/bin/env python3
"""
Generate HTML redirect files from _redirects.json.

This script reads the _redirects.json file and generates HTML redirect pages
for each entry. The JSON file should be an object mapping source names to
target URLs (either absolute paths like "/foo" or full URLs like "https://...").
"""
import json
from pathlib import Path

REDIRECT_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={url}">
    <title>Redirecting...</title>
</head>
<body>
    <p>If you are not redirected automatically, follow this <a href="{url}">link</a>.</p>
</body>
</html>
'''


def build_redirects():
    redirects_file = Path("_redirects.json")
    if not redirects_file.exists():
        print("No _redirects.json found, skipping redirect generation")
        return

    with open(redirects_file) as f:
        redirects = json.load(f)

    for source, target in redirects.items():
        html_file = Path(f"{source}.html")
        html_content = REDIRECT_TEMPLATE.format(url=target)
        html_file.write_text(html_content)
        print(f"Generated redirect: {source}.html -> {target}")


if __name__ == "__main__":
    build_redirects()
