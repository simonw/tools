"""
Playwright tests for grok-mermaid.html

Tests Mermaid-to-Unicode-box-art rendering via the grok-mermaid.wasm
WebAssembly module (built from grok-mermaid/, extracted from
xai-org/grok-build).
"""

import pathlib
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_initial_render(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/grok-mermaid.html")
    expect(page.locator("h1")).to_have_text("Mermaid to Unicode box art")
    # Default example is the flowchart; wait for the wasm render.
    expect(page.locator("#output")).to_contain_text("Request received")
    expect(page.locator("#output")).to_contain_text("▼")
    # Colored spans from the wasm module's classed HTML output.
    assert page.locator("#output span.b").count() > 0


def test_example_buttons(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/grok-mermaid.html")
    page.locator("#examples button", has_text="Sequence").click()
    expect(page.locator("#output")).to_contain_text("wasm_render_html()")
    page.locator("#examples button", has_text="State").click()
    expect(page.locator("#output")).to_contain_text("Loading")
    # Unsupported diagram types fall back to a framed source listing.
    page.locator("#examples button", has_text="Unsupported").click()
    expect(page.locator("#output")).to_contain_text("mermaid: pie")


def test_live_editing(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/grok-mermaid.html")
    expect(page.locator("#output")).to_contain_text("Request received")
    page.locator("#input").fill("graph LR\n  A[Hello] --> B[World]")
    expect(page.locator("#output")).to_contain_text("Hello")
    expect(page.locator("#output")).to_contain_text("World")
    expect(page.locator("#output")).to_contain_text("─")


def test_source_in_url_fragment(page: Page, unused_port_server):
    unused_port_server.start(root)
    src = "graph TD\n  X[From the URL] --> Y[Rendered]"
    from urllib.parse import quote

    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/grok-mermaid.html#{quote(src)}"
    )
    expect(page.locator("#output")).to_contain_text("From the URL")
