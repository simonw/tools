#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tree-sitter>=0.23",
#     "tree-sitter-html",
#     "tree-sitter-javascript",
# ]
# ///
"""Generate tags.json: which browser JavaScript APIs each tool uses.

Detection is deterministic. Each HTML file is parsed with tree-sitter's HTML
grammar, the contents of its inline <script> elements and on* handler
attributes are parsed with the JavaScript grammar, and the resulting syntax
trees are matched against the RULES table below. Text that merely mentions an
API in visible HTML, a comment or a string is never matched.

Run with: uv run build_tags.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import tree_sitter_html
import tree_sitter_javascript
from tree_sitter import Language, Parser

from build_by_month import _extract_summary, _parse_iso_datetime

GATHERED_LINKS_PATH = Path("gathered_links.json")
OUTPUT_PATH = Path("tags.json")

HTML_PARSER = Parser(Language(tree_sitter_html.language()))
JS_PARSER = Parser(Language(tree_sitter_javascript.language()))

# <script type="..."> values that contain JavaScript (the grammar handles JSX)
JS_SCRIPT_TYPES = {
    "",
    "module",
    "text/javascript",
    "application/javascript",
    "text/babel",
    "text/jsx",
}
GLOBAL_OBJECTS = {"window", "globalThis", "self"}

# Each rule is (tag, label, matchers). A page gets the tag if any matcher hits.
# Matcher kinds:
#   g:NAME        reference to a global identifier (also window.NAME, new NAME)
#   m:a.b.c       member expression chain, after stripping window./globalThis.
#   p:NAME        property name accessed on any object (x.NAME)
#   s:METHOD:ARG  x.METHOD("ARG", ...) with a string literal first argument
#   e:EVENT       addEventListener("EVENT"), x.onEVENT = or an onEVENT attribute
#   x:NAME        special flags set by the walker
#   l:TEXT        a <script src> or import URL containing TEXT, for APIs that
#                 are only reached through a library
RULES: list[tuple[str, str, list[str]]] = [
    # Network
    ("fetch", "fetch()", ["g:fetch"]),
    ("xhr", "XMLHttpRequest", ["g:XMLHttpRequest"]),
    ("websockets", "WebSockets", ["g:WebSocket"]),
    ("server-sent-events", "Server-sent events", ["g:EventSource"]),
    ("webrtc", "WebRTC", ["g:RTCPeerConnection"]),
    ("abort-controller", "AbortController", ["g:AbortController"]),
    ("streams", "Streams", ["g:ReadableStream", "g:WritableStream", "g:TransformStream", "p:getReader"]),
    ("compression-streams", "Compression Streams", ["g:CompressionStream", "g:DecompressionStream"]),
    # Audio, video, speech
    ("web-audio", "Web Audio", ["g:AudioContext", "g:webkitAudioContext", "g:OfflineAudioContext"]),
    ("speech-synthesis", "Speech synthesis", ["g:speechSynthesis", "g:SpeechSynthesisUtterance"]),
    ("speech-recognition", "Speech recognition", ["g:SpeechRecognition", "g:webkitSpeechRecognition"]),
    ("get-user-media", "Camera / microphone", ["p:getUserMedia"]),
    ("screen-capture", "Screen capture", ["p:getDisplayMedia"]),
    ("media-recorder", "MediaRecorder", ["g:MediaRecorder"]),
    ("webcodecs", "WebCodecs", ["g:VideoEncoder", "g:VideoDecoder", "g:AudioEncoder", "g:AudioDecoder", "g:VideoFrame"]),
    ("web-midi", "Web MIDI", ["p:requestMIDIAccess"]),
    # Graphics
    ("canvas-2d", "Canvas 2D", ["s:getContext:2d"]),
    ("webgl", "WebGL", [
        "s:getContext:webgl", "s:getContext:webgl2", "s:getContext:experimental-webgl",
        # three.js: THREE.WebGLRenderer or a named import of WebGLRenderer
        "p:WebGLRenderer", "g:WebGLRenderer",
        "l:maplibre-gl", "l:mapbox-gl", "l:deck.gl", "l:babylon", "l:pixi",
    ]),
    ("webgpu", "WebGPU", ["m:navigator.gpu"]),
    ("offscreen-canvas", "OffscreenCanvas", ["g:OffscreenCanvas"]),
    ("image-bitmap", "createImageBitmap", ["g:createImageBitmap"]),
    ("request-animation-frame", "requestAnimationFrame", ["g:requestAnimationFrame"]),
    ("view-transitions", "View Transitions", ["p:startViewTransition"]),
    # Storage and files
    ("localstorage", "localStorage", ["g:localStorage"]),
    ("sessionstorage", "sessionStorage", ["g:sessionStorage"]),
    ("indexeddb", "IndexedDB", ["g:indexedDB"]),
    ("cache-api", "Cache API", ["g:caches"]),
    ("opfs", "Origin private file system", ["m:navigator.storage.getDirectory"]),
    ("file-system-access", "File System Access", ["g:showOpenFilePicker", "g:showSaveFilePicker", "g:showDirectoryPicker"]),
    ("file-reader", "FileReader", ["g:FileReader"]),
    ("blob-urls", "Blob URLs", ["m:URL.createObjectURL"]),
    # Clipboard, drag and drop, sharing
    ("clipboard-api", "Clipboard API", ["m:navigator.clipboard"]),
    ("paste-events", "Paste events", ["e:paste"]),
    ("exec-command", "execCommand", ["p:execCommand"]),
    ("drag-and-drop", "Drag and drop", ["e:drop", "e:dragover", "e:dragstart"]),
    ("web-share", "Web Share", ["m:navigator.share"]),
    ("selection", "Selection API", ["g:getSelection", "m:document.getSelection"]),
    # Concurrency and code loading
    ("web-workers", "Web Workers", ["g:Worker", "g:SharedWorker"]),
    ("service-workers", "Service Workers", ["m:navigator.serviceWorker"]),
    ("webassembly", "WebAssembly", ["g:WebAssembly"]),
    ("es-modules", "ES modules", ["x:module"]),
    ("dynamic-import", "Dynamic import()", ["x:dynamic-import"]),
    ("broadcast-channel", "BroadcastChannel", ["g:BroadcastChannel"]),
    ("post-message", "postMessage", ["p:postMessage"]),
    # URLs and navigation
    ("history-api", "History API", ["m:history.pushState", "m:history.replaceState", "e:popstate"]),
    ("url-hash", "URL hash state", ["m:location.hash", "e:hashchange"]),
    ("url-search-params", "URLSearchParams", ["g:URLSearchParams"]),
    # DOM
    ("web-components", "Web Components", ["m:customElements.define", "p:attachShadow"]),
    ("intersection-observer", "IntersectionObserver", ["g:IntersectionObserver"]),
    ("resize-observer", "ResizeObserver", ["g:ResizeObserver"]),
    ("mutation-observer", "MutationObserver", ["g:MutationObserver"]),
    ("dom-parser", "DOMParser", ["g:DOMParser"]),
    ("dialog", "<dialog>", ["p:showModal"]),
    ("popover", "Popover", ["p:showPopover", "p:togglePopover"]),
    ("fullscreen", "Fullscreen", ["p:requestFullscreen", "p:webkitRequestFullscreen"]),
    ("match-media", "matchMedia", ["g:matchMedia"]),
    # Input and devices
    ("pointer-events", "Pointer events", ["e:pointerdown", "e:pointermove", "e:pointerup"]),
    ("touch-events", "Touch events", ["e:touchstart", "e:touchmove", "e:touchend"]),
    ("gamepad", "Gamepad", ["m:navigator.getGamepads"]),
    ("geolocation", "Geolocation", ["m:navigator.geolocation"]),
    ("device-orientation", "Device orientation", ["e:deviceorientation", "e:devicemotion"]),
    ("notifications", "Notifications", ["g:Notification"]),
    ("wake-lock", "Wake Lock", ["m:navigator.wakeLock"]),
    ("vibration", "Vibration", ["m:navigator.vibrate"]),
    ("web-bluetooth", "Web Bluetooth", ["m:navigator.bluetooth"]),
    ("web-usb", "WebUSB", ["m:navigator.usb"]),
    ("web-serial", "Web Serial", ["m:navigator.serial"]),
    ("barcode-detector", "BarcodeDetector", ["g:BarcodeDetector"]),
    ("eyedropper", "EyeDropper", ["g:EyeDropper"]),
    # Misc
    ("web-crypto", "Web Crypto", ["m:crypto.subtle"]),
    ("crypto-random", "crypto random values", ["m:crypto.getRandomValues", "m:crypto.randomUUID"]),
    ("text-encoding", "TextEncoder / TextDecoder", ["g:TextEncoder", "g:TextDecoder"]),
    ("intl", "Intl", ["g:Intl"]),
    ("built-in-ai", "Built-in AI", ["g:LanguageModel", "g:Summarizer", "g:Translator", "g:LanguageDetector"]),
]


# CDN-loaded JavaScript libraries. Only libraries used by at least this many
# tools become tags.
LIBRARY_MIN_TOOLS = 2
NPM_CDN_HOSTS = {
    "cdn.jsdelivr.net",
    "fastly.jsdelivr.net",
    "unpkg.com",
    "esm.sh",
    "esm.run",
    "cdn.skypack.dev",
    "ga.jspm.io",
}
CDN_HOSTS = NPM_CDN_HOSTS | {
    "cdnjs.cloudflare.com",
    "cdn.tailwindcss.com",
    "pyodide-cdn2.iodide.io",
}
# Different CDNs (and npm vs cdnjs) use different names for the same library
LIBRARY_ALIASES = {
    "three.js": "three",
    "pdfjs-dist": "pdf.js",
    "moment.js": "moment",
    "babel-standalone": "babel",
    "@babel/standalone": "babel",
    "react-dom": "react",
    "highlightjs": "highlight.js",
    "cdn-release": "highlight.js",  # jsDelivr gh/highlightjs/cdn-release
    "@highlightjs/cdn-assets": "highlight.js",
    "chart.js": "chart.js",
    "katex": "katex",
}
LIBRARY_LABELS = {
    "babel": "Babel",
    "chart.js": "Chart.js",
    "cropperjs": "Cropper.js",
    "d3": "D3",
    "dompurify": "DOMPurify",
    "highlight.js": "highlight.js",
    "jszip": "JSZip",
    "katex": "KaTeX",
    "leaflet": "Leaflet",
    "marked": "Marked",
    "pdf.js": "PDF.js",
    "pyodide": "Pyodide",
    "react": "React",
    "tailwindcss": "Tailwind CSS",
    "tesseract.js": "Tesseract.js",
    "three": "three.js",
}
_NPM_PACKAGE_RE = re.compile(r"((?:@[^/@]+/)?[^/@]+)")


def library_from_url(url: str) -> str | None:
    """Normalized library name for a CDN URL, or None if it isn't one.

    https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js -> "marked"
    https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js -> "three"
    """
    match = re.match(r"(?:https?:)?//([^/]+)/?(.*)", url.strip(), re.IGNORECASE)
    if not match:
        return None
    host = match.group(1).lower()
    path = match.group(2).split("?")[0].split("#")[0]
    if host not in CDN_HOSTS:
        return None
    name = None
    if "pyodide" in host or path.startswith("pyodide/"):
        name = "pyodide"
    elif host == "cdn.tailwindcss.com":
        name = "tailwindcss"
    elif host == "cdnjs.cloudflare.com":
        parts = path.split("/")  # ajax/libs/NAME/VERSION/file.js
        if len(parts) >= 4 and parts[:2] == ["ajax", "libs"]:
            name = parts[2]
    else:
        if path.startswith("gh/"):  # jsDelivr GitHub: gh/USER/REPO@VERSION/file
            parts = path.split("/")
            path = parts[2] if len(parts) > 2 else ""
        path = re.sub(r"^(npm/|npm:|v\d+/|stable/)", "", path)
        package = _NPM_PACKAGE_RE.match(path)
        if package:
            name = package.group(1)
    if not name:
        return None
    name = name.lower()
    return LIBRARY_ALIASES.get(name, name)


# External web APIs (services the tool talks to over the network), detected
# from hosts in URL strings in the tool's JavaScript. A host matches if it
# equals an entry or is a subdomain of it. Some services are only reached
# through an SDK, so a service can also be implied by a CDN library.
# (tag, label, hosts, libraries)
SERVICES: list[tuple[str, str, list[str], list[str]]] = [
    ("svc-github", "GitHub", ["api.github.com", "raw.githubusercontent.com", "gist.githubusercontent.com"], []),
    ("svc-bluesky", "Bluesky", ["public.api.bsky.app", "bsky.social", "bsky.network"], []),
    ("svc-anthropic", "Anthropic", ["api.anthropic.com"], []),
    ("svc-openai", "OpenAI", ["api.openai.com"], []),
    ("svc-gemini", "Gemini", ["generativelanguage.googleapis.com"], ["@google/generative-ai", "@google/genai"]),
    ("svc-hacker-news", "Hacker News", ["hn.algolia.com", "hacker-news.firebaseio.com"], []),
    ("svc-jina", "Jina", ["jina.ai"], []),
    ("svc-wikipedia", "Wikipedia", ["wikipedia.org"], []),
    ("svc-pypi", "PyPI", ["pypi.org"], []),
    ("svc-census-reporter", "Census Reporter", ["api.censusreporter.org"], []),
    ("svc-datasette", "Datasette", ["datasette.simonwillison.net", "latest.datasette.io"], []),
    ("svc-inaturalist", "iNaturalist", ["api.inaturalist.org"], []),
    ("svc-openstreetmap", "OpenStreetMap", ["nominatim.openstreetmap.org", "tiles.openfreemap.org"], []),
    ("svc-mdn", "MDN", ["bcd.developer.mozilla.org"], []),
    ("svc-bugzilla", "Bugzilla", ["bugzilla.mozilla.org"], []),
    ("svc-hugging-face", "Hugging Face", ["huggingface.co"], []),
    ("svc-osv", "OSV", ["api.osv.dev"], []),
    ("svc-software-heritage", "Software Heritage", ["archive.softwareheritage.org"], []),
    ("svc-arcgis", "ArcGIS", ["services.arcgis.com"], []),
]
_URL_HOST_RE = re.compile(r"^(?:https?|wss?)://([A-Za-z0-9.-]+)", re.IGNORECASE)
_BARE_HOST_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def _host_from_string(value: str) -> str | None:
    """Host of a URL string, or the string itself if it is a bare hostname."""
    match = _URL_HOST_RE.match(value)
    if match:
        return match.group(1).lower()
    if _BARE_HOST_RE.match(value):
        return value
    return None


def _library_tag(name: str) -> str:
    return "lib-" + re.sub(r"[^a-z0-9]+", "-", name).strip("-")


class Facts:
    """Everything the walker observed in one page's JavaScript."""

    def __init__(self) -> None:
        self.identifiers: set[str] = set()  # bare identifier references
        self.window_globals: set[str] = set()  # window.X / globalThis.X
        self.raw_chains: list[tuple[str, ...]] = []  # every a.b.c member chain
        self.chains: set[tuple[str, ...]] = set()  # chains rooted at a real global
        self.props: set[str] = set()
        self.string_calls: set[tuple[str, str]] = set()
        self.events: set[str] = set()
        self.flags: set[str] = set()
        self.libraries: set[str] = set()  # script, import and CDN string URLs
        self.hosts: set[str] = set()  # hosts of URL strings in the JavaScript
        self.declared: set[str] = set()  # names bound by the page's own code

    def matches(self, matcher: str) -> bool:
        kind, _, value = matcher.partition(":")
        if kind == "g":
            if value in self.window_globals:
                return True
            return value in self.identifiers and value not in self.declared
        if kind == "m":
            return tuple(value.split(".")) in self.chains
        if kind == "p":
            return value in self.props
        if kind == "s":
            method, _, arg = value.partition(":")
            return (method, arg) in self.string_calls
        if kind == "e":
            return value in self.events
        if kind == "x":
            return value in self.flags
        if kind == "l":
            return any(value in url for url in self.libraries)
        raise ValueError(f"Unknown matcher {matcher!r}")


def _text(node) -> str:
    return node.text.decode("utf-8", "replace")


def _walk(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)


def _member_chain(node) -> list[str] | None:
    """['navigator', 'clipboard', 'writeText'] for navigator.clipboard.writeText."""
    parts: list[str] = []
    while node.type == "member_expression":
        prop = node.child_by_field_name("property")
        if prop is None or prop.type != "property_identifier":
            return None
        parts.append(_text(prop))
        node = node.child_by_field_name("object")
        if node is None:
            return None
    if node.type != "identifier":
        return None
    parts.append(_text(node))
    return parts[::-1]


def _string_value(node) -> str | None:
    if node is not None and node.type == "string":
        return "".join(
            _text(child) for child in node.children if child.type == "string_fragment"
        )
    return None


def _declared_names(node):
    """Names bound by a declaration node, ignoring destructuring patterns."""
    if node.type in ("variable_declarator", "function_declaration", "class_declaration"):
        name = node.child_by_field_name("name")
        if name is not None and name.type == "identifier":
            yield _text(name)
    elif node.type == "formal_parameters":
        for child in node.children:
            if child.type == "identifier":
                yield _text(child)
            elif child.type == "assignment_pattern":
                left = child.child_by_field_name("left")
                if left is not None and left.type == "identifier":
                    yield _text(left)
    elif node.type == "arrow_function":
        param = node.child_by_field_name("parameter")
        if param is not None:
            yield _text(param)


def analyze_javascript(source: str, facts: Facts) -> None:
    tree = JS_PARSER.parse(source.encode("utf-8"))
    for node in _walk(tree.root_node):
        node_type = node.type
        if node_type == "identifier":
            facts.identifiers.add(_text(node))
        elif node_type == "member_expression":
            prop = node.child_by_field_name("property")
            if prop is not None and prop.type == "property_identifier":
                name = _text(prop)
                facts.props.add(name)
                if name.startswith("on") and name.islower():
                    facts.events.add(name[2:])
            chain = _member_chain(node)
            if chain:
                if chain[0] in GLOBAL_OBJECTS:
                    chain = chain[1:]
                    if len(chain) == 1:
                        facts.window_globals.add(chain[0])
                        continue
                facts.raw_chains.append(tuple(chain))
        elif node_type == "call_expression":
            function = node.child_by_field_name("function")
            arguments = node.child_by_field_name("arguments")
            if function is None:
                continue
            if function.type == "import":
                facts.flags.add("dynamic-import")
                if arguments is not None and arguments.named_children:
                    url = _string_value(arguments.named_children[0])
                    if url:
                        facts.libraries.add(url)
            elif function.type == "member_expression" and arguments is not None:
                prop = function.child_by_field_name("property")
                first = arguments.named_children[0] if arguments.named_children else None
                value = _string_value(first)
                if prop is not None and value is not None:
                    method = _text(prop)
                    facts.string_calls.add((method, value))
                    if method == "addEventListener":
                        facts.events.add(value)
        elif node_type == "string":
            # CDN URLs passed to loadPyodide(), importScripts(), script.src = ...
            value = _string_value(node)
            if value and library_from_url(value):
                facts.libraries.add(value)
            host = _host_from_string(value) if value else None
            if host:
                facts.hosts.add(host)
        elif node_type == "template_string":
            # `https://api.example.com/items/${id}` - the part before any ${}
            host = _host_from_string(_text(node).strip("`").split("${")[0])
            if host:
                facts.hosts.add(host)
        elif node_type in ("import_statement", "export_statement"):
            facts.flags.add("module")
            url = _string_value(node.child_by_field_name("source"))
            if url:
                facts.libraries.add(url)
        facts.declared.update(_declared_names(node))


def _attributes(tag_node) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for child in tag_node.children:
        if child.type != "attribute":
            continue
        name = value = ""
        for part in child.children:
            if part.type == "attribute_name":
                name = _text(part).lower()
            elif part.type == "attribute_value":
                value = _text(part)
            elif part.type == "quoted_attribute_value":
                value = "".join(
                    _text(v) for v in part.children if v.type == "attribute_value"
                )
        attrs[name] = html.unescape(value)
    return attrs


def analyze_html(source: str) -> Facts:
    facts = Facts()
    tree = HTML_PARSER.parse(source.encode("utf-8"))
    for node in _walk(tree.root_node):
        if node.type == "script_element":
            attrs: dict[str, str] = {}
            code = ""
            for child in node.children:
                if child.type == "start_tag":
                    attrs = _attributes(child)
                elif child.type == "raw_text":
                    code = _text(child)
            script_type = attrs.get("type", "").strip().lower()
            if attrs.get("src"):
                facts.libraries.add(attrs["src"])
            if script_type == "importmap":
                try:
                    imports = json.loads(code).get("imports", {})
                except (ValueError, AttributeError):
                    imports = {}
                facts.libraries.update(v for v in imports.values() if isinstance(v, str))
            if script_type not in JS_SCRIPT_TYPES:
                continue
            if script_type == "module":
                facts.flags.add("module")
            if code.strip():
                analyze_javascript(code, facts)
        elif node.type in ("start_tag", "self_closing_tag"):
            for name, value in _attributes(node).items():
                if name.startswith("on") and len(name) > 2:
                    facts.events.add(name[2:])
                    if value.strip():
                        analyze_javascript(value, facts)
    # A chain like history.pushState only counts if `history` is the browser
    # global, not a variable the page declared itself.
    for chain in facts.raw_chains:
        if chain[0] not in facts.declared:
            facts.chains.add(chain)
    return facts


def tags_for_html(source: str) -> tuple[list[str], list[str], list[str]]:
    """Returns (browser API tags, CDN-loaded library names, web API tags)."""
    facts = analyze_html(source)
    api_tags = [
        tag for tag, _label, matchers in RULES if any(facts.matches(m) for m in matchers)
    ]
    libraries = sorted({name for url in facts.libraries if (name := library_from_url(url))})
    service_tags = [
        tag
        for tag, _label, hosts, service_libraries in SERVICES
        if any(lib in libraries for lib in service_libraries)
        or any(h == host or h.endswith("." + host) for h in facts.hosts for host in hosts)
    ]
    return api_tags, libraries, service_tags


def build_tags() -> None:
    if not GATHERED_LINKS_PATH.exists():
        sys.exit("gathered_links.json not found - run gather_links.py first")
    pages = json.loads(GATHERED_LINKS_PATH.read_text("utf-8")).get("pages", {})

    tools: dict[str, dict] = {}
    libraries_by_tool: dict[str, list[str]] = {}
    tagged: dict[str, list[str]] = {}

    for filename, page in sorted(pages.items()):
        path = Path(filename)
        commits = page.get("commits", [])
        if not commits or not path.exists():
            continue
        created_date = _parse_iso_datetime(commits[-1].get("date"))
        if created_date is None:
            continue
        slug = path.stem
        if slug == "index":
            continue
        api_tags, libraries, service_tags = tags_for_html(
            path.read_text("utf-8", errors="replace")
        )
        summary, truncated = _extract_summary(Path(f"{slug}.docs.md"))
        tools[slug] = {
            "filename": filename,
            "url": f"/{slug}",
            "colophon": f"/colophon#{filename}",
            "created": created_date.isoformat(),
            "created_dt": created_date,
            "summary": summary,
            "truncated": truncated,
            "tags": api_tags + service_tags,
        }
        libraries_by_tool[slug] = libraries
        for tag in api_tags + service_tags:
            tagged.setdefault(tag, []).append(slug)

    # Libraries only become tags once enough tools use them
    library_tools: dict[str, list[str]] = {}
    for slug, libraries in libraries_by_tool.items():
        for name in libraries:
            library_tools.setdefault(name, []).append(slug)
    library_rules = []
    for name, slugs in sorted(library_tools.items()):
        if len(slugs) < LIBRARY_MIN_TOOLS:
            continue
        tag = _library_tag(name)
        library_rules.append((tag, LIBRARY_LABELS.get(name, name)))
        tagged[tag] = slugs
        for slug in slugs:
            tools[slug]["tags"].append(tag)

    def tag_entry(tag: str, label: str, kind: str) -> dict:
        return {
            "tag": tag,
            "label": label,
            "kind": kind,
            "count": len(tagged[tag]),
            # Most recently created first
            "tools": sorted(
                tagged[tag], key=lambda s: tools[s]["created_dt"], reverse=True
            ),
        }

    tag_entries = (
        [tag_entry(tag, label, "library") for tag, label in library_rules]
        + [
            tag_entry(tag, label, "browser-api")
            for tag, label, _ in RULES
            if tagged.get(tag)
        ]
        + [
            tag_entry(tag, label, "web-api")
            for tag, label, _, _ in SERVICES
            if tagged.get(tag)
        ]
    )
    # Leave out tools that ended up with no tags at all
    tools = {slug: tool for slug, tool in tools.items() if tool["tags"]}
    for tool in tools.values():
        del tool["created_dt"]

    output = {"tags": tag_entries, "tools": tools}
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), "utf-8")
    print(
        f"tags.json created successfully ({len(tag_entries)} tags "
        f"across {len(tools)} tools)"
    )


if __name__ == "__main__":
    build_tags()
