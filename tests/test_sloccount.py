from http.client import HTTPConnection
import pathlib
from playwright.sync_api import Page, expect
import pytest
import re
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
    """Test that the page loads correctly with initial state"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Check title and heading
    expect(page).to_have_title("SLOCCount - Count Lines of Code")
    expect(page.locator("h1")).to_have_text("SLOCCount - Count Lines of Code")

    # Check tabs are present
    expect(page.locator('.tab[data-tab="paste"]')).to_have_text("Paste Code")
    expect(page.locator('.tab[data-tab="github"]')).to_have_text("GitHub Repository")

    # Paste tab should be active by default
    expect(page.locator('.tab[data-tab="paste"]')).to_have_class(re.compile("active"))
    expect(page.locator('#paste-tab')).to_have_class(re.compile("active"))

    # Results should be hidden initially
    expect(page.locator("#results")).not_to_be_visible()


def test_tab_switching(page: Page, static_server):
    """Test switching between tabs"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Click GitHub tab
    page.locator('.tab[data-tab="github"]').click()
    expect(page.locator('.tab[data-tab="github"]')).to_have_class(re.compile("active"))
    expect(page.locator('#github-tab')).to_have_class(re.compile("active"))
    expect(page.locator('#paste-tab')).not_to_have_class(re.compile("active"))

    # Click back to Paste tab
    page.locator('.tab[data-tab="paste"]').click()
    expect(page.locator('.tab[data-tab="paste"]')).to_have_class(re.compile("active"))
    expect(page.locator('#paste-tab')).to_have_class(re.compile("active"))
    expect(page.locator('#github-tab')).not_to_have_class(re.compile("active"))


def test_analyze_python_code(page: Page, static_server):
    """Test analyzing pasted Python code"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Enter Python code
    python_code = """def hello_world():
    print("Hello, World!")
    return 42

# This is a comment
if __name__ == "__main__":
    hello_world()
"""

    page.locator("#code-input").fill(python_code)
    page.locator("#filename-input").fill("test.py")

    # Click analyze button
    page.locator("#analyze-paste-btn").click()

    # Wait for results to appear
    expect(page.locator("#results")).to_be_visible(timeout=5000)

    # Check that results contain Python
    expect(page.locator("#language-table")).to_contain_text("Python")

    # Check that we have some lines counted (should be non-zero)
    total_lines = page.locator("#total-lines").text_content()
    assert total_lines and total_lines != "0"

    # Check languages count
    expect(page.locator("#total-languages")).to_have_text("1")

    # Check files count
    expect(page.locator("#total-files")).to_have_text("1")


def test_analyze_javascript_code(page: Page, static_server):
    """Test analyzing pasted JavaScript code"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Enter JavaScript code
    js_code = """function calculateSum(a, b) {
    return a + b;
}

const result = calculateSum(5, 3);
console.log(result);
"""

    page.locator("#code-input").fill(js_code)
    page.locator("#filename-input").fill("app.js")

    # Click analyze button
    page.locator("#analyze-paste-btn").click()

    # Wait for results to appear
    expect(page.locator("#results")).to_be_visible(timeout=5000)

    # Check that results contain JavaScript
    expect(page.locator("#language-table")).to_contain_text("JavaScript")


def test_clear_button(page: Page, static_server):
    """Test that the clear button works"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Enter some code
    page.locator("#code-input").fill("print('test')")
    page.locator("#filename-input").fill("test.py")

    # Click clear
    page.locator("#clear-paste-btn").click()

    # Check that inputs are cleared
    expect(page.locator("#code-input")).to_have_value("")
    expect(page.locator("#filename-input")).to_have_value("")


def test_empty_code_validation(page: Page, static_server):
    """Test that analyzing empty code shows an error"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Try to analyze without code
    page.locator("#analyze-paste-btn").click()

    # Should show error status
    expect(page.locator("#status")).to_be_visible()
    expect(page.locator("#status")).to_have_class(re.compile("error"))


def test_missing_filename_validation(page: Page, static_server):
    """Test that analyzing without filename shows an error"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Enter code but no filename
    page.locator("#code-input").fill("print('test')")

    # Try to analyze
    page.locator("#analyze-paste-btn").click()

    # Should show error status
    expect(page.locator("#status")).to_be_visible()
    expect(page.locator("#status")).to_have_class(re.compile("error"))


def test_github_repo_validation(page: Page, static_server):
    """Test GitHub repo URL validation"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization (wait for visible button in active tab)
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    # Switch to GitHub tab
    page.locator('.tab[data-tab="github"]').click()

    # Try to analyze without URL
    page.locator("#analyze-repo-btn").click()

    # Should show error status
    expect(page.locator("#status")).to_be_visible()
    expect(page.locator("#status")).to_have_class(re.compile("error"))


def test_language_detection(page: Page, static_server):
    """Test language detection for various file extensions"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Wait for initialization
    page.wait_for_selector("#analyze-paste-btn:not([disabled])", timeout=10000)

    test_cases = [
        ("test.cpp", "C++"),
        ("test.java", "Java"),
        ("test.rb", "Ruby"),
        ("test.go", "Go"),
        ("test.rs", "Rust"),
    ]

    for filename, expected_lang in test_cases:
        # Enter code
        page.locator("#code-input").fill("// test code\nint main() {}")
        page.locator("#filename-input").fill(filename)

        # Analyze
        page.locator("#analyze-paste-btn").click()

        # Wait for results
        expect(page.locator("#results")).to_be_visible(timeout=5000)

        # Check language
        expect(page.locator("#language-table")).to_contain_text(expected_lang)

        # Clear for next iteration
        page.locator("#clear-paste-btn").click()
        expect(page.locator("#results")).not_to_be_visible()


def test_mobile_responsive(page: Page, static_server):
    """Test that the page is mobile responsive"""
    page.goto("http://127.0.0.1:8123/sloccount.html")

    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})

    # Check that elements are still visible
    expect(page.locator("h1")).to_be_visible()
    expect(page.locator("#code-input")).to_be_visible()
    expect(page.locator("#analyze-paste-btn")).to_be_visible()
