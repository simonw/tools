#!/usr/bin/env python3
"""Test script for microquickjs.html using playwright-python"""

import pathlib
import socket
import subprocess
import time
import sys
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).parent.absolute()


def find_unused_port():
    """Find and return an unused port number on localhost."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def wait_until_ready(port, server):
    """Block until the HTTP server answers, for up to 5 seconds."""
    for _ in range(50):
        time.sleep(0.1)
        if server.poll() is not None:
            raise RuntimeError(f"Server exited early: {server.communicate()[1]}")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return
        except (urllib.error.URLError, ConnectionRefusedError):
            continue
    raise RuntimeError("Server did not become ready in time")


def test_microquickjs(wasm_param=""):
    # Start a simple HTTP server in the background
    port = find_unused_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    wait_until_ready(port, server)

    console_messages = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Capture console messages for debugging
            page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
            page.on("pageerror", lambda err: console_messages.append(f"[PAGE ERROR] {err}"))

            # Navigate to the page - test with wasm param if provided
            print(f"Loading microquickjs.html{wasm_param}...")
            page.goto(f"http://127.0.0.1:{port}/microquickjs.html{wasm_param}")

            # Wait for the page to initialize (wait for "Run Code" button to be enabled)
            print("Waiting for MicroQuickJS to initialize...")
            page.wait_for_function(
                "() => document.getElementById('run-btn').textContent === 'Run Code'",
                timeout=30000
            )
            print("MicroQuickJS initialized successfully!")

            # Test 1: Hello World
            print("\n--- Test 1: Hello World ---")
            code = "'Hello, World!'"
            page.fill("#code-input", code)
            page.click("#run-btn")

            # Wait for output
            page.wait_for_selector("#output-section.visible")
            output = page.text_content("#output")
            print(f"Input: {code}")
            print(f"Output: {output}")
            assert output == "Hello, World!", f"Expected 'Hello, World!' but got '{output}'"
            print("✓ Test 1 passed!")

            # Test 2: Math calculation
            print("\n--- Test 2: Math Calculation ---")
            code = "2 + 2 * 10"
            page.fill("#code-input", code)
            page.click("#run-btn")
            time.sleep(0.5)
            output = page.text_content("#output")
            print(f"Input: {code}")
            print(f"Output: {output}")
            assert output == "22", f"Expected '22' but got '{output}'"
            print("✓ Test 2 passed!")

            # Test 3: Function definition and call
            print("\n--- Test 3: Factorial Function ---")
            code = """function factorial(n) {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}
factorial(5)"""
            page.fill("#code-input", code)
            page.click("#run-btn")
            time.sleep(0.5)
            output = page.text_content("#output")
            print(f"Input: factorial function")
            print(f"Output: {output}")
            assert output == "120", f"Expected '120' but got '{output}'"
            print("✓ Test 3 passed!")

            # Test 4: JSON stringify
            print("\n--- Test 4: JSON Stringify ---")
            code = 'JSON.stringify({a: 1, b: 2})'
            page.fill("#code-input", code)
            page.click("#run-btn")
            time.sleep(0.5)
            output = page.text_content("#output")
            print(f"Input: {code}")
            print(f"Output: {output}")
            assert output == '{"a":1,"b":2}', f"Expected '{{\"a\":1,\"b\":2}}' but got '{output}'"
            print("✓ Test 4 passed!")

            # Test 5: Array methods
            print("\n--- Test 5: Array Methods ---")
            code = "[1,2,3,4,5].filter(function(x) { return x > 2; }).join(',')"
            page.fill("#code-input", code)
            page.click("#run-btn")
            time.sleep(0.5)
            output = page.text_content("#output")
            print(f"Input: {code}")
            print(f"Output: {output}")
            assert output == "3,4,5", f"Expected '3,4,5' but got '{output}'"
            print("✓ Test 5 passed!")

            # Test 6: String operations
            print("\n--- Test 6: String Operations ---")
            code = "'hello'.toUpperCase() + ' ' + 'world'.toLowerCase()"
            page.fill("#code-input", code)
            page.click("#run-btn")
            time.sleep(0.5)
            output = page.text_content("#output")
            print(f"Input: {code}")
            print(f"Output: {output}")
            assert output == "HELLO world", f"Expected 'HELLO world' but got '{output}'"
            print("✓ Test 6 passed!")

            browser.close()
            print("\n" + "="*50)
            print("All tests passed! ✓")
            print("="*50)

    except Exception as e:
        # Print the console output for debugging, then let the failure
        # propagate so pytest reports it
        print(f"\n✗ Test failed with error: {e}")
        if console_messages:
            print("\nConsole output:")
            for msg in console_messages:
                print(f"  {msg}")
        raise
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    param = "?wasm=original" if len(sys.argv) > 1 and sys.argv[1] == "original" else ""
    try:
        test_microquickjs(param)
    except Exception:
        sys.exit(1)
    sys.exit(0)
