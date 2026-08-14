"""Playwright tests for markdown-svg-renderer.html."""

import pathlib

from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_svg_is_rendered_raw_in_a_network_isolated_iframe(
    page: Page, unused_port_server
):
    unused_port_server.start(root)
    leaked_urls = []

    def record_leak(route):
        leaked_urls.append(route.request.url)
        route.abort()

    page.route("**/svg-leak-probe-*", record_leak)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/markdown-svg-renderer.html"
    )

    svg = """<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg">
  <style>.wheel { fill: #22c55e; }</style>
  <defs><circle id="wheel" class="wheel" r="20"/></defs>
  <use href="#wheel" x="30" y="40"/>
  <use href="#wheel" x="90" y="40"/>
  <script>
    document.documentElement.setAttribute("data-script-ran", "yes");
    fetch("http://127.0.0.1:%s/svg-leak-probe-script");
  </script>
  <image href="http://127.0.0.1:%s/svg-leak-probe-image"/>
  <foreignObject width="10" height="10">
    <iframe xmlns="http://www.w3.org/1999/xhtml"
      src="http://127.0.0.1:%s/svg-leak-probe-frame"></iframe>
  </foreignObject>
</svg>""" % ((unused_port_server.port,) * 3)

    page.locator("#input").fill(f"```svg\n{svg}\n```")
    block = page.locator("svg-block")
    expect(block).to_be_visible()

    # The SVG is not passed through an allowlist, so valid SVG features such
    # as style and use survive intact.
    assert block.get_attribute("data-svg") == svg + "\n"

    iframe_locator = page.locator("svg-block iframe")
    assert iframe_locator.get_attribute("sandbox") == ""
    csp = iframe_locator.get_attribute("csp")
    assert csp is not None
    assert "default-src 'none'" in csp
    assert "script-src 'none'" in csp
    assert "style-src 'unsafe-inline'" in csp
    assert "img-src data: blob:" in csp

    srcdoc = iframe_locator.get_attribute("srcdoc")
    assert srcdoc is not None
    assert srcdoc.startswith(
        '<!doctype html>\n<meta http-equiv="Content-Security-Policy"'
    )

    iframe_element = iframe_locator.element_handle()
    assert iframe_element is not None
    iframe = iframe_element.content_frame()
    assert iframe is not None
    expect(iframe.locator("use")).to_have_count(2)
    expect(iframe.locator("circle")).to_have_css("fill", "rgb(34, 197, 94)")

    page.wait_for_timeout(500)
    assert iframe.locator("svg").get_attribute("data-script-ran") is None
    assert leaked_urls == []

