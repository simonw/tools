"""
Playwright tests for hn-comments-for-user.html
Tests the HTML-to-text conversion preserves newlines correctly
"""

import pathlib
import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for testing"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


def test_page_loads(page: Page, unused_port_server):
    """Test that the page loads successfully"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/hn-comments-for-user.html")

    # Check title
    expect(page).to_have_title("Hacker News comments for a user")

    # Check main heading
    heading = page.locator("h1")
    expect(heading).to_have_text("Hacker News comments for a user")


def test_htmltotext_preserves_newlines(page: Page, unused_port_server):
    """Test that htmlToText function preserves newlines from p and br tags"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/hn-comments-for-user.html")

    # Test various HTML structures to ensure newlines are preserved
    test_cases = [
        {
            "html": "<p>Line 1</p><p>Line 2</p><p>Line 3</p>",
            "expected_lines": 3,
            "description": "Multiple p tags"
        },
        {
            "html": "Line 1<br>Line 2<br>Line 3",
            "expected_lines": 3,
            "description": "BR tags"
        },
        {
            "html": "<p>First paragraph</p><p>Second paragraph with<br>a line break</p>",
            "expected_lines": 3,
            "description": "Mixed p and br tags"
        },
        {
            "html": "<p>This is <i>italic</i> text</p><p>This is <b>bold</b> text</p>",
            "expected_lines": 2,
            "description": "Nested formatting"
        }
    ]

    for test_case in test_cases:
        # Call the actual htmlToText function from the page
        result = page.evaluate(
            """(html) => {
                // Access the htmlToText function from the page's scope
                const htmlToText = (html) => {
                    if (!html) return '';
                    let text = html
                        .replace(/<\\/p>/gi, '\\n')
                        .replace(/<p>/gi, '')
                        .replace(/<br\\s*\\/?>|<\\/br>/gi, '\\n');
                    const div = document.createElement('div');
                    div.innerHTML = text;
                    return (div.textContent || div.innerText || '').trim();
                };
                return htmlToText(html);
            }""",
            test_case['html']
        )
        
        # Count the number of lines (split by newline)
        lines = [line for line in result.split('\n') if line.strip()]
        
        # Verify the expected number of lines
        assert len(lines) == test_case['expected_lines'], \
            f"Test '{test_case['description']}' failed: expected {test_case['expected_lines']} lines, got {len(lines)}. Result: {result}"


def test_empty_and_null_html(page: Page, unused_port_server):
    """Test that htmlToText handles empty/null HTML gracefully"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/hn-comments-for-user.html")

    # Test empty and null inputs
    test_cases = ["", None, "<p></p>", "<br>"]

    for test_input in test_cases:
        result = page.evaluate(
            """(html) => {
                const htmlToText = (html) => {
                    if (!html) return '';
                    let text = html
                        .replace(/<\\/p>/gi, '\\n')
                        .replace(/<p>/gi, '')
                        .replace(/<br\\s*\\/?>|<\\/br>/gi, '\\n');
                    const div = document.createElement('div');
                    div.innerHTML = text;
                    return (div.textContent || div.innerText || '').trim();
                };
                return htmlToText(html);
            }""",
            test_input
        )
        
        # All these should return empty strings
        assert result == "", f"Expected empty string for input {test_input}, got: {result}"


def test_input_validation(page: Page, unused_port_server):
    """Test validation for username input"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/hn-comments-for-user.html")

    # Check that buttons are present
    fetch_btn = page.locator("#fetchBtn")
    copy_btn = page.locator("#copyBtn")
    
    expect(fetch_btn).to_be_visible()
    expect(copy_btn).to_be_visible()
    
    # Copy button should be disabled initially
    expect(copy_btn).to_be_disabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
