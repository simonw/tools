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

# Mobile Safari encodes AVIF natively but ignores the quality argument.
# Emulate that by relabelling a PNG: every quality level is the same size.
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


def assert_all_avif(page, expected_count):
    outputs = output_image_bytes(page)
    assert len(outputs) == expected_count
    for data in outputs:
        assert data[4:8] == b"ftyp"
        assert data[8:12] == b"avif"


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


def test_avif_previews_skip_jsquash_when_browser_encodes_avif(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page, "avif")
    page.add_init_script(NATIVE_AVIF_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)

    avif_tab = page.locator("#format-tab-avif")
    assert avif_tab.get_attribute("title") is None
    avif_tab.click()
    expect(page.locator("#output .image-container a")).to_have_count(10)
    expect(page.locator("#output .image-info").first).to_contain_text("Format: AVIF")
    downloads = page.locator("#output .image-container a")
    assert downloads.first.get_attribute("download").endswith(".avif")

    page.wait_for_timeout(200)
    assert jsquash_requests == []


def test_avif_previews_fall_back_to_jsquash_without_native_support(
    page: Page, unused_port_server
):
    """Loads @jsquash/avif from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    jsquash_requests = track_jsquash_requests(page, "avif")
    page.add_init_script(NO_NATIVE_AVIF_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)

    # The AVIF tab is offered, and the encoder is not fetched until it is
    # actually used.
    avif_tab = page.locator("#format-tab-avif")
    expect(avif_tab).to_be_visible()
    assert "@jsquash/avif" in (avif_tab.get_attribute("title") or "")
    assert jsquash_requests == []

    with page.expect_request("**/@jsquash/avif@*/encode.js/+esm"):
        avif_tab.click()

    expect(page.locator("#output .image-container a")).to_have_count(
        10, timeout=90_000
    )
    expect(page.locator("#output .image-info").first).to_contain_text("Format: AVIF")
    downloads = page.locator("#output .image-container a")
    assert downloads.first.get_attribute("download").endswith(".avif")
    assert_all_avif(page, 10)


def test_avif_fallback_skips_encodes_made_stale_by_a_new_crop(
    page: Page, unused_port_server
):
    """Loads @jsquash/avif from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    page.add_init_script(NO_NATIVE_AVIF_INIT_SCRIPT)
    # Count the pixel reads that start each wasm AVIF encode.
    page.add_init_script(
        """
(() => {
  window.__imageDataReads = 0;
  const original = CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.getImageData = function (...args) {
    window.__imageDataReads++;
    return original.apply(this, args);
  };
})();
"""
    )
    load_page_with_image(page, unused_port_server.port)
    page.locator("#format-tab-avif").click()

    # Drag the right edge of the crop box in several steps, each of which
    # re-renders all ten previews.
    bar = page.locator(".crop-bar.right").bounding_box()
    x = bar["x"] + bar["width"] / 2
    y = bar["y"] + bar["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, 6):
        page.mouse.move(x - step * 20, y)
    page.mouse.up()

    expect(page.locator("#output .image-container a")).to_have_count(
        10, timeout=90_000
    )
    assert_all_avif(page, 10)
    # Six renders of ten previews were requested. Encoding all of them would
    # read pixels 60 times, on top of one transparency check per crop. Only
    # the last render's encodes (plus any already in flight) should run.
    reads = page.evaluate("window.__imageDataReads")
    page.wait_for_timeout(500)
    assert page.evaluate("window.__imageDataReads") == reads
    assert reads < 30


def test_avif_falls_back_to_jsquash_when_native_encoder_ignores_quality(
    page: Page, unused_port_server
):
    """Loads @jsquash/avif from jsdelivr, so this test needs network access."""
    unused_port_server.start(root)
    page.add_init_script(NATIVE_AVIF_IGNORING_QUALITY_INIT_SCRIPT)
    load_page_with_image(page, unused_port_server.port)
    avif_tab = page.locator("#format-tab-avif")
    assert "@jsquash/avif" in (avif_tab.get_attribute("title") or "")

    with page.expect_request("**/@jsquash/avif@*/encode.js/+esm"):
        avif_tab.click()

    expect(page.locator("#output .image-container a")).to_have_count(
        10, timeout=90_000
    )
    assert_all_avif(page, 10)
    # Each of the five quality levels at full width is a different size.
    sizes = [
        line
        for info in page.locator("#output .image-info").all_inner_texts()[:5]
        for line in info.splitlines()
        if line.startswith("Size:")
    ]
    assert len(set(sizes)) == 5, sizes
