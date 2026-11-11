import pytest

import build_tags


def tags(html):
    api_tags, libraries, service_tags = build_tags.tags_for_html(html)
    return set(api_tags), set(libraries), set(service_tags)


def script(js, attrs=""):
    return f"<html><body><script {attrs}>{js}</script></body></html>"


@pytest.mark.parametrize(
    "js,expected",
    [
        ("new WebSocket('wss://example.com')", "websockets"),
        ("const ctx = new (window.AudioContext || window.webkitAudioContext)()", "web-audio"),
        ("navigator.clipboard.writeText('hi')", "clipboard-api"),
        ("canvas.getContext('2d')", "canvas-2d"),
        ("document.addEventListener('paste', handle)", "paste-events"),
        ("el.onpaste = handle", "paste-events"),
        ("const r = new THREE.WebGLRenderer()", "webgl"),
        ("history.pushState({}, '', '/x')", "history-api"),
        ("const m = await import('./mod.js')", "dynamic-import"),
    ],
)
def test_browser_api_detected(js, expected):
    assert expected in tags(script(js))[0]


@pytest.mark.parametrize(
    "html",
    [
        # Visible text, comments and strings are not code
        "<p>This tool uses new WebSocket() and localStorage</p>",
        script("// could use indexedDB or new WebSocket() here"),
        script("const help = 'call new WebSocket() or fetch()'"),
        # Non-JavaScript script blocks are skipped
        script('{"note": "new WebSocket()"}', 'type="application/json"'),
        # A property called fetch is not the global
        script("api.fetch('/x')"),
    ],
)
def test_no_false_positives(html):
    assert tags(html)[0] == set()


def test_locally_declared_name_is_not_the_global():
    assert "history-api" not in tags(script("const history = []; history.pushState(1)"))[0]
    assert "fetch" not in tags(script("function fetch() {} fetch()"))[0]
    # ...unless it is reached through window
    assert "fetch" in tags(script("function fetch() {} window.fetch('/x')"))[0]


def test_inline_handler_attribute_is_parsed():
    html = "<button onclick=\"navigator.clipboard.writeText('x')\">Copy</button>"
    assert "clipboard-api" in tags(html)[0]


def test_module_script():
    assert "es-modules" in tags(script("let a = 1", 'type="module"'))[0]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js", "marked"),
        ("https://cdn.jsdelivr.net/npm/marked/marked.min.js", "marked"),
        ("https://esm.run/@google/generative-ai", "@google/generative-ai"),
        ("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "three"),
        ("https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js", "three"),
        ("https://unpkg.com/react-dom@18/umd/react-dom.production.min.js", "react"),
        ("https://cdn.jsdelivr.net/pyodide/v0.27.5/full/pyodide.js", "pyodide"),
        ("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.min.js", "pdf.js"),
        ("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.min.mjs", "pdf.js"),
        ("https://plausible.io/js/script.js", None),
        ("https://example.com/marked.js", None),
        ("./llm-lib.js", None),
    ],
)
def test_library_from_url(url, expected):
    assert build_tags.library_from_url(url) == expected


def test_libraries_from_script_src_import_and_importmap():
    html = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.2.3/purify.min.js"></script>
    <script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js"}}</script>
    <script type="module">
    import { marked } from "https://esm.run/marked";
    const py = await loadPyodide({indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/"});
    </script>
    <a href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/">not loaded, just linked</a>
    """
    assert tags(html)[1] == {"dompurify", "three", "marked", "pyodide"}


def test_web_api_services():
    assert tags(script("fetch('https://api.github.com/gists')"))[2] == {"svc-github"}
    assert tags(script("fetch(`https://hn.algolia.com/api/v1/items/${id}`)"))[2] == {"svc-hacker-news"}
    # Subdomains and bare hostnames match too
    assert tags(script("const host = 'jetstream.us-east.bsky.network'"))[2] == {"svc-bluesky"}
    # A service reached only through its SDK
    html = script('import { GoogleGenerativeAI } from "https://esm.run/@google/generative-ai"', 'type="module"')
    assert tags(html)[2] == {"svc-gemini"}
    # Links in the HTML are not calls
    assert tags('<a href="https://api.github.com/">GitHub API</a>')[2] == set()
