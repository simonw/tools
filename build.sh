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

# Install Jekyll and theme if not present
echo "Setting up Jekyll..."
if ! command -v jekyll &> /dev/null; then
    echo "Jekyll not found, installing..."
    gem install jekyll bundler --no-document
fi

echo "Installing Jekyll theme..."
gem install jekyll-theme-primer --no-document

# Build Jekyll site
echo "Building Jekyll site..."
jekyll build

echo "=== Build complete! ==="


