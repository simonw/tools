#!/bin/bash
set -e

echo "=== Building tools.simonwillison.net for Cloudflare Pages ==="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --quiet markdown

# Run Python build scripts (but NOT write_docs.py which generates LLM descriptions)
echo "Gathering links and metadata..."
python gather_links.py

echo "Building colophon page..."
python build_colophon.py

# Convert README.md to index.html using Python's markdown library
echo "Converting README.md to index.html..."
python << 'PYTHON_SCRIPT'
import markdown

# Read README.md
with open('README.md', 'r') as f:
    content = f.read()

# Convert to HTML
md = markdown.Markdown(extensions=['extra'])
body_html = md.convert(content)

# Create full HTML page
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>tools.simonwillison.net</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 980px;
            margin: 0 auto;
            padding: 20px;
            color: #24292e;
        }}
        h1 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        h2 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            margin-top: 24px;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
            padding: 0.2em 0.4em;
        }}
    </style>
</head>
<body>
{body_html}
</body>
</html>
"""

# Write index.html
with open('index.html', 'w') as f:
    f.write(html)

print("index.html created successfully")
PYTHON_SCRIPT

echo "=== Build complete! ==="
