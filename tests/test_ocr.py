from http.client import HTTPConnection
import pathlib
from playwright.sync_api import Page, expect
import pytest
from subprocess import Popen, PIPE
import time


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


@pytest.fixture(scope="module")
def static_server():
    process = Popen(
        ["python", "-m", "http.server", "8123", "--directory", root], stdout=PIPE
    )
    retries = 5
    while retries > 0:
        conn = HTTPConnection("127.0.0.1:8123")
        try:
            conn.request("HEAD", "/")
            response = conn.getresponse()
            if response is not None:
                yield process
                break
        except ConnectionRefusedError:
            time.sleep(1)
            retries -= 1

    if not retries:
        raise RuntimeError("Failed to start http server")
    else:
        process.terminate()
        process.wait()


def test_initial_state(page: Page, static_server):
    page.goto("http://127.0.0.1:8123/ocr.html")
    expect(page.locator("h1")).to_have_text(
        "OCR PDFs and images directly in your browser"
    )
    expect(page.locator("#dropzone")).to_have_text(
        "Drag and drop a PDF, JPG, PNG, or GIF file here or click to select a file"
    )
    expect(page.locator("#fullDocumentSection")).not_to_be_visible()
    # Wait for Tesseract and pdfjsLib to load from CDN
    page.wait_for_function("() => typeof Tesseract !== 'undefined' && typeof pdfjsLib !== 'undefined'", timeout=60000)
    # Wait for language select to be populated
    page.wait_for_function("() => document.getElementById('id_language').options.length > 0", timeout=10000)
    expect(page.locator("#id_language")).to_have_value("eng")


def test_open_image(page: Page, static_server):
    page.goto("http://127.0.0.1:8123/ocr.html")
    # Wait for Tesseract and pdfjsLib to load from CDN
    page.wait_for_function("() => typeof Tesseract !== 'undefined' && typeof pdfjsLib !== 'undefined'", timeout=60000)
    # Wait for language select to be populated
    page.wait_for_function("() => document.getElementById('id_language').options.length > 0", timeout=10000)
    file_input = page.locator("#fileInput")
    file_input.set_input_files(str(test_dir / "ocr-test-text.png"))
    expect(page.locator(".image-container img")).to_be_visible()
    expect(page.locator(".textarea-alt")).to_have_attribute(
        "placeholder", "OCRing image..."
    )
    expect(page.locator(".textarea-alt")).to_have_value("OCR test text", timeout=30000)
    expect(page.locator("#fullDocumentSection")).not_to_be_visible()


def test_open_pdf(page: Page, static_server):
    page.goto("http://127.0.0.1:8123/ocr.html")
    # Wait for Tesseract and pdfjsLib to load from CDN
    page.wait_for_function("() => typeof Tesseract !== 'undefined' && typeof pdfjsLib !== 'undefined'", timeout=60000)
    # Wait for language select to be populated
    page.wait_for_function("() => document.getElementById('id_language').options.length > 0", timeout=10000)
    page.locator("#fileInput").set_input_files(str(test_dir / "three_page_pdf.pdf"))
    expect(page.locator(".image-container img")).to_have_count(3, timeout=30000)
    expect(page.locator(".textarea-alt")).to_have_count(3)
    expect(page.locator(".textarea-alt").nth(0)).to_have_value("Page 1", timeout=30000)
    expect(page.locator(".textarea-alt").nth(1)).to_have_value("Second page", timeout=30000)
    expect(page.locator(".textarea-alt").nth(2)).to_have_value("Page the third", timeout=30000)
    expect(page.locator("#fullDocumentSection")).to_be_visible()
    expect(page.locator("#fullDocument")).to_have_value(
        "Page 1\n\nSecond page\n\nPage the third"
    )
