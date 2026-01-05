#!/bin/bash
set -e

# Make sure we have the full git history for finding commit dates:
if [ -f .git/shallow ]; then
    git fetch --unshallow
fi

echo "=== Building tools.joostvanderlaan.nl ==="

echo "Gathering links and metadata..."
python gather_links.py

# Only generate LLM summaries if GENERATE_LLM_DOCS is set
if [ "$GENERATE_LLM_DOCS" = "1" ]; then
    echo "Generating LLM documentation..."
    python write_docs.py
fi

echo "Building colophon page..."
python build_colophon.py

echo "Building dates.json..."
python build_dates.py

echo "Building index page..."
python build_index.py

echo "Building by-month page..."
python build_by_month.py

echo "Injecting footer.js into HTML files..."
# Get the git hash of the last commit that touched footer.js
FOOTER_HASH=$(git log -1 --format="%H" -- footer.js)
FOOTER_SHORT_HASH=$(echo "$FOOTER_HASH" | cut -c1-8)

# Insert footer.js script tag into all root-level .html files except index.html
# Only process files that are tracked in git
for file in *.html; do
  if [ -f "$file" ] && [ "$file" != "index.html" ] && git ls-files --error-unmatch "$file" > /dev/null 2>&1; then
    # Check if footer.js is not already included
    if ! grep -q 'src="footer.js' "$file"; then
      # Insert script tag before the LAST </body> tag using awk
      awk -v script="<script type=\"module\" src=\"footer.js?${FOOTER_SHORT_HASH}\"></script>" '
        { lines[NR] = $0 }
        /<\/body>/ { last_body = NR }
        END {
          for (i = 1; i <= NR; i++) {
            if (i == last_body) {
              sub(/<\/body>/, script "\n</body>", lines[i])
            }
            print lines[i]
          }
        }
      ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    fi
  fi
done

# Build redirects last so they don't get indexed in tools.json
echo "Building redirects from _redirects.json..."
python build_redirects.py

echo "=== Build complete! ==="
