"""
Playwright tests for video-compressor.html

The initial-state test runs offline. The full flow downloads the ~32 MB
ffmpeg.wasm core from jsDelivr, encodes a small fixture video into several
MP4 versions, and then checks the resulting files really are the kind of
MP4 the tool promises (H.264 Main profile, yuv420p, AAC, faststart).

Set FFMPEG_WASM_CACHE_DIR to a directory containing ffmpeg-core.js and
ffmpeg-core.wasm to serve the core from disk instead of the CDN.
"""

import base64
import os
import pathlib
import struct

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()
fixture = test_dir / "test-video.mp4"


def iter_boxes(data, start=0, end=None):
    """Yield (type, header_size, body_start, body_end) for MP4 boxes in data[start:end]."""
    end = len(data) if end is None else end
    pos = start
    while pos + 8 <= end:
        size, box_type = struct.unpack(">I4s", data[pos:pos + 8])
        header = 8
        if size == 1:
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header:
            break
        yield box_type, header, pos + header, pos + size
        pos += size


def find_box(data, path, start=0, end=None):
    """Find a nested box by path like [b"moov", b"trak"]; returns (body_start, body_end) or None."""
    # Sample description boxes carry extra header bytes before their children
    extra = {b"stsd": 8, b"avc1": 78, b"mp4a": 28}
    for box_type, header, body_start, body_end in iter_boxes(data, start, end):
        if box_type == path[0]:
            if len(path) == 1:
                return body_start, body_end
            skip = extra.get(box_type, 0)
            found = find_box(data, path[1:], body_start + skip, body_end)
            if found:
                return found
    return None


def describe_mp4(data):
    """Return a dict describing the container and codec layout of an MP4 file."""
    top_level = [box_type for box_type, _, _, _ in iter_boxes(data)]
    info = {"boxes": top_level}
    avcc = find_box(data, [b"moov", b"trak", b"mdia", b"minf", b"stbl", b"stsd", b"avc1", b"avcC"])
    if avcc:
        body = data[avcc[0]:avcc[1]]
        info["profile_idc"] = body[1]
        info["level_idc"] = body[3]
    info["has_mp4a"] = find_box(data, [b"moov", b"trak", b"mdia", b"minf", b"stbl", b"stsd", b"mp4a"]) is not None
    tkhd_dims = []
    moov = find_box(data, [b"moov"])
    if moov:
        for box_type, _, body_start, body_end in iter_boxes(data, *moov):
            if box_type == b"trak":
                tkhd = find_box(data, [b"tkhd"], body_start, body_end)
                if tkhd:
                    # width and height are the last two 16.16 fixed point fields of tkhd
                    offset = tkhd[1] - 8
                    width, height = struct.unpack(">II", data[offset:offset + 8])
                    if width and height:
                        tkhd_dims.append((width >> 16, height >> 16))
    info["dims"] = tkhd_dims
    return info


def route_ffmpeg_core(page: Page):
    """Serve the ffmpeg.wasm core from FFMPEG_WASM_CACHE_DIR, if set, instead of the CDN."""
    cache_dir = os.environ.get("FFMPEG_WASM_CACHE_DIR")
    if not cache_dir:
        return
    cache = pathlib.Path(cache_dir)

    def serve_from_cache(route, request):
        local = cache / request.url.rsplit("/", 1)[-1]
        if local.exists():
            content_type = "application/wasm" if local.suffix == ".wasm" else "text/javascript"
            route.fulfill(status=200, body=local.read_bytes(), content_type=content_type,
                          headers={"Access-Control-Allow-Origin": "*"})
        else:
            route.abort()

    page.route("https://cdn.jsdelivr.net/**", serve_from_cache)


def test_initial_state(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/video-compressor.html")

    expect(page).to_have_title("Video compressor")
    expect(page.locator("h1")).to_have_text("Video compressor")
    expect(page.locator("#drop-zone")).to_be_visible()

    # Settings and results only appear once a video has been chosen
    expect(page.locator("#settings-card")).to_be_hidden()
    expect(page.locator("#results-card")).to_be_hidden()
    expect(page.locator("#error")).to_be_hidden()

    # The vendored ffmpeg.wasm wrapper loaded from this origin
    assert page.evaluate("typeof FFmpegWASM.FFmpeg") == "function"


def test_full_flow_encodes_compatible_mp4s(page: Page, unused_port_server):
    """Downloads ffmpeg.wasm from the CDN unless FFMPEG_WASM_CACHE_DIR is set."""
    route_ffmpeg_core(page)
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/video-compressor.html")

    page.set_input_files("#file-input", str(fixture))
    expect(page.locator("#settings-card")).to_be_visible()
    expect(page.locator("#source-details")).to_contain_text("test-video.mp4")

    # Five default versions, all selected. The fixture is 640x360 so every
    # version is capped to the source resolution; only CRF differs. Keep the
    # three fastest.
    rows = page.locator("#variants-body tr")
    expect(rows).to_have_count(5)
    for row_id in ("xl", "l"):
        page.locator(f"#variants-body tr[data-id={row_id}] input.enabled").uncheck()

    page.click("#generate")
    # ~32 MB download plus three encodes of a 3 second clip
    page.wait_for_selector("#results-card[data-state=done]", timeout=300_000)
    expect(page.locator("#status")).to_contain_text("Done: 3 versions")
    expect(page.locator("#error")).to_be_hidden()

    # Playwright's Chromium has no H.264 decoder, so these details come from
    # ffmpeg probing the file rather than from the <video> element.
    expect(page.locator("#source-details")).to_contain_text("640×360")
    expect(page.locator("#source-details")).to_contain_text("0:03")
    expect(page.locator("#source-details")).to_contain_text("44100 Hz, stereo")

    # The original card plus one card per version, none failed
    expect(page.locator(".result.original")).to_have_count(1)
    expect(page.locator(".result.failed")).to_have_count(0)
    cards = page.locator(".result[data-state=done]")
    expect(cards).to_have_count(3)

    # Sorted smallest first. (The fixture itself is a low bitrate encode, so
    # the versions are not necessarily smaller than it.)
    sizes = [int(s) for s in cards.evaluate_all("els => els.map(e => e.dataset.bytes)")]
    assert sizes == sorted(sizes)
    assert all(size > 1000 for size in sizes)

    # Each card shows the ffmpeg command line that reproduces it
    first_command = cards.first.locator(".command").text_content()
    assert first_command.startswith("ffmpeg ")
    assert "-c:v libx264" in first_command
    assert "-movflags +faststart" in first_command
    assert "-map_metadata -1" in first_command

    # Pull the actual bytes out of the blob URLs and inspect the MP4 structure
    encoded = cards.evaluate_all("""async (els) => {
        const out = [];
        for (const el of els) {
            const buf = await (await fetch(el.querySelector('video').src)).arrayBuffer();
            let s = '';
            for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
            out.push({b64: btoa(s), width: el.dataset.width, height: el.dataset.height});
        }
        return out;
    }""")
    assert len(encoded) == 3
    for item in encoded:
        data = base64.b64decode(item["b64"])
        info = describe_mp4(data)
        assert info["boxes"][0] == b"ftyp"
        # faststart: moov before mdat
        assert info["boxes"].index(b"moov") < info["boxes"].index(b"mdat")
        # 66 = Baseline, 77 = Main, 100 = High. x264 signals the lowest profile the
        # stream actually conforms to, so Main can come out as Baseline; never High.
        assert info["profile_idc"] in (66, 77), info
        assert info["level_idc"] <= 31, info  # 640x360 at 30fps needs no more than level 3.1
        assert info["has_mp4a"]
        assert (640, 360) in info["dims"]
        assert (item["width"], item["height"]) == ("640", "360")


def test_sample_mode_estimates_full_size(page: Page, unused_port_server):
    """Same download as the full flow; checks the 'first N seconds' and 'no audio' options."""
    route_ffmpeg_core(page)
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/video-compressor.html")
    page.set_input_files("#file-input", str(fixture))
    expect(page.locator("#settings-card")).to_be_visible()

    for row_id in ("xl", "l", "m", "s"):
        page.locator(f"#variants-body tr[data-id={row_id}] input.enabled").uncheck()
    page.select_option("#preset", "ultrafast")
    page.check("#sample-mode")
    page.fill("#sample-seconds", "1")
    page.check("#no-audio")
    expect(page.locator("#variants-body tr[data-id=xs] input.audio")).to_be_disabled()

    page.click("#generate")
    page.wait_for_selector("#results-card[data-state=done]", timeout=300_000)
    card = page.locator(".result[data-state=done]")
    expect(card).to_have_count(1)
    expect(card.locator(".title")).to_contain_text("first 0:01")
    expect(card.locator(".size")).to_contain_text("estimated full length")
    expect(card.locator(".meta")).to_contain_text("no audio")
    expect(card.locator("button", has_text="Encode full version")).to_be_visible()
    command = card.locator(".command").text_content()
    assert " -t 1 " in command
    assert " -an " in command
    assert "-c:a" not in command

    # The file really has no audio track
    b64 = card.evaluate("""async (el) => {
        const buf = await (await fetch(el.querySelector('video').src)).arrayBuffer();
        let s = '';
        for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
        return btoa(s);
    }""")
    info = describe_mp4(base64.b64decode(b64))
    assert info["profile_idc"] in (66, 77)
    assert not info["has_mp4a"], info


def test_filename_poster_and_embed_snippet(page: Page, unused_port_server):
    """The filename field drives every download name, the first frame is saved as a
    JPEG, and the embed snippet always points at the first displayed video.
    Same ffmpeg.wasm download as the full flow."""
    route_ffmpeg_core(page)
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/video-compressor.html")
    expect(page.locator("#embed-card")).to_be_hidden()

    page.set_input_files("#file-input", str(fixture))
    expect(page.locator("#settings-card")).to_be_visible()

    # Filename is populated from the chosen file, minus its extension
    expect(page.locator("#base-name")).to_have_value("test-video")
    expect(page.locator("#base-name-hint")).to_contain_text("test-video-medium.mp4")
    expect(page.locator("#base-name-hint")).to_contain_text("test-video.jpg")

    # Before anything is encoded the snippet uses the first selected version
    expect(page.locator("#embed-card")).to_be_visible()
    snippet = page.locator("#embed-code").text_content()
    assert '<video controls playsinline preload="none" poster="test-video.jpg">' in snippet
    assert '<source src="test-video-largest.mp4" type="video/mp4">' in snippet

    # Editing the filename is reflected everywhere, and unsafe characters are cleaned up
    page.fill("#base-name", "My Clip")
    page.locator("#base-name").blur()
    expect(page.locator("#base-name")).to_have_value("My-Clip")
    expect(page.locator("#base-name-hint")).to_contain_text("My-Clip-medium.mp4")
    expect(page.locator("#embed-code")).to_contain_text('src="My-Clip-largest.mp4"')
    expect(page.locator("#embed-code")).to_contain_text('poster="My-Clip.jpg"')

    for row_id in ("xl", "l", "m", "s"):
        page.locator(f"#variants-body tr[data-id={row_id}] input.enabled").uncheck()
    expect(page.locator("#embed-code")).to_contain_text('src="My-Clip-smallest.mp4"')
    page.select_option("#preset", "ultrafast")
    page.check("#sample-mode")
    page.fill("#sample-seconds", "1")

    page.click("#generate")
    page.wait_for_selector("#results-card[data-state=done]", timeout=300_000)
    expect(page.locator("#error")).to_be_hidden()
    card = page.locator(".result[data-state=done]")
    expect(card).to_have_count(1)

    # Download links use the edited filename plus the version name
    expect(card.locator("a.download")).to_have_attribute("download", "My-Clip-smallest-sample.mp4")
    assert "My-Clip-smallest-sample.mp4" in card.locator(".command").text_content()

    # The first frame of the original was saved as a JPEG at the source resolution
    expect(page.locator("#poster-row")).to_be_visible()
    expect(page.locator("#poster-error")).to_be_hidden()
    expect(page.locator("#poster-download")).to_have_attribute("download", "My-Clip.jpg")
    expect(page.locator("#poster-meta")).to_contain_text("640×360")
    poster = page.locator("#poster-img").evaluate("""async (img) => {
        const buf = await (await fetch(img.src)).arrayBuffer();
        const bytes = new Uint8Array(buf);
        return {length: bytes.length, head: Array.from(bytes.slice(0, 3)), width: img.naturalWidth, height: img.naturalHeight};
    }""")
    assert poster["head"] == [0xFF, 0xD8, 0xFF], poster
    assert poster["length"] > 1000
    assert (poster["width"], poster["height"]) == (640, 360)
    expect(page.locator("#poster-size")).to_contain_text("KB")

    # The snippet now names the first displayed video, with its dimensions and the poster
    snippet = page.locator("#embed-code").text_content()
    assert 'preload="none"' in snippet
    assert 'width="640" height="360"' in snippet
    assert 'poster="My-Clip.jpg"' in snippet
    assert '<source src="My-Clip-smallest-sample.mp4" type="video/mp4">' in snippet

    # Renaming after encoding updates the existing results too
    page.fill("#base-name", "final")
    expect(card.locator("a.download")).to_have_attribute("download", "final-smallest-sample.mp4")
    expect(card.locator(".command")).to_contain_text("final-smallest-sample.mp4")
    expect(page.locator("#poster-download")).to_have_attribute("download", "final.jpg")
    expect(page.locator("#embed-code")).to_contain_text('src="final-smallest-sample.mp4"')
    expect(page.locator("#embed-code")).to_contain_text('poster="final.jpg"')

    # The XHTML option spells out boolean attributes and closes the empty element
    expect(page.locator("#embed-xhtml")).not_to_be_checked()
    page.check("#embed-xhtml")
    snippet = page.locator("#embed-code").text_content()
    assert snippet.startswith('<video controls="controls" playsinline="playsinline" preload="none" width="640" height="360" poster="final.jpg">')
    assert '<source src="final-smallest-sample.mp4" type="video/mp4" />' in snippet
    page.uncheck("#embed-xhtml")
    expect(page.locator("#embed-code")).to_contain_text('<video controls playsinline preload="none"')

    # The poster already matches the only video, so there is nothing to resize it to
    expect(card.locator("button.resize-poster")).to_be_hidden()

    # Encode a 320x180 version as well: it becomes the first displayed video and offers
    # to resize the poster to its dimensions
    page.locator("#variants-body tr[data-id=xs] input.enabled").uncheck()
    page.click("#settings-card details summary")
    page.fill("#custom-short", "180")
    page.click("#add-custom")
    page.click("#generate")
    cards = page.locator(".result[data-state=done]")
    expect(cards).to_have_count(2, timeout=120_000)
    page.wait_for_selector("#results-card[data-state=done]", timeout=120_000)
    small = cards.filter(has_text="Custom 1")
    card = cards.filter(has_text="Smallest")
    expect(small.locator(".meta")).to_contain_text("320×180")
    expect(small.locator("a.download")).to_have_attribute("download", "final-custom-1-sample.mp4")
    expect(page.locator("#embed-code")).to_contain_text('src="final-custom-1-sample.mp4"')
    expect(page.locator("#embed-code")).to_contain_text('width="320" height="180"')

    resize = small.locator("button.resize-poster")
    expect(resize).to_be_visible()
    expect(resize).to_have_text("Resize poster to 320×180")
    expect(card.locator("button.resize-poster")).to_be_hidden()
    resize.click()
    expect(page.locator("#poster-meta")).to_contain_text("320×180 JPEG, first frame of the original resized from 640×360")
    assert page.locator("#poster-img").evaluate("img => [img.naturalWidth, img.naturalHeight]") == [320, 180]
    expect(page.locator("#poster-download")).to_have_attribute("download", "final.jpg")
    expect(resize).to_be_hidden()

    # ...and the 640x360 card now offers to resize it back
    back = card.locator("button.resize-poster")
    expect(back).to_be_visible()
    expect(back).to_have_text("Resize poster to 640×360")
    back.click()
    expect(page.locator("#poster-meta")).to_have_text("640×360 JPEG, first frame of the original")
    assert page.locator("#poster-img").evaluate("img => [img.naturalWidth, img.naturalHeight]") == [640, 360]
    expect(back).to_be_hidden()
    expect(resize).to_be_visible()
