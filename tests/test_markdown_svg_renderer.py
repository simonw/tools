"""Playwright tests for markdown-svg-renderer.html."""

import pathlib

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_svg_is_rendered_raw_in_a_network_isolated_iframe(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    leaked_urls = []

    def record_leak(route):
        leaked_urls.append(route.request.url)
        route.abort()

    page.route("**/svg-leak-probe-*", record_leak)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )

    svg = """<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg">
  <style>.wheel { fill: #22c55e; }</style>
  <defs><circle id="wheel" class="wheel" r="20"/></defs>
  <use href="#wheel" x="30" y="40"/>
  <use href="#wheel" x="90" y="40"/>
  <script>
    document.documentElement.setAttribute("data-script-ran", "yes");
    fetch("http://127.0.0.1:%s/svg-leak-probe-script");
  </script>
  <image href="http://127.0.0.1:%s/svg-leak-probe-image"/>
  <foreignObject width="10" height="10">
    <iframe xmlns="http://www.w3.org/1999/xhtml"
      src="http://127.0.0.1:%s/svg-leak-probe-frame"></iframe>
  </foreignObject>
</svg>""" % ((unused_port_server.port,) * 3)

    page.locator("#input").fill(f"```svg\n{svg}\n```")
    block = page.locator("svg-block")
    expect(block).to_be_visible()

    # The SVG is not passed through an allowlist, so valid SVG features such
    # as style and use survive intact.
    assert block.get_attribute("data-svg") == svg + "\n"

    iframe_locator = page.locator("svg-block iframe")
    assert iframe_locator.get_attribute("sandbox") == ""
    csp = iframe_locator.get_attribute("csp")
    assert csp is not None
    assert "default-src 'none'" in csp
    assert "script-src 'none'" in csp
    assert "style-src 'unsafe-inline'" in csp
    assert "img-src data: blob:" in csp

    srcdoc = iframe_locator.get_attribute("srcdoc")
    assert srcdoc is not None
    assert srcdoc.startswith(
        '<!doctype html>\n<meta http-equiv="Content-Security-Policy"'
    )

    iframe_element = iframe_locator.element_handle()
    assert iframe_element is not None
    iframe = iframe_element.content_frame()
    assert iframe is not None
    expect(iframe.locator("use")).to_have_count(2)
    expect(iframe.locator("circle")).to_have_css("fill", "rgb(34, 197, 94)")

    page.wait_for_timeout(500)
    assert iframe.locator("svg").get_attribute("data-script-ran") is None
    assert leaked_urls == []


ANIMATED_SMIL_SVG = """<svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="50" height="100" fill="#dc2626">
    <animate attributeName="x" from="0" to="150" dur="2s" repeatCount="indefinite"/>
  </rect>
</svg>"""

ANIMATED_CSS_SVG = """<svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
  <style>
    rect { animation: slide 3s linear infinite; }
    @keyframes slide {
      from { transform: translateX(0); }
      to { transform: translateX(150px); }
    }
  </style>
  <rect x="0" y="0" width="50" height="100" fill="#2563eb"/>
</svg>"""

STATIC_SVG = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" fill="#22c55e"/>
</svg>"""


def fill_svg_block(page, svg):
    page.locator("#input").fill(f"```svg\n{svg}\n```")
    expect(page.locator("svg-block")).to_be_visible()
    return page.locator("svg-block")


def test_details_toggle_with_markdown_and_svg(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    page.locator("#input").fill(f"""## Reasoning

<details><summary>Reasoning</summary>

Some **formatted** text.

1. First step
2. Second step

```svg
{STATIC_SVG}
```

</details>

## Response

Outside the disclosure.
""")
    details = page.locator("#output details")
    expect(details).to_have_count(1)
    expect(details.locator("summary")).to_have_text("Reasoning")
    expect(details.locator("strong")).to_be_hidden()
    expect(page.get_by_text("Outside the disclosure.", exact=True)).to_be_visible()

    details.locator("summary").click()
    expect(details).to_have_attribute("open", "")
    expect(details.locator("strong")).to_be_visible()
    expect(details.locator("li")).to_have_text(["First step", "Second step"])
    expect(details.locator("svg-block iframe")).to_be_visible()
    assert details.locator("svg-block").get_attribute("data-svg") == STATIC_SVG + "\n"

    details.locator("summary").press("Enter")
    expect(details.locator("strong")).to_be_hidden()
    expect(details.locator("svg-block iframe")).to_be_hidden()


def test_details_open_nested_and_literal_code(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    literal = "<details><summary>Example</summary></details>"
    page.locator("#input").fill(f"""<details open><summary>Outer</summary>

Outer content.

<details><summary>Inner</summary>

Inner content.

</details>

</details>

`{literal}`

```text
{literal}
```
""")
    outer = page.locator("#output > details")
    inner = outer.locator("details")
    expect(page.locator("#output details")).to_have_count(2)
    expect(outer).to_have_attribute("open", "")
    expect(outer.locator("p").first).to_be_visible()
    expect(inner.locator("p")).to_be_hidden()
    inner.locator("summary").click()
    expect(inner.locator("p")).to_be_visible()
    expect(page.locator("#output > p > code")).to_have_text(literal)
    expect(page.locator("#output pre code")).to_have_text(literal + "\n")


def test_static_svg_has_no_mp4_tab(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, STATIC_SVG)
    expect(block.locator('button[data-tab="png"]')).to_be_visible()
    assert block.locator('button[data-tab="mp4"]').count() == 0


def test_smil_animation_gets_mp4_tab_with_detected_duration(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    ffmpeg_requests = []
    page.on(
        "request",
        lambda request: "/@ffmpeg/" in request.url
        and ffmpeg_requests.append(request.url),
    )
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, ANIMATED_SMIL_SVG)

    # ffmpeg.wasm is heavy (~31 MB) so it must not load until the MP4 tab is
    # first selected.
    page.wait_for_timeout(200)
    assert ffmpeg_requests == []

    with page.expect_request("**/@ffmpeg/core**"):
        block.locator('button[data-tab="mp4"]').click()
    panel = block.locator('.panel[data-panel="mp4"]')
    expect(panel.locator("input")).to_have_value("2")
    expect(panel.locator(".mp4-generate")).to_be_visible()


def test_css_animation_gets_mp4_tab_with_detected_duration(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, ANIMATED_CSS_SVG)
    block.locator('button[data-tab="mp4"]').click()
    expect(block.locator('.panel[data-panel="mp4"] input')).to_have_value("3")


def test_generate_mp4(page: Page, unused_port_server):
    """Full pipeline: captures frames, loads ffmpeg.wasm from jsdelivr
    (~31 MB, so this test needs network access) and encodes an H.264 MP4."""
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, ANIMATED_SMIL_SVG)
    block.locator('button[data-tab="mp4"]').click()
    panel = block.locator('.panel[data-panel="mp4"]')
    panel.locator("input").fill("0.3")
    panel.locator(".mp4-generate").click()

    download_button = panel.locator(".image-actions button")
    expect(download_button).to_be_visible(timeout=180_000)
    assert "Download MP4 (" in download_button.text_content()

    # Fetch the generated bytes from the video blob URL and sanity-check the
    # MP4 container: ftyp header, and faststart (moov before mdat).
    head = page.evaluate(
        """() => {
      const video = document.querySelector("svg-block").shadowRoot
        .querySelector("video");
      return fetch(video.src)
        .then((r) => r.arrayBuffer())
        .then((buf) => Array.from(new Uint8Array(buf.slice(0, 4096))));
    }"""
    )
    data = bytes(head)
    assert data[4:8] == b"ftyp"
    assert b"moov" in data
    assert b"avc1" in data


def test_html_block_rendered_in_sandboxed_iframe_with_csp(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    leaked_urls = []

    def record_leak(route):
        leaked_urls.append(route.request.url)
        route.abort()

    page.route("**/html-leak-probe-*", record_leak)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )

    html = """<div id="greeting">Hello HTML</div>
<script>
  document.getElementById("greeting").setAttribute("data-script-ran", "yes");
  fetch("http://127.0.0.1:%s/html-leak-probe-script");
</script>
<img src="http://127.0.0.1:%s/html-leak-probe-image"/>
<iframe src="http://127.0.0.1:%s/html-leak-probe-frame"></iframe>""" % ((unused_port_server.port,) * 3)

    page.locator("#input").fill(f"```html\n{html}\n```")
    block = page.locator("html-block")
    expect(block).to_be_visible()

    assert block.get_attribute("data-html") == html + "\n"

    iframe_locator = page.locator("html-block iframe")
    assert iframe_locator.get_attribute("sandbox") == "allow-scripts"

    csp = iframe_locator.get_attribute("csp")
    assert csp is not None
    assert "default-src 'none'" in csp
    assert "cdnjs.cloudflare.com" in csp
    assert "cdn.jsdelivr.net" in csp
    assert "unpkg.com" in csp
    assert "esm.sh" in csp

    srcdoc = iframe_locator.get_attribute("srcdoc")
    assert srcdoc is not None
    assert srcdoc.startswith(
        '<!doctype html>\n<meta http-equiv="Content-Security-Policy"'
    )
    assert "cdnjs.cloudflare.com" in srcdoc
    assert "cdn.jsdelivr.net" in srcdoc
    assert "unpkg.com" in srcdoc
    assert "esm.sh" in srcdoc

    iframe_element = iframe_locator.element_handle()
    assert iframe_element is not None
    iframe = iframe_element.content_frame()
    assert iframe is not None

    expect(iframe.locator("#greeting")).to_have_text("Hello HTML")
    expect(iframe.locator("#greeting")).to_have_attribute("data-script-ran", "yes")

    page.wait_for_timeout(500)
    assert leaked_urls == []

    # Verify tabs
    code_button = block.locator('button[data-tab="code"]')
    expect(code_button).to_be_visible()
    code_button.click()
    expect(block.locator('.panel[data-panel="code"] pre')).to_have_text(html + "\n")

    # Verify copy button in code tab
    copy_button = block.locator('.panel[data-panel="code"] .copy-btn')
    expect(copy_button).to_be_visible()
    expect(copy_button.locator('svg.copy-icon')).to_be_visible()
    copy_button.click()
    expect(copy_button).to_have_text("Copied!")
    expect(copy_button.locator('svg.check-icon')).to_be_visible()


def test_svg_code_tab_has_copy_button(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, STATIC_SVG)
    code_button = block.locator('button[data-tab="code"]')
    code_button.click()
    expect(block.locator('.panel[data-panel="code"] pre')).to_have_text(STATIC_SVG + "\n")

    copy_button = block.locator('.panel[data-panel="code"] .copy-btn')
    expect(copy_button).to_be_visible()
    expect(copy_button.locator('svg.copy-icon')).to_be_visible()
    copy_button.click()
    expect(copy_button).to_have_text("Copied!")
    expect(copy_button.locator('svg.check-icon')).to_be_visible()

