"""
Playwright tests for sqlite-query-explainer.html

The initial-state tests run offline. The full flow (loading Pyodide from the
CDN, building the example database, running annotated queries) is covered by
a single test marked as needing network access.
"""

import pathlib
import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_initial_state(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sqlite-query-explainer.html")

    expect(page).to_have_title("SQLite Query Explainer")
    expect(page.locator("h1")).to_have_text("SQLite Query Explainer")

    # Both database entry points are offered
    expect(page.locator("#load-example")).to_be_visible()
    expect(page.locator("#open-db-btn")).to_be_visible()

    # Query UI and output stay hidden until a database is loaded
    expect(page.locator("#query-card")).to_be_hidden()
    expect(page.locator("#output")).to_be_hidden()
    expect(page.locator("#schema-details")).to_be_hidden()


def test_full_flow_with_example_database(page: Page, unused_port_server):
    """Loads Pyodide from the CDN - needs network access."""
    unused_port_server.start(root)
    page.goto(f"http://localhost:{unused_port_server.port}/sqlite-query-explainer.html")

    page.click("#load-example")
    # Pyodide (~15 MB) plus building 170k rows can take a while on CI
    page.wait_for_selector("#output:not([hidden])", timeout=240_000)

    # The first example query auto-ran: results, plan and bytecode all render
    expect(page.locator("#results-meta")).to_contain_text("row")
    expect(page.locator("#eqp")).to_contain_text("Full table scan")
    assert page.locator("#bytecode-table tbody tr").count() > 5

    # Schema panel lists the example tables
    expect(page.locator("#schema")).to_contain_text("customers")
    expect(page.locator("#schema")).to_contain_text("order_items")

    # Bytecode instructions cross-reference each other with address links
    assert page.locator("#bytecode-table a.addr-link").count() > 3
    first_link = page.locator("#bytecode-table a.addr-link").first
    addr = first_link.get_attribute("data-addr")
    first_link.click()
    assert "flash" in (page.locator(f"#op-{addr}").get_attribute("class") or "")

    # Errors are reported
    page.fill("#sql", "SELECT nope FROM customers")
    page.click("#run")
    page.wait_for_selector("#error:not([hidden])")
    expect(page.locator("#error")).to_contain_text("no such column")

    # Queries are bookmarkable: running one stores it in the URL hash
    page.fill("#sql", "SELECT * FROM customers WHERE id = 42")
    page.click("#run")
    page.wait_for_function("location.hash.includes('customers')")
    # ...and reloading the page restores and re-runs it from the hash
    page.reload()
    page.wait_for_selector("#output:not([hidden])", timeout=240_000)
    assert "WHERE id = 42" in page.input_value("#sql")
    expect(page.locator("#eqp")).to_contain_text("rowid")
