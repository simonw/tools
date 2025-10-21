import pathlib
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_initial_state(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/ocr.html")
    expect(page.locator("h1")).to_have_text(
        "OCR PDFs and images directly in your browser"
    )
    expect(page.locator("#dropzone")).to_have_text(
        "Drag and drop a PDF, JPG, PNG, or GIF file here or click to select a file"
    )
    expect(page.locator("#fullDocumentSection")).not_to_be_visible()
    expect(page.locator("#id_language")).to_have_value("eng")


def test_open_image(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/ocr.html")
    file_input = page.locator("#fileInput")
    file_input.set_input_files(str(test_dir / "ocr-test-text.png"))
    expect(page.locator(".image-container img")).to_be_visible()
    expect(page.locator(".textarea-alt")).to_have_attribute(
        "placeholder", "OCRing image..."
    )
    expect(page.locator(".textarea-alt")).to_have_value("OCR test text")
    expect(page.locator("#fullDocumentSection")).not_to_be_visible()


def test_open_pdf(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/ocr.html")
    page.locator("#fileInput").set_input_files(str(test_dir / "three_page_pdf.pdf"))
    expect(page.locator(".image-container img")).to_have_count(3)
    expect(page.locator(".textarea-alt")).to_have_count(3)
    expect(page.locator(".textarea-alt").nth(0)).to_have_value("Page 1")
    expect(page.locator(".textarea-alt").nth(1)).to_have_value("Second page")
    expect(page.locator(".textarea-alt").nth(2)).to_have_value("Page the third")
    expect(page.locator("#fullDocumentSection")).to_be_visible()
    expect(page.locator("#fullDocument")).to_have_value(
        "Page 1\n\nSecond page\n\nPage the third"
    )
