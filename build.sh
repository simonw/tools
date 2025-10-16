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

# Install Jekyll if not present
echo "Setting up Jekyll..."
if ! command -v jekyll &> /dev/null; then
    echo "Jekyll not found, installing..."
    gem install jekyll bundler --no-document
fi

# Build Jekyll site
echo "Building Jekyll site..."
jekyll build

echo "=== Build complete! ==="


