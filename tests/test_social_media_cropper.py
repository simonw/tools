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


# Most browsers cannot encode AVIF from a canvas either. Force that, so the
# @jsquash/avif fallback runs even if Chromium gains a native encoder.
NO_NATIVE_AVIF_INIT_SCRIPT = """
(() => {
  const original = HTMLCanvasElement.prototype.toBlob;
  HTMLCanvasElement.prototype.toBlob = function (callback, type, quality) {
    if (type === "image/avif") type = "image/png";
    return original.call(this, callback, type, quality);
  };
})();
"""

# Emulate a browser that can encode AVIF natively by relabelling the JPEG
# Chromium produces at the requested quality, to check the wasm encoder is
# then never fetched.
NATIVE_AVIF_INIT_SCRIPT = """
(() => {
  const original = HTMLCanvasElement.prototype.toBlob;
  HTMLCanvasElement.prototype.toBlob = function (callback, type, quality) {
    if (type !== "image/avif") return original.call(this, callback, type, quality);
    return original.call(
      this,
      (blob) => callback(blob && new Blob([blob], { type: "image/avif" })),
      "image/jpeg",
      quality
    );
  };
})();
"""

# Emulate a browser whose native AVIF encoder ignores the quality argument,
# by relabelling a PNG: every quality level comes out the same size.
NATIVE_AVIF_IGNORING_QUALITY_INIT_SCRIPT = """
(() => {
  const original = HTMLCanvasElement.prototype.toBlob;
  HTMLCanvasElement.prototype.toBlob = function (callback, type, quality) {
    if (type !== "image/avif") return original.call(this, callback, type, quality);
    return original.call(
      this,
      (blob) => callback(blob && new Blob([blob], { type: "image/avif" })),
      "image/png"
    );
  };
})();
"""


def track_jsquash_requests(page, codec="webp"):
    requests = []
    page.on(
        "request",
        lambda request: f"/@jsquash/{codec}" in request.url
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


def download_size_kb(page):
    return page.evaluate(
        """() => fetch(document.getElementById("downloadBtn").href)
      .then((r) => r.arrayBuffer()).then((buf) => buf.byteLength)"""
    )


def test_quality_input_updates_preview_live(page: Page, unused_port_server):
    unused_port_server.start(root)
    load_page_with_image(page, unused_port_server.port)
    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("(JPEG q90,")
    high_quality_size = download_size_kb(page)
    high_quality_preview = page.locator("#preview").get_attribute("src")

    # Typing into the box (input event, no blur) re-renders immediately.
    quality = page.locator("#quality")
    quality.fill("10")
    expect(download).to_contain_text("(JPEG q10,")
    low_quality_size = download_size_kb(page)
    assert low_quality_size < high_quality_size
    assert page.locator("#preview").get_attribute("src") != high_quality_preview

    # Quality also applies to WebP.
    page.locator('input[name="outputFormat"][value="webp"]').check()
    expect(download).to_contain_text("(WebP q10,")
    webp_low = download_size_kb(page)
    quality.fill("95")
    expect(download).to_contain_text("(WebP q95,")
    assert download_size_kb(page) > webp_low

    # Out-of-range values are clamped when editing finishes.
    quality.fill("250")
    quality.dispatch_event("change")
    expect(quality).to_have_value("100")
    expect(download).to_contain_text("(WebP q100,")


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


def test_avif_download_skips_jsquash_when_browser_encodes_avif(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page, "avif")
    page.add_init_script(NATIVE_AVIF_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)
    assert page.locator("#avifNote").is_hidden()

    page.locator('input[name="outputFormat"][value="avif"]').check()
    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (AVIF q90,")
    assert download.get_attribute("download") == "social-card-2.avif"

    page.wait_for_timeout(200)
    assert jsquash_requests == []


def test_avif_download_falls_back_to_jsquash_without_native_support(
    page: Page, unused_port_server
):
    """Loads @jsquash/avif from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page, "avif")
    page.add_init_script(NO_NATIVE_AVIF_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)

    # The JPEG default must not trigger the encoder download.
    expect(page.locator("#downloadBtn")).to_contain_text("Download Social Media Card (JPEG")
    expect(page.locator("#avifNote")).to_be_visible()
    assert jsquash_requests == []

    with page.expect_request("**/@jsquash/avif@*/encode.js/+esm"):
        page.locator('input[name="outputFormat"][value="avif"]').check()

    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (AVIF q90,", timeout=60_000)
    assert download.get_attribute("download") == "social-card-2.avif"
    data = download_bytes(page)
    assert data[4:8] == b"ftyp"
    assert data[8:12] == b"avif"
    high_quality_size = download_size_kb(page)

    # Quality applies to AVIF too.
    page.locator("#quality").fill("10")
    expect(download).to_contain_text("Download Social Media Card (AVIF q10,", timeout=60_000)
    assert download_size_kb(page) < high_quality_size


def test_avif_download_falls_back_to_jsquash_when_native_encoder_ignores_quality(
    page: Page, unused_port_server
):
    """Loads @jsquash/avif from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    page.add_init_script(NATIVE_AVIF_IGNORING_QUALITY_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)
    expect(page.locator("#avifNote")).to_be_visible()

    with page.expect_request("**/@jsquash/avif@*/encode.js/+esm"):
        page.locator('input[name="outputFormat"][value="avif"]').check()

    download = page.locator("#downloadBtn")
    expect(download).to_contain_text("Download Social Media Card (AVIF q90,", timeout=60_000)
    data = download_bytes(page)
    assert data[4:8] == b"ftyp"
    assert data[8:12] == b"avif"
