"""
Playwright tests for latex.html

Equations render with MathJax, documents with faster-latex (WebAssembly),
and the source travels in the URL fragment, either readable or compressed
with a LaTeX-specific DEFLATE dictionary.
"""

import pathlib
import re
from urllib.parse import quote

import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()

BASEL = r"\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}"
# Compressed with LATEX_DICTIONARY_V1. If this test fails, the dictionary has
# changed and every compressed link already shared would break.
BASEL_COMPRESSED = "~1g6UPQ5TggY1MxhkhIgVYroE6aWa1AA"
RENDER_VIEW = re.compile(r"\bview-render\b")
EDIT_VIEW = re.compile(r"\bview-edit\b")
DICTIONARY_SHA256 = "3df04eb786bc74539bd879b538101423529c8057d1e41d5980d67a6c1c445fbe"


@pytest.fixture
def latex_url(unused_port_server):
    unused_port_server.start(root)
    return f"http://127.0.0.1:{unused_port_server.port}/latex.html"


def test_readable_fragment_renders_equation(page: Page, latex_url):
    page.goto(latex_url + "#E=mc^2")
    expect(page.locator("body")).to_have_class(RENDER_VIEW)
    expect(page.locator("#output .eq mjx-container svg")).to_be_visible()
    expect(page.locator("#source")).to_be_hidden()
    expect(page).to_have_title("E=mc^2 · LaTeX")


def test_compressed_fragment_and_dictionary_are_stable(page: Page, latex_url):
    page.goto(latex_url + "#" + BASEL_COMPRESSED)
    expect(page.locator("#output .eq mjx-container svg")).to_be_visible()
    expect(page).to_have_title(BASEL + " · LaTeX")
    digest = page.evaluate(
        """async () => [...new Uint8Array(await crypto.subtle.digest('SHA-256', latexTool.dictionary))]
            .map((b) => b.toString(16).padStart(2, '0')).join('')"""
    )
    assert digest == DICTIONARY_SHA256
    assert page.evaluate("s => latexTool.compressedFragment(s)", BASEL) == BASEL_COMPRESSED


def test_damaged_compressed_link_shows_error(page: Page, latex_url):
    page.goto(latex_url + "#" + BASEL_COMPRESSED[:-6])
    expect(page.locator("#message")).to_contain_text("could not be decompressed")
    expect(page.locator("#source")).to_be_visible()


@pytest.mark.parametrize(
    "source",
    [
        BASEL,
        "x^2 % a comment\n\\text{100\\% café} \\# α",
        "~ starts with a tilde",
        "a+b=c & d|e {f} [g] (h) 'i' \"j\" <k> `l`",
        "\\begin{aligned}\na &= b \\\\\n&= c\n\\end{aligned}",
    ],
)
def test_fragments_round_trip(page: Page, latex_url, source):
    page.goto(latex_url)
    page.wait_for_function("!!window.latexTool")
    result = page.evaluate(
        """source => {
          const readable = latexTool.readableFragment(source);
          const compressed = latexTool.compressedFragment(source);
          return {
            readable: readable === null ? null : latexTool.decodeFragment(readable).source,
            compressed: latexTool.decodeFragment(compressed).source,
            // what location.hash gives back after the browser normalizes the URL
            viaUrl: readable === null ? null : latexTool.decodeFragment(new URL('#' + readable, location.href).hash.slice(1)).source,
          };
        }""",
        source,
    )
    assert result["compressed"] == source
    if source.startswith("~"):
        assert result["readable"] is None
    else:
        assert result["readable"] == source
        assert result["viaUrl"] == source


def test_editor_then_bookmarkable_rendered_view(page: Page, latex_url):
    page.goto(latex_url)
    expect(page.locator("body")).to_have_class(EDIT_VIEW)
    expect(page.locator("#source")).to_be_visible()
    page.locator("#source").fill(r"\int_0^1 x^2\,dx = \frac{1}{3}")
    expect(page.locator("#output .eq mjx-container")).to_be_visible()
    page.get_by_role("button", name="Rendered").click()
    expect(page.locator("body")).to_have_class(RENDER_VIEW)
    assert "?edit" not in page.url
    assert "#" in page.url
    # The rendered view survives a reload, so it can be bookmarked
    page.reload()
    expect(page.locator("body")).to_have_class(RENDER_VIEW)
    expect(page.locator("#output .eq mjx-container")).to_be_visible()
    # Back to the editor with the source intact
    page.get_by_role("button", name="Edit").click()
    expect(page.locator("#source")).to_have_value(r"\int_0^1 x^2\,dx = \frac{1}{3}")
    assert "?edit#" in page.url


def test_fragment_view_can_switch_to_source(page: Page, latex_url):
    page.goto(latex_url + "#" + BASEL_COMPRESSED)
    expect(page.locator("#source")).to_be_hidden()
    page.get_by_role("button", name="Edit").click()
    expect(page.locator("#source")).to_be_visible()
    expect(page.locator("#source")).to_have_value(BASEL)
    page.go_back()
    expect(page.locator("body")).to_have_class(RENDER_VIEW)


def test_ctrl_enter_switches_to_rendered_view(page: Page, latex_url):
    page.goto(latex_url)
    page.locator("#source").fill("a^2 + b^2 = c^2")
    page.locator("#source").press("Control+Enter")
    expect(page.locator("body")).to_have_class(RENDER_VIEW)
    expect(page.locator("#output .eq mjx-container")).to_be_visible()


def test_document_mode_uses_faster_latex(page: Page, latex_url):
    source = "\\section{Introduction}\nLet $x^2 + y^2 = 1$ be a circle.\n\\begin{equation}\ne^{i\\pi} + 1 = 0\n\\end{equation}"
    page.goto(latex_url + "?edit#" + quote(source, safe=""))
    expect(page.locator("#mode-chip")).to_have_text("Document · faster-latex (WASM)")
    expect(page.locator("#output .fl-article h2")).to_contain_text("Introduction")
    expect(page.locator("#output .fl-eqnum")).to_have_text("(1)")
    # faster-latex's MathML is re-typeset by MathJax
    expect(page.locator("#output .fl-article mjx-container")).to_have_count(2)
    assert page.locator("#output math").count() == 0


def test_document_example_and_title(page: Page, latex_url):
    page.goto(latex_url)
    page.get_by_role("button", name="Document").click()
    expect(page.locator("#output .fl-title")).to_have_text("Sums of Odd Numbers")
    expect(page).to_have_title("Sums of Odd Numbers · LaTeX")


def test_cross_reference_links_do_not_replace_the_fragment(page: Page, latex_url):
    page.goto(latex_url)
    page.get_by_role("button", name="Document").click()
    expect(page.locator("#output .fl-title")).to_have_text("Sums of Odd Numbers")
    page.get_by_role("button", name="Rendered").click()
    url = page.url
    page.locator("#output a.fl-ref", has_text="(1)").click()
    page.wait_for_timeout(300)
    assert page.url == url
    expect(page.locator("#output .fl-title")).to_have_text("Sums of Odd Numbers")


def test_unknown_commands_and_errors_are_reported(page: Page, latex_url):
    page.goto(latex_url)
    page.locator("#source").fill(r"\foo + \bar{x}")
    expect(page.locator("#message")).to_have_text("Unknown command: \\foo")
    page.locator("#source").fill(r"\frac{1}{")
    expect(page.locator("#message")).to_contain_text("Missing close brace")


def test_newcommand_does_not_leak_between_renders(page: Page, latex_url):
    page.goto(latex_url)
    page.locator("#source").fill(r"\newcommand{\R}{\mathbb{R}} x \in \R")
    expect(page.locator("#output .eq mjx-container")).to_be_visible()
    expect(page.locator("#message")).to_be_hidden()
    page.locator("#source").fill(r"y \in \R")
    expect(page.locator("#message")).to_have_text("Unknown command: \\R")


def test_javascript_links_are_neutralized(page: Page, latex_url):
    page.goto(latex_url + "#" + quote(r"\href{javascript:alert(1)}{x} + y", safe=""))
    expect(page.locator("#output .eq mjx-container")).to_be_visible()
    assert page.locator("#output [href^='javascript']").count() == 0
    doc = "\\section{Hi}\n<img src=x onerror=alert(1)> \\href{javascript:alert(2)}{link} $z$"
    page.goto(latex_url + "#" + quote(doc, safe=""))
    expect(page.locator("#output .fl-article h2")).to_contain_text("Hi")
    assert page.locator("#output img").count() == 0
    assert page.locator("#output [href^='javascript']").count() == 0


def test_share_panel_links(page: Page, latex_url):
    page.goto(latex_url + "#" + BASEL_COMPRESSED)
    expect(page.locator("#output .eq mjx-container")).to_be_visible()
    page.get_by_role("button", name="Share and export").click()
    expect(page.locator("#compressed-link")).to_have_value(re.compile(re.escape("#" + BASEL_COMPRESSED) + "$"))
    readable = r"\sum_{n=1}^{\infty}%20\frac{1}{n^2}%20=%20\frac{\pi^2}{6}"
    expect(page.locator("#readable-link")).to_have_value(re.compile(re.escape("#" + readable) + "$"))
    expect(page.get_by_role("button", name="Download PNG")).to_be_visible()


@pytest.mark.parametrize(
    "source,mode",
    [
        ("E=mc^2", "equation"),
        ("$$x^2$$", "equation"),
        (r"\[ \int f \]", "equation"),
        (r"\begin{align} a &= b \end{align}", "equation"),
        (r"\text{costs \$5} + x", "equation"),
        (r"a \\[2pt] b", "equation"),
        ("The value $x$ is small.", "document"),
        (r"\section{Intro} Hello", "document"),
        (r"\documentclass{article}\begin{document}Hi\end{document}", "document"),
        (r"\begin{itemize}\item One\end{itemize}", "document"),
        ("$a$ and $b$", "document"),
        (r"\begin{equation} a \end{equation} so $a$ holds", "document"),
        (r"\begin{equation} a \end{equation}\begin{equation} b \end{equation}", "document"),
        ("   ", "empty"),
        ("% just a comment", "empty"),
        ("a \\\\% $ not maths\nb", "equation"),
    ],
)
def test_mode_detection(page: Page, latex_url, source, mode):
    page.goto(latex_url)
    page.wait_for_function("!!window.latexTool")
    assert page.evaluate("s => latexTool.analyze(s).mode", source) == mode


def test_load_example_keeps_draft_recoverable(page: Page, latex_url):
    page.goto(latex_url)
    expect(page.get_by_text("Load an example:")).to_be_visible()
    # Loading onto an empty editor needs no confirmation
    page.get_by_role("button", name="Quadratic formula").click()
    expect(page.locator("#source")).to_have_value(re.compile(r"\\frac\{-b \\pm"))
    # Switching between unmodified examples needs no confirmation either
    page.get_by_role("button", name="Matrix").click()
    expect(page.locator("#source")).to_have_value(re.compile(r"pmatrix"))
    # A draft asks first; dismissing keeps it
    page.locator("#source").fill("my draft x^2")
    dialogs = []
    page.once("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.get_by_role("button", name="Maxwell").click()
    expect(page.locator("#source")).to_have_value("my draft x^2")
    assert dialogs and "Replace" in dialogs[0]
    # Accepting replaces it, and Back brings the draft back
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Maxwell").click()
    expect(page.locator("#source")).to_have_value(re.compile(r"\\nabla"))
    page.go_back()
    expect(page.locator("#source")).to_have_value("my draft x^2")


@pytest.mark.parametrize(
    "name,selector",
    [
        ("Chemistry", "#output .eq mjx-container"),
        ("Prose", "#output .fl-article mjx-container"),
        ("TikZ", "#output .fl-tikz svg"),
        ("Document", "#output .fl-title"),
    ],
)
def test_examples_render(page: Page, latex_url, name, selector):
    page.goto(latex_url)
    page.get_by_role("button", name=name, exact=True).click()
    expect(page.locator(selector).first).to_be_visible()
    expect(page.locator("#message")).to_be_hidden()


# Links are attacker-controlled, and other tools on this origin keep API keys
# in localStorage, so nothing in a fragment may run script.
XSS_PAYLOADS = [
    r"\href{javascript:alert(1)}{a} \href{ JaVaScRiPt:alert(1)}{b} \href{data:text/html,x}{c}",
    r"\style{position:fixed;inset:0;background:url(https://example.com/x)}{a} \bbox[background:url(x)]{b}",
    r"\mmlToken{mi}[href='javascript:alert(1)']{x} \cssId{source}{y} \class{topbar}{z}",
    r"\text{<img src=x onerror=alert(1)>} \texttip{b}{<img src=x onerror=alert(1)>}",
    r"\def\x{\href{javascript:alert(1)}{q}}\x \require{../../evil}",
    "\\section{<svg onload=alert(1)>}\n<img src=x onerror=alert(1)> <script>alert(1)</script>",
    "\\section{L}\n\\href{javascript:alert(1)}{a} \\url{javascript:alert(1)} \\includegraphics{x\" onerror=\"alert(1)}",
    "\\section{C}\n\\textcolor{red;position:fixed;inset:0}{a} \\colorbox{red;position:fixed}{b} \\label{x\" onmouseover=\"alert(1)}",
    "\\begin{verbatim}<script>alert(1)</script>\\end{verbatim} \\verb|<img src=x onerror=alert(1)>|",
    "\\begin{tikzpicture}\\node[fill=red\" onload=\"alert(1)] at (0,0) {<script>alert(1)</script>};\\end{tikzpicture}",
    "\\title{</title><script>alert(1)</script>}\\begin{document}\\maketitle $\\href{javascript:alert(2)}{m}$\\end{document}",
]


@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_xss_payloads_are_inert(page: Page, latex_url, payload):
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.goto(latex_url + "#" + quote(payload, safe=""))
    expect(page.locator("#output mjx-container, #output .fl-article, #output .eq").first).to_be_attached()
    page.wait_for_timeout(500)
    for el in page.locator("#output a, #output [data-mjx-href], #output img").all():
        el.click(timeout=1000, no_wait_after=True, force=True)
    page.wait_for_timeout(300)
    assert dialogs == []
    assert page.url.startswith(latex_url)
    problems = page.evaluate(
        """() => {
          const problems = [];
          for (const el of document.querySelectorAll('#output *')) {
            if (['script', 'iframe', 'object', 'embed', 'foreignobject', 'base', 'form'].includes(el.localName)) {
              problems.push('element ' + el.localName);
            }
            for (const { name, value } of el.attributes) {
              const v = value.replace(/[\\s\\u0000-\\u001f]/g, '').toLowerCase();
              if (name.startsWith('on')) problems.push('handler ' + name);
              if (/^(javascript|data|vbscript):/.test(v)) problems.push('url ' + name + '=' + value);
              if (name === 'id' && document.getElementById(value) !== el && /^(source|output|message|eq-probe)$/.test(value)) {
                problems.push('id ' + value);
              }
            }
            if (getComputedStyle(el).position === 'fixed') problems.push('fixed ' + el.localName);
          }
          return problems;
        }"""
    )
    assert problems == []
