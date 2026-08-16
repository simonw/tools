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
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )
    block = fill_svg_block(page, ANIMATED_SMIL_SVG)
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

