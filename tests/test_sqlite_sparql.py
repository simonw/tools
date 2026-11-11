"""
Playwright tests for sqlite-sparql.html

The page runs SQLite's official WASM build with the sparqlite SPARQL extension
(Rust, compiled to WebAssembly and statically linked in - see sqlite-sparql/)
inside a Web Worker, preloaded with the sparqlite tutorial dataset.
"""

import pathlib
import re
from urllib.parse import quote

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()

DONE = (
    "document.querySelector('#results').children.length > 0"
    " && document.getElementById('run').textContent === 'Run'"
)


def open_page(page: Page, server, fragment=""):
    server.start(root)
    page.goto(f"http://127.0.0.1:{server.port}/sqlite-sparql.html{fragment}")
    expect(page.locator("#status .ready")).to_be_visible(timeout=60000)
    page.wait_for_function(DONE, timeout=30000)


def run_example(page: Page, title: str):
    page.evaluate("document.getElementById('results').replaceChildren()")
    page.locator(".example-group button", has_text=title).click()
    page.wait_for_function(DONE, timeout=30000)


def run_editor(page: Page, text: str):
    page.evaluate("document.getElementById('results').replaceChildren()")
    page.locator("#editor").fill(text)
    page.locator("#run").click()
    page.wait_for_function(DONE, timeout=30000)


def test_loads_and_runs_first_example(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    expect(page.locator("h1")).to_have_text("SPARQL in SQLite")
    expect(page.locator("#status")).to_contain_text("sparqlite 0.1.0 (SQLite 3.54.0)")
    expect(page.locator("#status")).to_contain_text("2,413 quads")
    head = page.locator("#results .result-head").first
    expect(head).to_contain_text("25 rows")
    table = page.locator("#results table")
    expect(table.locator("th").first).to_have_text("?lang")
    # IRIs are compacted with the query's prefixes; literals keep their language tag.
    expect(table.locator("a.iri", has_text="ex:Mojo")).to_be_visible()
    expect(table.locator("tbody tr").first).to_contain_text("Mojo@en")
    expect(table.locator("tbody tr").first).to_contain_text("2023")


def test_every_example_runs(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    examples = page.evaluate(
        "EXAMPLES.map(e => ({title: e.title, expectError: !!e.expectError}))"
    )
    assert len(examples) >= 60
    buttons = page.locator(".example-group button")
    assert buttons.count() == len(examples)
    for i, example in enumerate(examples):
        page.evaluate("document.getElementById('results').replaceChildren()")
        buttons.nth(i).click()
        page.wait_for_function(DONE, timeout=30000)
        errors = page.locator("#results .error-box")
        if example["expectError"]:
            assert errors.count() == 1, example["title"]
        else:
            assert errors.count() == 0, (
                example["title"] + ": " + page.inner_text("#results")[:500]
            )


def test_property_paths_and_ask(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "Everything that influenced Rust")
    expect(page.locator("#results table")).to_contain_text("ALGOL 60")
    expect(page.locator("#results table")).to_contain_text("Haskell")
    run_example(page, "ASK: did ALGOL 60 influence Rust?")
    expect(page.locator("#results .ask")).to_have_text("true")
    run_editor(
        page,
        "PREFIX ex: <http://example.org/pl/>\nASK { ex:ALGOL60 ex:influencedBy+ ex:Rust }",
    )
    expect(page.locator("#results .ask")).to_have_text("false")


def test_construct_output_formats(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "CONSTRUCT new triples (Turtle)")
    expect(page.locator("#format")).to_have_value("turtle")
    raw = page.locator("#results pre.raw")
    expect(raw).to_contain_text("designedBy")
    expect(raw).to_contain_text("Pascal")
    page.locator("#format").select_option("ntriples")
    page.wait_for_function(DONE)
    expect(page.locator("#results pre.raw")).to_contain_text(
        "<http://example.org/pl/designedBy>"
    )
    page.locator("#format").select_option("table")
    page.wait_for_function(DONE)
    expect(page.locator("#results .result-head").first).to_contain_text("triples")


def test_select_as_csv_and_json(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "Languages per decade")
    page.locator("#format").select_option("csv")
    page.wait_for_function(DONE)
    raw = page.locator("#results pre.raw")
    expect(raw).to_contain_text("decade,languages")
    expect(raw).to_contain_text("1950,")
    page.locator("#format").select_option("json")
    page.wait_for_function(DONE)
    expect(page.locator("#results pre.raw")).to_contain_text('"vars": [')
    # A graph format for a SELECT query falls back to a table, with a notice.
    page.locator("#format").select_option("turtle")
    page.wait_for_function(DONE)
    expect(page.locator("#results .notice").first).to_contain_text("format for graphs")
    expect(page.locator("#results table")).to_be_visible()


def test_update_changes_store(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "INSERT DATA: a new language")
    expect(page.locator("#results .changes")).to_contain_text("5 quads")
    expect(page.locator("#status")).to_contain_text("2,418 quads")
    # Changing the output format re-runs read-only queries, but never an update.
    page.locator("#format").select_option("csv")
    page.wait_for_timeout(500)
    expect(page.locator("#status")).to_contain_text("2,418 quads")
    run_example(page, "Languages, newest first")
    expect(page.locator("#results table tbody tr").first).to_contain_text("Toylang")


def test_sql_tab_runs_multiple_statements(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    page.locator("#tab-sql").click()
    run_editor(
        page,
        "CREATE TABLE t(x);\nINSERT INTO t VALUES (1), (2), (3);\n"
        "SELECT sum(x) AS total, sparql_version() AS v FROM t;\n"
        "SELECT * FROM no_such_table;\nSELECT 'never reached';",
    )
    results = page.locator("#results .result")
    expect(results).to_have_count(3)
    expect(results.nth(1)).to_contain_text("3 rows changed")
    expect(results.nth(2)).to_contain_text("sparqlite 0.1.0")
    expect(page.locator("#results .error-box")).to_contain_text("no such table")
    expect(page.locator("#results")).not_to_contain_text("never reached")


def test_sparql_error_is_shown(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "Errors point at the problem")
    box = page.locator("#results .error-box")
    expect(box).to_contain_text("sparql: syntax error")
    expect(box).to_contain_text("Prefix not found")


def test_explain_and_engine(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "The most influential languages")
    page.locator("#explain").select_option("plan")
    page.wait_for_function(DONE)
    expect(page.locator("#results pre.raw")).to_contain_text("Scan")
    page.locator("#explain").select_option("sql")
    page.wait_for_function(DONE)
    expect(page.locator("#results pre.raw")).to_contain_text("SELECT")
    # The SQL translation engine gives the same answer as the native engine.
    run_example(page, "The most influential languages")
    native = page.inner_text("#results table")
    page.evaluate("document.getElementById('results').replaceChildren()")
    page.locator("#engine").select_option("sql")
    page.wait_for_function(DONE)
    assert page.inner_text("#results table") == native
    assert "engine=sql" in page.url


def test_click_iri_explores_it(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "Who designed Python?")
    page.locator("#results a.iri", has_text="person:guido-van-rossum").click()
    expect(page.locator("#results th").first).to_have_text("?direction")
    expect(page.locator("#editor")).to_have_value(re.compile("guido-van-rossum"))
    table = page.locator("#results table")
    expect(table).to_contain_text("Guido van Rossum")
    expect(table).to_contain_text("ex:Python")


def test_as_sql_button(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "Who designed Python?")
    page.locator("#to-sql").click()
    page.wait_for_function(DONE)
    expect(page.locator("#tab-sql")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#editor")).to_have_value(re.compile(r"FROM sparql_rows\("))
    expect(page.locator("#results table")).to_contain_text("Guido van Rossum")


def test_query_in_url_fragment(page: Page, unused_port_server):
    q = "SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }"
    open_page(page, unused_port_server, "#sparql=" + quote(q))
    expect(page.locator("#editor")).to_have_value(q)
    expect(page.locator("#results table")).to_contain_text("267")
    page.goto("about:blank")
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/sqlite-sparql.html#sql="
        + quote("SELECT sparql_version() AS v")
    )
    page.wait_for_function(DONE, timeout=60000)
    expect(page.locator("#tab-sql")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#results table")).to_contain_text("sparqlite 0.1.0")


def test_load_rdf_from_data_tab(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    page.locator("#tab-data").click()
    expect(page.locator("#store-stats")).to_contain_text("2,413")
    page.locator("#rdf-sample").click()
    page.locator("#rdf-graph").fill("http://example.org/graph/esoteric")
    page.locator("#rdf-load").click()
    expect(page.locator("#rdf-message")).to_contain_text("Loaded 9 new quads")
    expect(page.locator("#store-graphs")).to_contain_text("esoteric")
    page.locator("#rdf-input").fill("<http://example.org/a> <http://example.org/b> .")
    page.locator("#rdf-format").select_option("ntriples")
    page.locator("#rdf-load").click()
    expect(page.locator("#rdf-message .error-box")).to_contain_text("parse error")
    page.locator("#tab-sparql").click()
    run_editor(
        page,
        "SELECT ?s WHERE { GRAPH <http://example.org/graph/esoteric> "
        "{ ?s a <http://example.org/pl/ProgrammingLanguage> } } ORDER BY ?s",
    )
    expect(page.locator("#results .result-head").first).to_contain_text("2 rows")


def test_empty_reset_download_and_reopen(page: Page, unused_port_server, tmp_path):
    open_page(page, unused_port_server)
    page.locator("#tab-data").click()
    with page.expect_download() as info:
        page.locator("#download-db").click()
    db_file = tmp_path / "playground.sqlite"
    info.value.save_as(db_file)
    assert db_file.read_bytes()[:16] == b"SQLite format 3\x00"
    page.locator("#empty-store").click()
    expect(page.locator("#data-message")).to_contain_text("The store is empty")
    expect(page.locator("#store-stats")).to_contain_text("0 quads")
    page.locator("#open-db").set_input_files(str(db_file))
    expect(page.locator("#data-message")).to_contain_text("2,413 quads")
    page.locator("#empty-store").click()
    expect(page.locator("#store-stats")).to_contain_text("0 quads")
    page.locator("#reset-data").click()
    expect(page.locator("#data-message")).to_contain_text("Reset: 2,413 quads")


def test_stop_restores_last_state(page: Page, unused_port_server):
    open_page(page, unused_port_server)
    run_example(page, "INSERT DATA: a new language")
    # The SPARQL parser takes exponential time on nested !( ... ): a stuck request.
    nested = "!(" * 26 + "true" + ")" * 26
    page.locator("#editor").fill(f"ASK {{ FILTER({nested}) }}")
    page.locator("#run").click()
    stop = page.locator("#stop")
    expect(stop).to_be_visible(timeout=10000)
    stop.click()
    expect(page.locator("#results .error-box")).to_contain_text("Stopped")
    expect(page.locator("#status .ready")).to_be_visible(timeout=60000)
    run_editor(page, "ASK { <http://example.org/pl/Toylang> ?p ?o }")
    expect(page.locator("#results .ask")).to_have_text("true")


def test_mobile_layout(page: Page, unused_port_server):
    page.set_viewport_size({"width": 390, "height": 844})
    open_page(page, unused_port_server)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    examples = page.locator("#examples")
    expect(examples).not_to_have_attribute("open", "")
    page.locator("#examples > summary").click()
    run_example(page, "Labels in five languages")
    expect(page.locator("#results table")).to_contain_text("@ja")
