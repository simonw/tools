#!/usr/bin/env python3
"""Convert a pi agent session JSONL log to readable Markdown.

Usage:
    python pi_jsonl_to_md.py input.jsonl [-o output.md] [--no-thinking]

Handles line types found in pi session logs:
  - session / model_change / thinking_level_change (metadata header)
  - message lines with roles: user, assistant, toolResult
    content blocks: text, thinking, toolCall
"""

import argparse
import json
import re
from pathlib import Path


def fence(text: str, lang: str = "") -> str:
    """Wrap text in a fenced code block, widening the fence if needed."""
    max_fence = max([len(m) for m in re.findall(r"^`{3,}", text, flags=re.M)] + [0])
    marker = "`" * max(4, max_fence + 1)
    return f"{marker}{lang}\n{text.rstrip()}\n{marker}"


def render_tool_call(block: dict) -> str:
    name = block.get("name", "tool")
    args = block.get("arguments", {})
    body = json.dumps(args, indent=2, ensure_ascii=False) if isinstance(args, (dict, list)) else str(args)
    lang = {"bash": "bash", "read": "", "write": "", "edit": ""}.get(name, "")
    return f"**🔧 `{name}`**\n\n{fence(body, lang)}"


def render_tool_result(block: dict) -> str:
    name = block.get("toolName") or "result"
    content = block.get("content", [])
    if isinstance(content, list):
        text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    else:
        text = str(content)
    isError = block.get("isError") or (block.get("content") and isinstance(block["content"], list)
                                      and any(isinstance(c, dict) and c.get("type") == "error" for c in block["content"]))
    label = f"**❌ {name} failed**" if isError else f"**↩️ `{name}` result**"
    return f"{label}\n\n{fence(text or '(empty)', '')}"


def render_message(d: dict, include_thinking: bool) -> list[str]:
    """Render one 'message' line into a list of markdown chunks."""
    m = d["message"]
    role = m.get("role")
    content = m.get("content", [])
    if not isinstance(content, list):
        content = [{"type": "text", "text": str(content)}]

    parts: list[str] = []
    if role == "user":
        text = "\n\n".join(c.get("text", "") for c in content if c.get("type") == "text").strip()
        parts.append(f"## 💬 User\n\n{text}")
    elif role == "assistant":
        body: list[str] = []
        for c in content:
            ctype = c.get("type")
            if ctype == "thinking" and include_thinking:
                body.append(f"<details>\n<summary>🧠 Thinking</summary>\n\n{c.get('thinking', '').strip()}\n\n</details>")
            elif ctype == "text":
                body.append(c.get("text", "").strip())
            elif ctype == "toolCall":
                body.append(render_tool_call(c))
        if body:
            parts.append("\n\n".join(body))
    elif role == "toolResult":
        for c in content if isinstance(content, list) else [content]:
            # toolResult lines carry their own fields; handle both shapes
            src = c if (c.get("toolCallId") or c.get("toolName")) else m
            parts.append(render_tool_result(src))
    return parts


def convert(path: Path, include_thinking: bool) -> str:
    out: list[str] = []
    session_meta: dict = {}

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                out.append(f"> ⚠️ Skipped invalid JSONL line: `{line[:80]}…`\n")
                continue

            t = d.get("type")
            if t == "session":
                session_meta.update({k: d[k] for k in ("id", "cwd", "version") if k in d})
            elif t == "model_change" and "modelId" in d:
                session_meta["model"] = f"{d.get('provider', '')}/{d['modelId']}" if d.get("provider") else d["modelId"]
            elif t == "thinking_level_change":
                session_meta.setdefault("thinkingLevel", d.get("thinkingLevel"))
            elif t == "message":
                out.extend(render_message(d, include_thinking))

    # Header
    header = ["# Session Transcript", ""]
    for label, key in [("Session ID", "id"), ("Model", "model"),
                       ("Working dir", "cwd"), ("Thinking level", "thinkingLevel")]:
        if session_meta.get(key):
            v = str(session_meta[key])
            header.append(f"- **{label}:** `{v}`" if key != "id" else f"- **{label}:** {v}")
    out_md = "\n\n".join(out)
    return "\n".join(header).rstrip() + "\n\n---\n\n" + (out_md.rstrip() or "*No messages found.*")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="Input .jsonl session file")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output .md path (default: <input>.md)")
    ap.add_argument("--no-thinking", action="store_true",
                    help="Omit assistant thinking blocks")
    args = ap.parse_args()

    out_path = args.output or args.input.with_suffix(".md")
    md = convert(args.input, include_thinking=not args.no_thinking)
    out_path.write_text(md + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(md)} chars)")


if __name__ == "__main__":
    main()
