# Notes for coding agents

## Deterministic tagging (`build_tags.py`)

`build_tags.py` writes `tags.json`, which `homepage-tags.js` uses to render the
three tag clouds on the index page. Tags are never hand-assigned or
LLM-generated: each tool's HTML is parsed with tree-sitter, its inline
`<script>` blocks and `on*` attributes are parsed as JavaScript, and the syntax
trees are matched against tables in `build_tags.py`. Text in visible HTML,
comments and unrelated strings must never produce a tag.

There are three kinds of tag, each with its own table:

- **Browser APIs** (`kind: "browser-api"`): the `RULES` list. Each rule is
  `(tag, label, matchers)`; the matcher kinds (`g:`, `m:`, `p:`, `s:`, `e:`,
  `x:`, `l:`) are documented in the comment above `RULES`.
- **JavaScript libraries** (`kind: "library"`): detected from CDN URLs by
  `library_from_url()`. A library only becomes a tag once `LIBRARY_MIN_TOOLS`
  tools use it. Add a CDN to `NPM_CDN_HOSTS`/`CDN_HOSTS`, merge differently
  named packages with `LIBRARY_ALIASES`, and set display names in
  `LIBRARY_LABELS`.
- **Web APIs** (`kind: "web-api"`): the `SERVICES` list of
  `(tag, label, hosts, libraries)`. A tool gets the tag if a URL string in its
  JavaScript has one of the hosts (or a subdomain), or if it loads one of the
  listed SDK libraries.

### Updating

1. Edit the relevant table. Prefer the most specific matcher that works, for
   example `m:navigator.clipboard` rather than `p:clipboard`.
2. If an API is only reached through a library (WebGL via three.js), add a
   matcher for the library's own entry point or an `l:` URL matcher rather
   than trying to parse the library.
3. Add a case to `tests/test_build_tags.py`, including a false-positive case
   if the new matcher is broad.
4. Regenerate and review what changed (see below).

### Testing

The tests run in CI on every push (`.github/workflows/test.yml`), and
`build.sh` runs `build_tags.py` as part of the GitHub Pages deploy
(`.github/workflows/pages.yml`), which installs the tree-sitter packages with
pip. If you add a dependency to `build_tags.py`, add it in three places: the
script's inline metadata, `pyproject.toml` and the pip install line in
`pages.yml`.

```bash
uv run pytest tests/test_build_tags.py
```

Then regenerate `tags.json` and check the counts for the tags you touched. It
needs an up to date `gathered_links.json`, so run `gather_links.py` first if
tools have been added:

```bash
python gather_links.py
uv run build_tags.py
python -c "import json; [print(t['count'], t['kind'], t['label']) for t in json.load(open('tags.json'))['tags']]"
```

To see the result in a browser, rebuild the index and serve the directory:

```bash
uv run --with markdown build_index.py
python -m http.server 8000
```

`tags.json`, `index.html`, `tools.json` and `gathered_links.json` are build
outputs and are not committed.
