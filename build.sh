#!/bin/bash
set -e

# Mae sure we have the full git history for finding commit dates:
git fetch --unshallow

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
python build_index.py

echo "=== Build complete! ==="
