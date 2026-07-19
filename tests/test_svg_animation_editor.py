import pathlib
from playwright.sync_api import Page, expect

test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


def test_demo_project_loads(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/svg-animation-editor.html"
    )
    expect(page.locator("h1")).to_contain_text("SVG Animation Editor")
    # demo project ships with three layers: Ball, Star, Title
    expect(page.locator(".layer")).to_have_count(3)
    expect(page.locator("#shapesG ellipse")).to_have_count(1)
    expect(page.locator("#shapesG polygon")).to_have_count(1)
    expect(page.locator("#shapesG text")).to_have_count(1)
    # timeline shows keyframe diamonds for the demo animation
    assert page.locator(".kf").count() > 0


def test_draw_rectangle_and_autokey_tween(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/svg-animation-editor.html"
    )
    page.evaluate("localStorage.clear()")
    page.reload()
    layers_before = page.locator(".layer").count()

    # draw a rectangle
    page.click('[data-tool="rect"]')
    stage = page.locator("#stage").bounding_box()
    page.mouse.move(stage["x"] + 60, stage["y"] + 60)
    page.mouse.down()
    page.mouse.move(stage["x"] + 200, stage["y"] + 160, steps=4)
    page.mouse.up()
    expect(page.locator(".layer")).to_have_count(layers_before + 1)

    # scrub to 2s, then drag the rectangle: auto-key should create a tween
    ruler = page.locator("#ruler").bounding_box()
    # tracks are inset by 8px (TRACK_PAD) so t=0 keyframes clear the labels
    page.mouse.click(ruler["x"] + 8 + 240, ruler["y"] + 12)
    expect(page.locator("#timecode")).to_contain_text("2.00")
    page.click('[data-tool="select"]')
    page.mouse.move(stage["x"] + 130, stage["y"] + 110)
    page.mouse.down()
    page.mouse.move(stage["x"] + 400, stage["y"] + 300, steps=6)
    page.mouse.up()
    keyframed = page.evaluate(
        "Object.keys(project.shapes[project.shapes.length - 1].tracks).length"
    )
    assert keyframed > 0


def test_export_produces_smil_svg(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.goto(
        f"http://127.0.0.1:{unused_port_server.port}/svg-animation-editor.html"
    )
    page.evaluate("localStorage.clear()")
    page.reload()
    page.click("#exportBtn")
    code = page.locator("#exportCode").input_value()
    assert code.startswith("<svg")
    assert "<animate" in code
    assert "keySplines" in code
    parses = page.evaluate(
        """(c) => {
            const doc = new DOMParser().parseFromString(c, 'image/svg+xml');
            return !doc.querySelector('parsererror');
        }""",
        code,
    )
    assert parses
