"""Playwright tests for image-resize-quality.html."""

import pathlib

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()
TEST_IMAGE = test_dir / "ocr-test-text.png"

# Safari (desktop and iOS) cannot encode WebP from a canvas: toBlob silently
# hands back a PNG instead. Emulate that so the @jsquash/webp fallback path
# runs in Chromium.
SAFARI_NO_WEBP_INIT_SCRIPT = """
(() => {
  const original = HTMLCanvasElement.prototype.toBlob;
  HTMLCanvasElement.prototype.toBlob = function (callback, type, quality) {
    if (type === "image/webp") type = "image/png";
    return original.call(this, callback, type, quality);
  };
})();
"""


def track_jsquash_requests(page):
    requests = []
    page.on(
        "request",
        lambda request: "/@jsquash/webp" in request.url
        and requests.append(request.url),
    )
    return requests


def load_page_with_image(page, port):
    page.goto(f"http://127.0.0.1:{port}/image-resize-quality.html")
    expect(page.locator("#format-tab-webp")).to_be_visible()
    page.locator("#file-input").set_input_files(str(TEST_IMAGE))
    expect(page.locator("#output .image-container").first).to_be_visible()


def output_image_bytes(page):
    """Fetch every rendered preview blob currently shown in #output."""
    return [
        bytes(item)
        for item in page.evaluate(
            """() => Promise.all(
      Array.from(document.querySelectorAll("#output .image-container img"))
        .map((img) => fetch(img.src)
          .then((r) => r.arrayBuffer())
          .then((buf) => Array.from(new Uint8Array(buf.slice(0, 12))))))"""
        )
    ]


def assert_all_webp(page, expected_count):
    outputs = output_image_bytes(page)
    assert len(outputs) == expected_count
    for data in outputs:
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WEBP"


def test_webp_previews_use_native_encoder_when_available(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page)
    load_page_with_image(page, unused_port_server.port)

    page.locator("#format-tab-webp").click()
    expect(page.locator("#format-tab-webp")).to_have_attribute("aria-selected", "true")
    # Two widths x five quality levels.
    expect(page.locator("#output .image-container a")).to_have_count(10)
    expect(page.locator("#output .image-info").first).to_contain_text("Format: WebP")

    assert_all_webp(page, 10)
    downloads = page.locator("#output .image-container a")
    assert downloads.first.get_attribute("download").endswith(".webp")

    page.wait_for_timeout(200)
    assert jsquash_requests == []


def test_webp_previews_fall_back_to_jsquash_without_native_support(
    page: Page, unused_port_server
):
    """Loads @jsquash/webp from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page)
    page.add_init_script(SAFARI_NO_WEBP_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)

    # The WebP tab is still offered, and the encoder is not fetched until it
    # is actually used.
    webp_tab = page.locator("#format-tab-webp")
    expect(webp_tab).to_be_visible()
    assert "jsquash" in (webp_tab.get_attribute("title") or "")
    assert jsquash_requests == []

    with page.expect_request("**/@jsquash/webp@*/encode.js/+esm"):
        webp_tab.click()

    expect(page.locator("#output .image-container a")).to_have_count(
        10, timeout=60_000
    )
    expect(page.locator("#output .image-info").first).to_contain_text("Format: WebP")
    assert_all_webp(page, 10)
