"""
Playwright tests for quickjs.html
Tests JavaScript code execution using QuickJS WebAssembly
"""

import pathlib
import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


# Check if CDN is reachable (tests may be running in isolated environment)
def cdn_is_reachable():
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen('https://cdn.jsdelivr.net/', timeout=5)
        return True
    except (urllib.error.URLError, OSError):
        return False


# Skip QuickJS runtime tests if CDN is not reachable
requires_cdn = pytest.mark.skipif(
    not cdn_is_reachable(),
    reason="CDN not reachable - tests require network access to load QuickJS"
)


def test_page_loads(page: Page, unused_port_server):
    """Test that the page loads successfully"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Check title
    expect(page).to_have_title("QuickJS Code Executor")

    # Check main heading
    heading = page.locator("h1")
    expect(heading).to_have_text("QuickJS Code Executor")


@requires_cdn
def test_initialization(page: Page, unused_port_server):
    """Test that QuickJS initializes successfully"""
    # Capture console logs for debugging
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))

    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization - button should change from "Initializing..." to "Run Code"
    run_btn = page.locator("#run-btn")

    try:
        expect(run_btn).to_have_text("Run Code", timeout=30000)
    except AssertionError:
        print("Console logs:", console_logs)
        print("Errors:", errors)
        raise

    expect(run_btn).to_be_enabled()


@requires_cdn
def test_simple_execution(page: Page, unused_port_server):
    """Test executing simple JavaScript code"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Enter simple code
    page.locator("#code-input").fill("1 + 2")

    # Click run
    run_btn.click()

    # Wait for output section to be visible
    output_section = page.locator("#output-section")
    expect(output_section).to_have_class("visible", timeout=5000)

    # Check output shows result
    output = page.locator("#output")
    expect(output).to_contain_text("3")


@requires_cdn
def test_console_log(page: Page, unused_port_server):
    """Test console.log output"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Enter code with console.log
    page.locator("#code-input").fill("console.log('Hello, World!')")

    # Click run
    run_btn.click()

    # Check output
    output = page.locator("#output")
    expect(output).to_contain_text("Hello, World!", timeout=5000)


@requires_cdn
def test_multiple_console_logs(page: Page, unused_port_server):
    """Test multiple console.log statements"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Enter code with multiple console.log statements
    code = """console.log('Line 1');
console.log('Line 2');
console.log('Line 3');"""
    page.locator("#code-input").fill(code)

    # Click run
    run_btn.click()

    # Check output contains all lines
    output = page.locator("#output")
    expect(output).to_contain_text("Line 1", timeout=5000)
    expect(output).to_contain_text("Line 2")
    expect(output).to_contain_text("Line 3")


@requires_cdn
def test_error_handling(page: Page, unused_port_server):
    """Test that JavaScript errors are displayed"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Enter code with syntax error
    page.locator("#code-input").fill("this is not valid javascript")

    # Click run
    run_btn.click()

    # Check output shows error
    output = page.locator("#output")
    expect(output).to_have_class("error-output", timeout=5000)
    expect(output).to_contain_text("Error")


@requires_cdn
def test_url_hash_update(page: Page, unused_port_server):
    """Test that URL hash is updated after execution"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Enter code
    code = "console.log('test')"
    page.locator("#code-input").fill(code)

    # Click run
    run_btn.click()

    # Wait for output
    expect(page.locator("#output-section")).to_have_class("visible", timeout=5000)

    # Check URL hash contains the code
    url = page.url
    assert "#" in url
    # The hash should contain URL-encoded version of the code
    assert "console.log" in url or "console" in url


@requires_cdn
def test_url_hash_load_and_execute(page: Page, unused_port_server):
    """Test that loading page with hash populates and executes code"""
    unused_port_server.start(root)

    # Load page with code in hash
    code = "console.log('from hash')"
    encoded_code = code.replace("'", "%27").replace("(", "%28").replace(")", "%29")
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html#{encoded_code}")

    # Wait for initialization and execution
    run_btn = page.locator("#run-btn")
    expect(run_btn).to_have_text("Run Code", timeout=30000)

    # Check that code was populated
    code_input = page.locator("#code-input")
    expect(code_input).to_have_value(code, timeout=5000)

    # Check that code was executed and output is shown
    output = page.locator("#output")
    expect(output).to_contain_text("from hash", timeout=5000)


@requires_cdn
def test_clear_button(page: Page, unused_port_server):
    """Test that clear button works"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter code and run
    page.locator("#code-input").fill("console.log('test')")
    page.locator("#run-btn").click()

    # Wait for output
    expect(page.locator("#output-section")).to_have_class("visible", timeout=5000)

    # Click clear
    page.locator("#clear-btn").click()

    # Check that input is cleared
    expect(page.locator("#code-input")).to_have_value("")

    # Check that output is hidden
    expect(page.locator("#output-section")).not_to_have_class("visible")


@requires_cdn
def test_keyboard_shortcut(page: Page, unused_port_server):
    """Test Ctrl+Enter keyboard shortcut to run code"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter code
    code_input = page.locator("#code-input")
    code_input.fill("console.log('shortcut test')")

    # Focus the textarea and press Ctrl+Enter
    code_input.focus()
    page.keyboard.press("Control+Enter")

    # Check output
    output = page.locator("#output")
    expect(output).to_contain_text("shortcut test", timeout=5000)


@requires_cdn
def test_execution_time_displayed(page: Page, unused_port_server):
    """Test that execution time is displayed"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter and run code
    page.locator("#code-input").fill("1 + 1")
    page.locator("#run-btn").click()

    # Wait for output
    expect(page.locator("#output-section")).to_have_class("visible", timeout=5000)

    # Check execution time is shown
    execution_time = page.locator("#execution-time")
    expect(execution_time).to_contain_text("Execution time:")
    expect(execution_time).to_contain_text("ms")


@requires_cdn
def test_copy_button(page: Page, unused_port_server):
    """Test that copy button works"""
    unused_port_server.start(root)

    # Grant clipboard permissions
    context = page.context
    context.grant_permissions(["clipboard-read", "clipboard-write"])

    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter and run code
    page.locator("#code-input").fill("console.log('copy me')")
    page.locator("#run-btn").click()

    # Wait for output
    expect(page.locator("#output-section")).to_have_class("visible", timeout=5000)

    # Click copy button
    copy_btn = page.locator("#copy-btn")
    copy_btn.click()

    # Check button text changes to "Copied!"
    expect(copy_btn).to_have_text("Copied!")


@requires_cdn
def test_function_execution(page: Page, unused_port_server):
    """Test executing code with function definitions"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter code with function
    code = """function add(a, b) {
    return a + b;
}
console.log(add(2, 3));"""
    page.locator("#code-input").fill(code)
    page.locator("#run-btn").click()

    # Check output
    output = page.locator("#output")
    expect(output).to_contain_text("5", timeout=5000)


@requires_cdn
def test_return_value_display(page: Page, unused_port_server):
    """Test that return values are displayed with => prefix"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter expression that returns a value
    page.locator("#code-input").fill("42 * 2")
    page.locator("#run-btn").click()

    # Check output shows return value with =>
    output = page.locator("#output")
    expect(output).to_contain_text("=> 84", timeout=5000)


@requires_cdn
def test_object_output(page: Page, unused_port_server):
    """Test that objects are displayed as JSON"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Enter code that logs an object
    page.locator("#code-input").fill("console.log({name: 'test', value: 123})")
    page.locator("#run-btn").click()

    # Check output contains object properties
    output = page.locator("#output")
    expect(output).to_contain_text("name", timeout=5000)
    expect(output).to_contain_text("test")
    expect(output).to_contain_text("123")


def test_mobile_responsive(page: Page, unused_port_server):
    """Test mobile responsiveness"""
    page.set_viewport_size({"width": 375, "height": 667})
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Check elements are visible
    expect(page.locator("h1")).to_be_visible()
    expect(page.locator("#code-input")).to_be_visible()
    expect(page.locator("#run-btn")).to_be_visible()
    expect(page.locator("#clear-btn")).to_be_visible()


@requires_cdn
def test_empty_code_validation(page: Page, unused_port_server):
    """Test validation when trying to run empty code"""
    unused_port_server.start(root)
    page.goto(f"http://127.0.0.1:{unused_port_server.port}/quickjs.html")

    # Wait for initialization
    expect(page.locator("#run-btn")).to_have_text("Run Code", timeout=30000)

    # Clear the placeholder text and try to run empty code
    page.locator("#code-input").fill("")
    page.locator("#run-btn").click()

    # Check error message is shown
    status = page.locator("#status")
    expect(status).to_have_class("visible error", timeout=5000)
    expect(status).to_contain_text("enter some code")
