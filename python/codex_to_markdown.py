#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Iterable


def format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def format_block(text: str, indent: int) -> list[str]:
    spaces = "  " * indent
    inner = text.splitlines() or [""]
    lines = [f"{spaces}```"]
    lines.extend(f"{spaces}{line}" for line in inner)
    lines.append(f"{spaces}```")
    return lines


def command_has_multiline(command: Iterable[object]) -> bool:
    for item in command:
        if isinstance(item, str) and "\n" in item:
            return True
    return False


def format_command_list(command: Iterable[object], indent: int) -> list[str]:
    spaces = "  " * indent
    lines: list[str] = []
    for idx, item in enumerate(command, 1):
        if isinstance(item, str) and "\n" in item:
            lines.append(f"{spaces}- arg {idx} (script):")
            lines.extend(format_block(item, indent + 1))
        else:
            lines.append(f"{spaces}- `{format_scalar(item)}`")
    return lines


def try_format_embedded_command_json(text: str, indent: int) -> list[str] | None:
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    command = parsed.get("command")
    if not isinstance(command, list) or not command_has_multiline(command):
        return None
    return format_value(parsed, indent)


def try_parse_structured_json(text: str) -> object | None:
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None


def format_value(value: object, indent: int = 0) -> list[str]:
    spaces = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, val in value.items():
            if (
                key == "command"
                and isinstance(val, list)
                and command_has_multiline(val)
            ):
                lines.append(f"{spaces}- **{key}**:")
                lines.extend(format_command_list(val, indent + 1))
            elif isinstance(val, (dict, list)):
                lines.append(f"{spaces}- **{key}**:")
                lines.extend(format_value(val, indent + 1))
            elif isinstance(val, str):
                if key == "encrypted_content":
                    byte_count = len(val.encode("utf-8"))
                    lines.append(
                        f"{spaces}- **{key}**: encrypted_content: {byte_count} bytes"
                    )
                    continue
                embedded = try_format_embedded_command_json(val, indent + 1)
                if embedded is not None:
                    lines.append(f"{spaces}- **{key}**:")
                    lines.extend(embedded)
                    continue
                if key in {"arguments", "output"}:
                    structured = try_parse_structured_json(val)
                    if structured is not None:
                        lines.append(f"{spaces}- **{key}**:")
                        lines.extend(format_value(structured, indent + 1))
                        continue
                if "\n" in val or len(val) > 80:
                    lines.append(f"{spaces}- **{key}**:")
                    lines.extend(format_block(val, indent + 1))
                else:
                    lines.append(f"{spaces}- **{key}**: {format_scalar(val)}")
            else:
                lines.append(f"{spaces}- **{key}**: {format_scalar(val)}")
        return lines
    if isinstance(value, list):
        lines = []
        for idx, item in enumerate(value, 1):
            label = f"item {idx}" if isinstance(item, (dict, list)) else None
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}- {label}:")
                lines.extend(format_value(item, indent + 1))
            elif isinstance(item, str) and ("\n" in item or len(item) > 80):
                lines.append(f"{spaces}- entry {idx}:")
                lines.extend(format_block(item, indent + 1))
            else:
                lines.append(f"{spaces}- {format_scalar(item)}")
        return lines
    if isinstance(value, str) and ("\n" in value or len(value) > 80):
        return format_block(value, indent)
    return [f"{spaces}- {format_scalar(value)}"]


def render_markdown(entries: list[dict], source: Path) -> str:
    if not entries:
        return f"# Session Log\n\n_No entries found in {source.name}_."

    session_meta = next((e for e in entries if e.get("type") == "session_meta"), None)
    title = "Session Log"
    if session_meta:
        payload = session_meta.get("payload", {})
        identifier = payload.get("id")
        if identifier:
            title = f"Session Log `{identifier}`"

    last_token_count_index: int | None = None
    for idx, entry in enumerate(entries):
        if entry.get("type") != "event_msg":
            continue
        payload = entry.get("payload")
        if isinstance(payload, dict) and payload.get("type") == "token_count":
            last_token_count_index = idx

    lines = [f"# {title}"]

    if session_meta:
        lines.append("\n## Session Metadata")
        meta_payload = session_meta.get("payload", {})
        meta_lines = format_value(
            {
                "timestamp": session_meta.get("timestamp"),
                "cwd": meta_payload.get("cwd"),
                "originator": meta_payload.get("originator"),
                "cli_version": meta_payload.get("cli_version"),
                "instructions": meta_payload.get("instructions"),
            }
        )
        lines.extend(meta_lines)

    lines.append("\n## Events")
    for idx, entry in enumerate(entries):
        if idx != last_token_count_index:
            if entry.get("type") == "event_msg":
                payload = entry.get("payload")
                if isinstance(payload, dict) and payload.get("type") == "token_count":
                    continue
        timestamp = entry.get("timestamp", "unknown time")
        entry_type = entry.get("type", "unknown type")
        lines.append(f"\n### {timestamp} · {entry_type}")
        payload = entry.get("payload")
        if payload is None:
            lines.append("- _No payload_")
            continue
        lines.extend(format_value(payload))

    return "\n".join(lines) + "\n"


def read_entries(path: Path) -> list[dict]:
    entries: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                entries.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise SystemExit(
                    f"Failed to parse JSON on line {number}: {exc}"
                ) from exc
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Codex JSONL session logs to Markdown"
    )
    parser.add_argument("path", type=Path, help="Path to the .jsonl file")
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit(f"File not found: {args.path}")

    entries = read_entries(args.path)
    markdown = render_markdown(entries, args.path)
    print(markdown)


if __name__ == "__main__":
    main()
