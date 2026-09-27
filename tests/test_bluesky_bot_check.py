"""
Playwright tests for bluesky-bot-check.html

The Bluesky public API is mocked with synthetic accounts, so these run offline:
one that behaves like an AI reply bot and one that behaves like a person.
"""

import json
import pathlib
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import Page, expect


test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()

NOW = datetime.now(timezone.utc).replace(microsecond=0)
PAGE = 100


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def iso_python(dt):
    # How a Python script writes timestamps: microseconds, not milliseconds
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def post_view(did, handle, rkey, text, created, embed=None, reply=None, langs=("en",), created_str=None):
    record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": created_str or iso(created)}
    if langs:
        record["langs"] = list(langs)
    if reply:
        record["reply"] = reply
    view = {
        "$type": "app.bsky.feed.defs#postView",
        "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
        "cid": "bafy" + rkey,
        "author": {"did": did, "handle": handle},
        "record": record,
        "indexedAt": iso(created + timedelta(milliseconds=500)),
        "likeCount": 0,
        "replyCount": 0,
        "repostCount": 0,
    }
    if embed:
        view["embed"] = embed
    return view


def ref(view):
    return {"uri": view["uri"], "cid": view["cid"]}


def reply_item(me, rkey, text, created, parent, root, grandparent=None, likes=0, script=False, replies=0):
    post = post_view(
        me["did"], me["handle"], rkey, text, created,
        reply={"parent": ref(parent), "root": ref(root)},
        langs=None if script else ("en",),
        created_str=iso_python(created) if script else None,
    )
    post["likeCount"] = likes
    post["replyCount"] = replies
    item = {"post": post, "reply": {"parent": parent, "root": root}}
    if grandparent:
        item["reply"]["grandparentAuthor"] = grandparent
    return item


BOT = {"did": "did:plc:replybot", "handle": "helpful-replies.bsky.social"}
SLOW_BOT = {"did": "did:plc:slowbot", "handle": "thoughtful-builder.bsky.social"}
HUMAN = {"did": "did:plc:person", "handle": "person.bsky.social"}

BOT_TOPICS = ["climate policy", "remote work", "open source", "city planning", "ev charging", "space travel"]


def bot_feed():
    items = []
    t = NOW - timedelta(minutes=5)
    for i in range(300):
        topic = BOT_TOPICS[i % len(BOT_TOPICS)]
        parent = post_view(
            f"did:plc:big{i}", f"big{i}.bsky.social", f"p{i}",
            f"Some thoughts on {topic} today", t - timedelta(seconds=8 + i % 12),
        )
        text = (
            f"This is such an insightful take on {topic}! I think the real question is whether "
            f"we can scale these ideas sustainably without leaving anyone behind in the process. "
            f"What do you see as the biggest challenge ahead, big{i}?"
        )
        items.append(reply_item(BOT, f"b{i}", text, t, parent, parent, replies=1 if i % 5 == 0 else 0))
        t -= timedelta(minutes=37)
    return items


def slow_bot_feed():
    """Replies hours after the original post, in bursts of six a few seconds apart, only
    during the working day - so it passes the fast-reply and never-sleeps tests."""
    items = []
    openers = ["Makes sense.", "Interesting angle.", "Fair point.", "Good callout.", "Hard agree.", "Useful framing."]
    for day in range(1, 31):
        for burst in range(2):
            start = (NOW - timedelta(days=day)).replace(hour=14 + burst * 3, minute=5, second=0)
            for k in range(6):
                i = day * 100 + burst * 10 + k
                t = start + timedelta(seconds=15 * k)
                parent = post_view(f"did:plc:dev{i}", f"dev{i}.bsky.social", f"q{i}",
                                   "Shipping agents to production is harder than it looks", t - timedelta(hours=3 + k))
                text = (
                    f"{openers[k]} The gap between a demo agent and one you can trust in production is "
                    f"mostly evals and permissions, not the model itself. Curious how team {i} handles it at scale."
                )
                items.append(reply_item(SLOW_BOT, f"s{i}", text, t, parent, parent, script=True,
                                        replies=1 if k == 0 else 0))
    items.sort(key=lambda it: it["post"]["record"]["createdAt"], reverse=True)
    return items


def human_feed():
    items = []
    me = HUMAN
    hours = [15, 17, 19, 21, 23, 1, 3]  # never posts 04:00-14:00 UTC
    texts = [
        "lol",
        "Yes! Exactly this.",
        "I went to that exhibition last week and honestly it was much better than the reviews "
        "suggested - the second room especially, with all the early sketches. Worth the trip.",
        "hmm not sure about that one",
        "My cat has decided the keyboard is her bed now, so this reply is brought to you by the "
        "three keys she isn't lying on.",
        "Agreed",
    ]
    for i in range(300):
        day = i // 5
        date = (NOW - timedelta(days=day + 1)).replace(hour=0, minute=0, second=0)
        t = date + timedelta(hours=hours[i % len(hours)], minutes=(i * 13) % 50)
        text = texts[i % len(texts)]
        kind = i % 5
        if kind == 0:
            post = post_view(
                me["did"], me["handle"], f"h{i}", text, t,
                embed={"$type": "app.bsky.embed.images#view", "images": []},
            )
            post["likeCount"] = 12
            post["replyCount"] = 3
            items.append({"post": post})
        elif kind == 1:  # someone replied to my post, I reply back
            root = post_view(me["did"], me["handle"], f"r{i}", "my post", t - timedelta(hours=3))
            parent = post_view(f"did:plc:friend{i % 7}", f"friend{i % 7}.bsky.social", f"f{i}",
                               "reply to you", t - timedelta(minutes=1))
            items.append(reply_item(me, f"h{i}", text, t, parent, root,
                                    grandparent={"did": me["did"], "handle": me["handle"]}, likes=2))
        elif kind == 2:  # drive-by reply at a human-looking delay
            parent = post_view(f"did:plc:friend{i % 9}", f"friend{i % 9}.bsky.social", f"d{i}",
                               "a top-level post", t - timedelta(minutes=5 + (i * 7919) % 480))
            items.append(reply_item(me, f"h{i}", text, t, parent, parent, likes=1))
        elif kind == 3:  # continuing my own thread
            parent = post_view(me["did"], me["handle"], f"s{i}", "thread start", t - timedelta(minutes=2))
            items.append(reply_item(me, f"h{i}", text, t, parent, parent))
        else:  # joining someone else's thread
            root = post_view(f"did:plc:friend{i % 5}", f"friend{i % 5}.bsky.social", f"tr{i}",
                             "thread root", t - timedelta(hours=6))
            parent = post_view(f"did:plc:other{i % 4}", f"other{i % 4}.bsky.social", f"tp{i}",
                               "a reply in the thread", t - timedelta(minutes=20 + i % 90))
            items.append(reply_item(me, f"h{i}", text, t, parent, root))
        if i % 10 == 0:
            original = post_view("did:plc:someone", "someone.bsky.social", f"o{i}", "a good post", t)
            items.append({"post": original, "reason": {"$type": "app.bsky.feed.defs#reasonRepost", "indexedAt": iso(t)}})
    return items


ACCOUNTS = {
    BOT["handle"]: {
        "profile": {
            **BOT, "displayName": "Helpful Replies", "followersCount": 41, "followsCount": 3200,
            "postsCount": 2100, "createdAt": iso(NOW - timedelta(days=12)),
        },
        "feed": bot_feed(),
    },
    SLOW_BOT["handle"]: {
        "profile": {
            **SLOW_BOT, "displayName": "Builder", "followersCount": 25, "followsCount": 14,
            "postsCount": 360, "createdAt": iso(NOW - timedelta(days=200)),
        },
        "feed": slow_bot_feed(),
    },
    HUMAN["handle"]: {
        "profile": {
            **HUMAN, "displayName": "A Person", "followersCount": 320, "followsCount": 410,
            "postsCount": 4100, "createdAt": iso(NOW - timedelta(days=700)),
        },
        "feed": human_feed(),
    },
}
BY_DID = {a["profile"]["did"]: a for a in ACCOUNTS.values()}


def mock_api(route):
    url = urllib.parse.urlparse(route.request.url)
    qs = urllib.parse.parse_qs(url.query)
    method = url.path.rsplit("/", 1)[-1]
    if method == "app.bsky.actor.getProfile":
        actor = qs["actor"][0]
        account = ACCOUNTS.get(actor) or BY_DID.get(actor)
        if not account:
            return route.fulfill(status=400, content_type="application/json",
                                 headers={"access-control-allow-origin": "*"},
                                 body=json.dumps({"error": "InvalidRequest", "message": "Profile not found"}))
        data = account["profile"]
    elif method == "app.bsky.feed.getAuthorFeed":
        feed = BY_DID[qs["actor"][0]]["feed"]
        start = int(qs.get("cursor", ["0"])[0])
        data = {"feed": feed[start:start + PAGE]}
        if start + PAGE < len(feed):
            data["cursor"] = str(start + PAGE)
    elif method == "app.bsky.actor.getProfiles":
        data = {"profiles": [
            {"did": d, "handle": d.split(":")[-1] + ".bsky.social",
             "followersCount": 55000 if d.startswith("did:plc:big") else 180}
            for d in qs["actors"]
        ]}
    else:
        return route.abort()
    route.fulfill(status=200, content_type="application/json",
                  headers={"access-control-allow-origin": "*"}, body=json.dumps(data))


@pytest.fixture
def tool(page: Page, unused_port_server):
    unused_port_server.start(root)
    page.route("https://public.api.bsky.app/**", mock_api)

    def open_tool(user=None):
        suffix = "?user=" + urllib.parse.quote(user) if user else ""
        page.goto(f"http://localhost:{unused_port_server.port}/bluesky-bot-check.html{suffix}")
        return page

    return open_tool


def test_initial_state(tool):
    page = tool()
    expect(page).to_have_title("Bluesky reply bot checker")
    expect(page.locator("#userInput")).to_be_visible()
    expect(page.locator("#results")).to_be_hidden()


def test_bot_like_account(tool):
    page = tool("@" + BOT["handle"])
    expect(page.locator("#results")).to_be_visible(timeout=20_000)

    expect(page.locator(".verdict-badge")).to_have_text("⚑Strong bot-like pattern")
    expect(page.locator("#overview")).to_contain_text("all 300 posts the API returned")

    flagged = page.locator(".signal.flag-status .signal-name").all_inner_texts()
    for name in [
        "Replies arrive very quickly",
        "Replies faster than anyone could type them",
        "Never replies back",
        "Never takes a break",
        "Unusually consistent reply length",
        "Nothing but text",
        "New account",
    ]:
        assert name in flagged

    # Examples show the evidence for each reply
    expect(page.locator("#examples .reply-card").first).to_contain_text("Faster than typing")
    expect(page.locator("#examples .reply-card").first).to_contain_text("55,000 followers")

    # Recent replies list is capped at 50
    assert page.locator("#recentReplies .reply-card").count() == 50

    # All posts list pages in hundreds
    assert page.locator("#allPosts .post-row").count() == 100
    page.click("#showMore")
    assert page.locator("#allPosts .post-row").count() == 200


def test_human_like_account(tool):
    page = tool(HUMAN["handle"])
    expect(page.locator("#results")).to_be_visible(timeout=20_000)

    expect(page.locator(".verdict-badge")).to_have_text("✓Few bot-like signals")
    assert page.locator(".signal.flag-status").count() == 0
    expect(page.locator("#verdict")).to_contain_text("None of the direct checks for automation were triggered")
    # Passing a two-way test counts as human-like; one-way signals are just "not triggered"
    human_like = page.locator(".signal.clear-status .signal-name").all_inner_texts()
    assert "Never takes a break" in human_like
    assert "Never replies back" in human_like
    not_triggered = page.locator(".signal.quiet-status .signal-name").all_inner_texts()
    assert "Replies arrive very quickly" in not_triggered

    # Posting mix shows the reposts and image posts
    expect(page.locator("#replyStats")).to_contain_text("Reposts of other people")
    expect(page.locator("#overview")).to_contain_text("Reposts")

    # Filtering the full list
    page.click("#allPosts button[data-filter='top']")
    assert page.locator("#allPosts .post-row").count() == 60
    expect(page.locator("#allPosts .post-row").first).to_contain_text("Top-level post")


def test_slow_scheduled_bot(tool):
    """Slow replies must not count in a bot's favour: bursts, script records and never
    replying back are enough."""
    page = tool(SLOW_BOT["handle"])
    expect(page.locator("#results")).to_be_visible(timeout=20_000)

    expect(page.locator(".verdict-badge")).to_have_text("⚑Strong bot-like pattern")
    flagged = page.locator(".signal.flag-status .signal-name").all_inner_texts()
    for name in [
        "Replies posted by software, not an app",
        "Replies faster than anyone could type them",
        "Never replies back",
        "Only drive-by replies to top-level posts",
        "Unusually consistent reply length",
    ]:
        assert name in flagged
    assert "Replies arrive very quickly" not in flagged
    assert "Never takes a break" not in flagged

    # The typing evidence cites the gap after its own previous post
    expect(page.locator("#examples")).to_contain_text("after this account’s own previous post")
    expect(page.locator("#examples")).to_contain_text("a format the Bluesky app never uses")


def test_profile_not_found(tool):
    page = tool("nobody.bsky.social")
    expect(page.locator("#status")).to_contain_text("Profile not found", timeout=20_000)
    expect(page.locator("#results")).to_be_hidden()
