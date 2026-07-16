"""
Playwright tests for mermaid-ascii.html

Tests Mermaid-to-ASCII-art rendering via the mermaid-ascii.wasm WebAssembly
module (the Go library AlexanderGrooff/mermaid-ascii compiled with
GOOS=js GOARCH=wasm — see mermaid-ascii/).
"""

import pathlib
from urllib.parse import quote

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_initial_render(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    expect(page.locator("h1")).to_have_text("Mermaid to ASCII art")
    # Default example is the flowchart; wait for the wasm render.
    expect(page.locator("#output")).to_contain_text("Check auth")
    expect(page.locator("#output")).to_contain_text("▼")


def test_example_buttons(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    page.locator("#examples button", has_text="Sequence").first.click()
    expect(page.locator("#output")).to_contain_text("renderMermaidAscii()")
    page.locator("#examples button", has_text="Alt fragment").click()
    expect(page.locator("#output")).to_contain_text("[alt valid credentials]")
    page.locator("#examples button", has_text="Parallel").click()
    expect(page.locator("#output")).to_contain_text("GET /users")


def test_colored_classes(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    page.locator("#examples button", has_text="Colors").click()
    expect(page.locator("#output")).to_contain_text("Rollback")
    # classDef colors arrive as sanitized spans with inline color styles.
    assert page.locator("#output span[style*='color']").count() > 0


def test_live_editing(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    expect(page.locator("#output")).to_contain_text("Check auth")
    page.locator("#input").fill("graph LR\nA[Hello] --> B[World]")
    expect(page.locator("#output")).to_contain_text("Hello")
    expect(page.locator("#output")).to_contain_text("World")
    expect(page.locator("#output")).to_contain_text("─")


def test_ascii_only_mode(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    page.locator("#input").fill("graph LR\nA --> B")
    expect(page.locator("#output")).to_contain_text("─")
    page.locator("#ascii").check()
    expect(page.locator("#output")).to_contain_text("+---+")


def test_parse_error_shown(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    page.locator("#input").fill("this is not mermaid")
    expect(page.locator("#output .err")).to_contain_text("Error:")


def test_markup_in_labels_not_injected(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html")
    page.locator("#input").fill('graph LR\nA[<img src=x onerror=alert(1)>] --> B')
    # The markup must be rendered as literal text, not become an element.
    expect(page.locator("#output")).to_contain_text("<img src=x onerror=alert(1)>")
    assert page.locator("#output img").count() == 0


def test_source_in_url_fragment(page: Page, unused_port_server):
    unused_port_server.start(root)
    src = "graph TD\nX[From the URL] --> Y[Rendered]"
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/mermaid-ascii.html#{quote(src)}"
    )
    expect(page.locator("#output")).to_contain_text("From the URL")
