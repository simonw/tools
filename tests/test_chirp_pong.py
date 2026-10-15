"""
Playwright tests for chirp-pong.html

Two phones play pong with the ball handed between them over sound: each phone
"sings" frames as FSK chirps and decodes the other's with its microphone. These
tests check the modem on synthetic audio, the game physics, practice mode, and
a full two-phone match played through the real modem over a simulated room.
"""

import pathlib
import time

import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()


@pytest.fixture
def pong_url(unused_port_server):
    unused_port_server.start(root)
    return f"http://127.0.0.1:{unused_port_server.port}/chirp-pong.html"


def collect_errors(page: Page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


def wait_for(page: Page, expression: str, timeout: float = 30, interval: float = 0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = page.evaluate(expression)
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for: {expression}")


def test_title_screen(page: Page, pong_url):
    errors = collect_errors(page)
    page.goto(pong_url)
    expect(page).to_have_title("Chirp Pong")
    expect(page.locator("#btn-duel")).to_be_visible()
    expect(page.locator("#btn-practice")).to_be_visible()
    page.click("#btn-howto")
    expect(page.locator("#trick-list .ic")).to_have_count(7)
    page.click("#btn-howto-back")
    expect(page.locator("#scr-title")).to_have_class("screen active")
    assert errors == []


def test_frame_codec_round_trips_and_catches_corruption(page: Page, pong_url):
    page.goto(pong_url)
    result = page.evaluate(
        """() => {
        const C = ChirpCore;
        let roundTrips = 0, detected = 0, corrupted = 0;
        for (let i = 0; i < 400; i++) {
            const type = i % 8, seq = i & 1, fields = {};
            for (const [name, bits] of C.LAYOUT[type]) fields[name] = Math.floor(Math.random() * (1 << bits));
            const vals = C.encodeFrame(type, seq, fields);
            const frame = C.decodeFrame(vals);
            if (frame && frame.type === type && frame.seq === seq
                && JSON.stringify(frame.fields) === JSON.stringify(fields)) roundTrips++;
            const j = 1 + Math.floor(Math.random() * (vals.length - 1));
            vals[j] = (vals[j] + 1 + Math.floor(Math.random() * 15)) % 16;
            corrupted++;
            if (!C.decodeFrame(vals)) detected++;
        }
        return { roundTrips, detected, corrupted };
    }"""
    )
    assert result["roundTrips"] == 400
    assert result["detected"] == result["corrupted"]


def test_demodulator_decodes_noisy_echoey_audio(page: Page, pong_url):
    page.goto(pong_url)
    result = page.evaluate(
        """() => {
        const C = ChirpCore;
        const gauss = () => Math.sqrt(-2 * Math.log(Math.random() + 1e-12)) * Math.cos(2 * Math.PI * Math.random());
        const out = {};
        for (const sr of [44100, 48000]) {
            for (const band of [0, 1]) {
                let ok = 0;
                for (let t = 0; t < 12; t++) {
                    const type = [2, 3, 4, 5][t % 4];
                    const fields = {};
                    for (const [name, bits] of C.LAYOUT[type]) fields[name] = Math.floor(Math.random() * (1 << bits));
                    const clean = C.synthFrame(band, C.encodeFrame(type, t & 1, fields), sr,
                        { amp: 0.05, lead: 0.15 + Math.random() * 0.1, tail: 0.3 });
                    // A few room echoes, background noise, and the other phone's band busy too.
                    const sig = Float32Array.from(clean);
                    for (const [delay, gain] of [[0.004, 0.5], [0.019, -0.3], [0.047, 0.2], [0.09, 0.12]]) {
                        const d = Math.round(delay * sr);
                        for (let i = d; i < sig.length; i++) sig[i] += clean[i - d] * gain;
                    }
                    const other = C.synthFrame(1 - band, C.encodeFrame(2, 0, { x: 7 }), sr, { amp: 0.3, lead: 0.05 });
                    for (let i = 0; i < sig.length; i++) sig[i] += 0.005 * gauss() + (other[i] || 0);
                    const d = new C.Demodulator(sr);
                    let got = false;
                    d.onFrame = (f) => {
                        if (f.band === band && f.type === type && JSON.stringify(f.fields) === JSON.stringify(fields)) got = true;
                    };
                    for (let i = 0; i < sig.length; i += 128) d.process(sig.subarray(i, i + 128), i / sr);
                    if (got) ok++;
                }
                out[`${sr}/${band}`] = ok;
            }
        }
        // Pure noise must not produce frames.
        const d = new C.Demodulator(48000);
        let falseFrames = 0;
        d.onFrame = () => falseFrames++;
        const noise = new Float32Array(48000 * 10);
        for (let i = 0; i < noise.length; i++) noise[i] = 0.05 * gauss();
        for (let i = 0; i < noise.length; i += 128) d.process(noise.subarray(i, i + 128), i / 48000);
        out.falseFrames = falseFrames;
        return out;
    }"""
    )
    for key in ["44100/0", "44100/1", "48000/0", "48000/1"]:
        assert result[key] >= 11, result
    assert result["falseFrames"] == 0


def test_own_echo_is_ignored_but_reply_is_heard(page: Page, pong_url):
    page.goto(pong_url)
    result = page.evaluate(
        """() => {
        const C = ChirpCore, sr = 48000;
        let acks = 0, echoes = 0;
        for (const latency of [0.02, 0.08, 0.15]) {
            for (let t = 0; t < 4; t++) {
                const ball = C.encodeFrame(2, 0, { x: 9, ang: 3, spd: 2, spin: 3, trick: 1, rally: 7 });
                const t0 = 0.2, t1 = t0 + (C.PRE_SYMS + ball.length) * C.T_SYM;
                // Our own chirp is loud and arrives late; their ACK follows.
                const own = C.synthFrame(0, ball, sr, { amp: 0.5, lead: t0 + latency, tail: 0 });
                const ack = C.synthFrame(1, C.encodeFrame(4, 0, { of: 2 }), sr, { amp: 0.03, lead: t1 + 2 * latency + 0.2, tail: 0.3 });
                const sig = new Float32Array(ack.length);
                for (let i = 0; i < sig.length; i++) sig[i] = (own[i] || 0) + ack[i];
                const d = new C.Demodulator(sr);
                d.noteTx(0, t0, t1);
                d.onFrame = (f) => { if (f.band === 1 && f.type === 4) acks++; if (f.band === 0) echoes++; };
                for (let i = 0; i < sig.length; i += 128) d.process(sig.subarray(i, i + 128), i / sr);
            }
        }
        return { acks, echoes };
    }"""
    )
    assert result == {"acks": 12, "echoes": 0}


PHYSICS = """(kind) => {
    const app = chirpPong, G = app.mainGame;
    app.paused = true;
    G.controller = null;
    G.state = 'have'; G.balls = []; G.bombs = []; G.gem = null; G.vortex = null; G.rally = 0;
    const p = G.paddle;
    Object.assign(p, { x: 50, y: G.H - 16, stun: 0, swipe: 0, flick: 0, vx: 0, vy: 0 });
    G.input = { x: 50, y: p.y };
    for (let i = 0; i < 10; i++) G.update(1 / 60);
    G.balls = [G.makeBall(52, p.y - 14, 0, 110, { speed: 110 })];
    for (let i = 0; i < 40; i++) {
        if (kind === 'swipe') G.setTarget(44 + Math.min(i, 8) * 3, G.H - 16);
        if (kind === 'flick') G.setTarget(50, i < 6 ? G.H - 16 - i * 3.5 : G.H - 34);
        if (kind === 'still') G.setTarget(50, G.H - 16);
        G.update(1 / 60);
    }
    const b = G.balls[0];
    return { rally: G.rally, spin: b.spin, speed: b.speed, vy: b.vy, smashes: G.stats.smashes };
}"""


def test_paddle_swipe_curves_and_flick_smashes(page: Page, pong_url):
    page.goto(pong_url)
    page.click("#btn-practice")
    wait_for(page, "chirpPong.mainGame && chirpPong.mainGame.state === 'serve'", timeout=10)
    still = page.evaluate(PHYSICS, "still")
    swipe = page.evaluate(PHYSICS, "swipe")
    flick = page.evaluate(PHYSICS, "flick")
    assert still["rally"] == 1 and still["vy"] < 0 and still["spin"] == 0
    assert swipe["rally"] == 1 and swipe["spin"] > 0.5
    assert flick["rally"] == 1 and flick["smashes"] == 1
    assert flick["speed"] > still["speed"] * 1.25


def test_touch_drag_moves_paddle_and_tap_serves(page: Page, pong_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(pong_url)
    page.click("#btn-practice")
    wait_for(page, "chirpPong.mainGame.state === 'serve'", timeout=10)
    page.mouse.move(300, 700)
    page.mouse.down()
    page.mouse.move(320, 700, steps=4)
    time.sleep(0.3)
    x = page.evaluate("chirpPong.mainGame.paddle.x")
    assert abs(x - 320 / 3.9) < 2
    page.mouse.up()
    page.mouse.click(320, 700)
    wait_for(page, "chirpPong.mainGame.state === 'have'", timeout=3)


def test_practice_rally_against_cpu(page: Page, pong_url):
    errors = collect_errors(page)
    page.goto(pong_url)
    page.click("#btn-practice")
    page.evaluate("chirpPong.mainGame.controller = new AIController(0.95)")
    wait_for(
        page,
        "chirpPong.mainGame.totals.crossings >= 2 && chirpPong.mainGame.totals.received >= 1",
        timeout=40,
    )
    assert errors == []


def test_game_over_and_rematch(page: Page, pong_url):
    page.goto(pong_url)
    page.click("[data-v='7']")
    page.click("#btn-practice")
    wait_for(page, "chirpPong.mainGame.state === 'serve'", timeout=10)
    page.evaluate(
        """() => {
        const G = chirpPong.mainGame, C = chirpPong.games[1];
        G.score = [5, 6]; C.score = [5, 6];
        G.controller = null;
        G.launchServe();
        Object.assign(G.balls[0], { vx: 0, vy: 120, y: G.H - 5 });
        G.input.x = G.paddle.x = 10;
    }"""
    )
    expect(page.locator("#scr-over")).to_have_class("screen overlay active", timeout=10000)
    expect(page.locator("#over-title")).to_have_text("CPU WINS")
    page.click("#btn-rematch")
    # The loser serves first in the rematch, on both sides of the link.
    wait_for(page, "chirpPong.mainGame.state === 'serve' && chirpPong.games[1].state === 'away'", timeout=10)
    assert page.evaluate("chirpPong.mainGame.score") == [0, 0]


def test_two_phones_play_over_simulated_audio(page: Page, pong_url):
    """Two CPU players pair and pass the ball through the real modem: tones
    mixed into one simulated room, with noise, decoded by each phone."""
    errors = collect_errors(page)
    page.goto(pong_url + "#sim&noise=0.01")
    page.click("#sim-go")
    wait_for(page, "window.chirpSim && chirpSim.eps.every((e) => e.game)", timeout=20)
    sides = page.evaluate("chirpSim.eps.map((e) => e.game.side)")
    assert sorted(sides) == [0, 1]
    wait_for(
        page,
        "chirpSim.eps.every((e) => e.game.totals.received >= 1 && e.game.totals.crossings >= 1)",
        timeout=60,
    )
    stats = page.evaluate("chirpSim.eps.map((e) => e.link.stats)")
    for s in stats:
        assert s["received"] >= 1
    assert errors == []
