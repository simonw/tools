"""Playwright tests for social-media-cropper.html."""

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
    page.goto(f"http://127.0.0.1:{port}/social-media-cropper.html")
    page.locator("#fileInput").set_input_files(str(TEST_IMAGE))
    expect(page.locator("#previewContainer")).to_be_visible()


def download_bytes(page):
    return bytes(
        page.evaluate(
            """() => fetch(document.getElementById("downloadBtn").href)
      .then((r) => r.arrayBuffer())
      .then((buf) => Array.from(new Uint8Array(buf.slice(0, 12))))"""
        )
    )


def test_defaults_to_jpeg_download(page: Page, unused_port_server):
    unused_port_server.start(root)
    load_page_with_image(page, unused_port_server.port)

    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (JPEG")
    assert download.get_attribute("download") == "social-card-2.jpg"
    assert download.get_attribute("href").startswith("blob:")
    assert download_bytes(page)[:3] == b"\xff\xd8\xff"


def test_webp_download_uses_native_encoder_when_available(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page)
    load_page_with_image(page, unused_port_server.port)
    assert page.locator("#webpNote").is_hidden()

    page.locator('input[name="outputFormat"][value="webp"]').check()
    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (WebP")
    assert download.get_attribute("download") == "social-card-2.webp"

    data = download_bytes(page)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"

    page.wait_for_timeout(200)
    assert jsquash_requests == []


def test_webp_download_falls_back_to_jsquash_without_native_support(
    page: Page, unused_port_server
):
    """Loads @jsquash/webp from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page)
    page.add_init_script(SAFARI_NO_WEBP_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)

    # The JPEG default must not trigger the encoder download.
    expect(page.locator("#downloadBtn")).to_contain_text("Download Social Media Card (JPEG")
    expect(page.locator("#webpNote")).to_be_visible()
    assert jsquash_requests == []

    with page.expect_request("**/@jsquash/webp@*/encode.js/+esm"):
        page.locator('input[name="outputFormat"][value="webp"]').check()

    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (WebP", timeout=60_000)
    assert download.get_attribute("download") == "social-card-2.webp"

    data = download_bytes(page)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"
