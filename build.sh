#!/bin/bash
set -e

# Make sure we have the full git history for finding commit dates:
if [ -f .git/shallow ]; then
    git fetch --unshallow
fi

echo "=== Building tools.simonwillison.net ==="

echo "Gathering links and metadata..."
python gather_links.py

# Only generate LLM summaries if GENERATE_LLM_DOCS is set
if [ "$GENERATE_LLM_DOCS" = "1" ]; then
    echo "Generating LLM documentation..."
    python write_docs.py
fi

echo "Building colophon page..."
python build_colophon.py

echo "Building index page..."
python build_index.py

echo "Injecting footer.js into HTML files..."
# Get the git hash of the last commit that touched footer.js
FOOTER_HASH=$(git log -1 --format="%H" -- footer.js)
FOOTER_SHORT_HASH=$(echo "$FOOTER_HASH" | cut -c1-8)

# Insert footer.js script tag into all root-level .html files except index.html
for file in *.html; do
  if [ -f "$file" ] && [ "$file" != "index.html" ]; then
    # Check if footer.js is not already included
    if ! grep -q 'src="footer.js' "$file"; then
      # Insert script tag before the LAST </body> tag only
      # Using tac to reverse, replace first match, then reverse back
      tac "$file" | sed '0,/<\/body>/s|</body>|<script src="footer.js?'"${FOOTER_SHORT_HASH}"'"></script>\n</body>|' | tac > "$file.tmp" && mv "$file.tmp" "$file"
    fi
  fi
done

echo "=== Build complete! ==="
