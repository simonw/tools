"""
Playwright tests for sloccount.html
Tests both pasted code analysis and GitHub repository analysis
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
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Check title
    expect(page).to_have_title("SLOCCount - Count Lines of Code")

    # Check main heading
    heading = page.locator("h1")
    expect(heading).to_have_text("SLOCCount - Count Lines of Code")


def test_tab_switching(page: Page, unused_port_server):
    """Test that tab switching works correctly"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Initially, paste tab should be active
    paste_tab = page.locator('[data-tab="paste"]')
    github_tab = page.locator('[data-tab="github"]')

    expect(paste_tab).to_have_class("tab active")
    expect(github_tab).not_to_have_class("tab active")

    # Click GitHub tab
    github_tab.click()

    expect(github_tab).to_have_class("tab active")
    expect(paste_tab).not_to_have_class("tab active")

    # Click back to paste tab
    paste_tab.click()

    expect(paste_tab).to_have_class("tab active")
    expect(github_tab).not_to_have_class("tab active")


def test_initialization_message(page: Page, unused_port_server):
    """Test that initialization messages appear"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization to complete
    # The buttons should change from "Initializing..." to their final text
    analyze_btn = page.locator("#analyze-paste-btn")

    # Wait up to 30 seconds for WebPerl to initialize
    expect(analyze_btn).not_to_have_text("Initializing...", timeout=30000)
    expect(analyze_btn).to_have_text("Analyze Code")


def test_paste_code_validation(page: Page, unused_port_server):
    """Test validation for pasted code analysis"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # Try to analyze without code
    analyze_btn.click()

    status = page.locator("#status")
    expect(status).to_have_class("visible error")
    expect(status).to_contain_text("Please paste some code to analyze")

    # Add code but no filename
    page.locator("#code-input").fill("print('hello world')")
    analyze_btn.click()

    expect(status).to_have_class("visible error")
    expect(status).to_contain_text("Please provide a filename")


def test_paste_code_python(page: Page, unused_port_server):
    """Test analyzing pasted Python code"""
    # Capture console logs
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))

    # Capture errors
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    try:
        expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)
    except AssertionError:
        print("Console logs:", console_logs)
        print("Errors:", errors)
        raise

    # Fill in Python code
    python_code = """
def hello_world():
    # This is a comment
    print("Hello, World!")
    return True

# Another comment
def main():
    hello_world()

if __name__ == "__main__":
    main()
"""

    page.locator("#code-input").fill(python_code)
    page.locator("#filename-input").fill("test.py")

    # Analyze
    analyze_btn.click()

    # Wait for results
    results = page.locator("#results")
    expect(results).to_have_class("visible", timeout=10000)

    # Check that we got results
    total_lines = page.locator("#total-lines")
    expect(total_lines).not_to_have_text("0")

    total_languages = page.locator("#total-languages")
    expect(total_languages).to_have_text("1")

    total_files = page.locator("#total-files")
    expect(total_files).to_have_text("1")

    # Check language breakdown
    language_table = page.locator("#language-table")
    expect(language_table).to_contain_text("Python")


def test_paste_code_javascript(page: Page, unused_port_server):
    """Test analyzing pasted JavaScript code"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # Fill in JavaScript code
    js_code = """
// This is a comment
function hello() {
    console.log("Hello, World!");
}

/* Multi-line
   comment */
function main() {
    hello();
}

main();
"""

    page.locator("#code-input").fill(js_code)
    page.locator("#filename-input").fill("app.js")

    # Analyze
    analyze_btn.click()

    # Wait for results
    results = page.locator("#results")
    expect(results).to_have_class("visible", timeout=10000)

    # Check language breakdown
    language_table = page.locator("#language-table")
    expect(language_table).to_contain_text("JavaScript")


def test_clear_button(page: Page, unused_port_server):
    """Test that the clear button works"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    expect(page.locator("#analyze-paste-btn")).to_have_text("Analyze Code", timeout=30000)

    # Fill in some code
    page.locator("#code-input").fill("print('test')")
    page.locator("#filename-input").fill("test.py")

    # Click clear
    page.locator("#clear-paste-btn").click()

    # Check that inputs are cleared
    expect(page.locator("#code-input")).to_have_value("")
    expect(page.locator("#filename-input")).to_have_value("")


def test_github_repo_validation(page: Page, unused_port_server):
    """Test validation for GitHub repository analysis"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Switch to GitHub tab
    page.locator('[data-tab="github"]').click()

    # Wait for initialization
    analyze_btn = page.locator("#analyze-repo-btn")
    expect(analyze_btn).to_have_text("Analyze Repository", timeout=30000)

    # Try to analyze without URL
    analyze_btn.click()

    status = page.locator("#status")
    expect(status).to_have_class("visible error")
    expect(status).to_contain_text("Please provide a GitHub repository URL")

    # Try with invalid URL
    page.locator("#repo-input").fill("https://example.com/not/github")
    analyze_btn.click()

    expect(status).to_have_class("visible error")
    expect(status).to_contain_text("Invalid format")


MOCK_REPO_FILES = {
    "src/hello.c": '#include <stdio.h>\n\nint main(void) {\n    printf("hello\\n");\n    return 0;\n}\n',
    "scripts/count.py": "import sys\n\n\ndef main():\n    print(len(sys.argv))\n\n\nmain()\n",
    "README.md": "# Not code\n",
}


def mock_github(route):
    """Serve a tiny fake repository in place of the GitHub API and raw.githubusercontent.com,
    whose unauthenticated rate limit is easily exhausted by shared CI runners."""
    url = route.request.url
    headers = {"access-control-allow-origin": "*"}
    if url == "https://api.github.com/repos/example/tiny":
        return route.fulfill(json={"default_branch": "main"}, headers=headers)
    if url == "https://api.github.com/repos/example/tiny/git/trees/main?recursive=1":
        tree = [{"path": path, "type": "blob"} for path in MOCK_REPO_FILES]
        return route.fulfill(json={"tree": tree, "truncated": False}, headers=headers)
    prefix = "https://raw.githubusercontent.com/example/tiny/main/"
    if url.startswith(prefix) and url[len(prefix):] in MOCK_REPO_FILES:
        return route.fulfill(body=MOCK_REPO_FILES[url[len(prefix):]], headers=headers)
    route.fulfill(status=404, headers=headers)


def test_github_repo_analysis(page: Page, unused_port_server):
    """Test analyzing a small GitHub repository"""
    page.route("https://api.github.com/**", mock_github)
    page.route("https://raw.githubusercontent.com/**", mock_github)
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Switch to GitHub tab
    page.locator('[data-tab="github"]').click()

    # Wait for initialization
    analyze_btn = page.locator("#analyze-repo-btn")
    expect(analyze_btn).to_have_text("Analyze Repository", timeout=30000)

    page.locator("#repo-input").fill("https://github.com/example/tiny")
    analyze_btn.click()

    # Wait for results
    results = page.locator("#results")
    expect(results).to_have_class("visible", timeout=60000)

    # Only the C and Python files count, not the README
    expect(page.locator("#total-files")).to_have_text("2")
    expect(page.locator("#total-languages")).to_have_text("2")
    expect(page.locator("#total-lines")).not_to_have_text("0")


def test_mobile_responsive(page: Page, unused_port_server):
    """Test mobile responsiveness"""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Check that tabs are visible
    paste_tab = page.locator('[data-tab="paste"]')
    expect(paste_tab).to_be_visible()

    # Check that input fields are visible
    code_input = page.locator("#code-input")
    expect(code_input).to_be_visible()

    # Check that buttons stack vertically (full width)
    analyze_btn = page.locator("#analyze-paste-btn")
    clear_btn = page.locator("#clear-paste-btn")

    expect(analyze_btn).to_be_visible()
    expect(clear_btn).to_be_visible()


def test_comment_filtering(page: Page, unused_port_server):
    """Test that comments are properly filtered"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # Code with lots of comments
    code_with_comments = """
# This is a comment
def func():
    # Another comment
    x = 1  # Inline comment
    return x
# Final comment
"""

    page.locator("#code-input").fill(code_with_comments)
    page.locator("#filename-input").fill("test.py")

    # Analyze
    analyze_btn.click()

    # Wait for results
    expect(page.locator("#results")).to_have_class("visible", timeout=10000)

    # The line count should be less than total lines due to comment filtering
    # We have 7 total lines, but 4 are comments, so should count ~3 lines
    total_lines_text = page.locator("#total-lines").inner_text()
    total_lines = int(total_lines_text.replace(",", ""))

    # Should be less than total line count (7)
    assert total_lines < 7, f"Expected less than 7 lines, got {total_lines}"
    # Should be at least 2 (the actual code lines)
    assert total_lines >= 2, f"Expected at least 2 lines, got {total_lines}"


def test_percentage_calculation(page: Page, unused_port_server):
    """Test that percentages are calculated correctly"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # Simple code
    page.locator("#code-input").fill("x = 1\ny = 2\n")
    page.locator("#filename-input").fill("test.py")

    # Analyze
    analyze_btn.click()

    # Wait for results
    expect(page.locator("#results")).to_have_class("visible", timeout=10000)

    # For a single language, percentage should be 100%
    percentage_cell = page.locator(".percentage").first
    expect(percentage_cell).to_contain_text("100.0%")


def test_cocomo_year_presets(page: Page, unused_port_server):
    """Test COCOMO year preset switching (2000 vs 2025)"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # Analyze some code
    page.locator("#code-input").fill("def hello():\n    print('Hello')\n    return True\n")
    page.locator("#filename-input").fill("test.py")
    analyze_btn.click()

    # Wait for results
    expect(page.locator("#results")).to_have_class("visible", timeout=10000)

    # Check initial year 2000 values
    salary_input = page.locator("#salary-input")
    overhead_input = page.locator("#overhead-input")
    overhead_mult_input = page.locator("#overhead-multiplier-input")

    expect(salary_input).to_have_value("56286")
    expect(overhead_input).to_have_value("2.4")
    expect(overhead_mult_input).to_have_value("2.4")

    # Switch to 2025
    page.locator("#year-2025").click()
    page.wait_for_timeout(500)  # Wait for recalculation

    # Check 2025 values
    expect(salary_input).to_have_value("133080")
    expect(overhead_input).to_have_value("2.94")
    expect(overhead_mult_input).to_have_value("1.85")

    # Switch back to 2000
    page.locator("#year-2000").click()
    page.wait_for_timeout(500)

    # Should revert to 2000 values
    expect(salary_input).to_have_value("56286")
    expect(overhead_input).to_have_value("2.4")


def test_cost_estimate_footnote_link(page: Page, unused_port_server):
    """Test that the footnote asterisk links to cost estimates section"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    expect(page.locator("#analyze-paste-btn")).to_have_text("Analyze Code", timeout=30000)

    # Analyze code to show results
    page.locator("#code-input").fill("print('test')")
    page.locator("#filename-input").fill("test.py")
    page.locator("#analyze-paste-btn").click()
    expect(page.locator("#results")).to_have_class("visible", timeout=10000)

    # Get initial scroll position
    initial_y = page.evaluate("window.scrollY")

    # Click the asterisk footnote
    page.locator('a[href="#cost-estimates-info"]').first.click()
    page.wait_for_timeout(500)

    # Should have scrolled down
    new_y = page.evaluate("window.scrollY")
    assert new_y > initial_y, "Should scroll to cost estimates section"

    # Cost estimates section should be visible
    expect(page.locator("#cost-estimates-info")).to_be_visible()


def test_wasm_javascript_counter(page: Page, unused_port_server):
    """Test that JavaScript uses WASM c_count counter"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    # JavaScript code (should be counted by WASM)
    js_code = """// Comment
function greet() {
    console.log("Hi");
}

function farewell() {
    console.log("Bye");
}
"""
    page.locator("#code-input").fill(js_code)
    page.locator("#filename-input").fill("app.js")

    # Analyze
    analyze_btn.click()

    # Wait for results
    expect(page.locator("#results")).to_have_class("visible", timeout=10000)

    # Check JavaScript was detected
    language_table = page.locator("#language-table")
    expect(language_table).to_contain_text("JavaScript")

    # Should count lines (WASM counter working)
    total_lines = page.locator("#total-lines").inner_text()
    assert int(total_lines.replace(",", "")) > 0


def test_modern_languages(page: Page, unused_port_server):
    """Test analyzing modern language files (post-2001)"""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sloccount.html")

    # Wait for initialization
    analyze_btn = page.locator("#analyze-paste-btn")
    expect(analyze_btn).to_have_text("Analyze Code", timeout=30000)

    test_cases = [
        ("fun main() { println(\"Hello\") }", "main.kt", "Kotlin"),
        ("defmodule Test do\n  def hello, do: \"world\"\nend", "test.ex", "Elixir"),
        ("fn main() { println!(\"Hello\"); }", "main.rs", "Rust"),
        ("package main\n\nfunc main() {\n  println(\"Hello\")\n}", "main.go", "Go"),
        ("func greet() -> String { return \"Hello\" }", "main.swift", "Swift"),
        ("void main() { print('Hello'); }", "main.dart", "Dart"),
        ("object Hello extends App { println(\"Hello\") }", "Hello.scala", "Scala"),
        ("def greet() { println \"Hello\" }", "main.groovy", "Groovy"),
        ("function greet()\n  println(\"Hello\")\nend", "main.jl", "Julia"),
        ("let greet() = printfn \"Hello\"", "main.fs", "F#"),
    ]

    for code, filename, expected_lang in test_cases:
        # Fill in code
        page.locator("#code-input").fill(code)
        page.locator("#filename-input").fill(filename)

        # Analyze
        analyze_btn.click()

        # Wait for results
        results = page.locator("#results")
        expect(results).to_have_class("visible", timeout=10000)

        # Check that the expected language was detected
        language_table = page.locator("#language-table")
        expect(language_table).to_contain_text(expected_lang)

        # Check that we got a non-zero line count
        total_lines = page.locator("#total-lines")
        expect(total_lines).not_to_have_text("0")


def test_perl_counter_self_tests():
    """Test that all Perl counter scripts have working self-tests"""
    import subprocess

    languages = [
        'kotlin', 'swift', 'dart', 'scala', 'groovy',
        'elixir', 'julia', 'fsharp', 'rust', 'go'
    ]

    for lang in languages:
        counter_script = root / 'lib' / 'sloc' / f'{lang}_count'

        # Run the self-test
        result = subprocess.run(
            ['perl', str(counter_script), '--test'],
            capture_output=True,
            text=True,
            cwd=root
        )

        # Check that it passed
        assert result.returncode == 0, f"{lang}_count self-test failed: {result.stdout}{result.stderr}"
        assert 'PASS' in result.stdout, f"{lang}_count self-test did not print PASS: {result.stdout}"
        assert lang.capitalize() in result.stdout or lang.upper() in result.stdout, \
            f"{lang}_count self-test output doesn't mention language: {result.stdout}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
