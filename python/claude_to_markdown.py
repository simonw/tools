#!/usr/bin/env python3
"""
Convert Claude Code JSONL conversation logs to readable Markdown format.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def format_timestamp(ts):
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts


def format_tool_use(tool):
    """Format tool use content."""
    name = tool.get("name", "Unknown")
    tool_input = tool.get("input", {})

    md = f"**Tool:** `{name}`\n\n"

    if tool_input:
        md += "**Input:**\n```json\n"
        md += json.dumps(tool_input, indent=2)
        md += "\n```\n"

    return md


def format_tool_result(result):
    """Format tool result content."""
    content = result.get("content", "")

    if isinstance(content, list):
        # Handle structured content
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        content = "\n".join(parts)

    md = "**Result:**\n```\n"
    md += str(content)
    md += "\n```\n"

    return md


def format_message_content(content):
    """Format message content (can be text, tool use, thinking, etc)."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                msg_type = item.get("type", "text")

                if msg_type == "text":
                    parts.append(item.get("text", ""))
                elif msg_type == "thinking":
                    thinking = item.get("thinking", "")
                    if thinking:
                        parts.append(
                            f"<details>\n<summary>💭 Thinking</summary>\n\n{thinking}\n</details>"
                        )
                elif msg_type == "tool_use":
                    parts.append(format_tool_use(item))
                elif msg_type == "tool_result":
                    parts.append(format_tool_result(item))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)

    return str(content)


def process_jsonl_line(line):
    """Process a single JSONL line and convert to markdown."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    entry_type = data.get("type", "unknown")

    # Skip file history snapshots
    if entry_type == "file-history-snapshot":
        return None

    # Process user and assistant messages
    if entry_type in ["user", "assistant"]:
        message = data.get("message", {})
        role = message.get("role", entry_type)
        content = message.get("content", "")
        timestamp = data.get("timestamp", "")

        # Format header
        icon = "👤" if role == "user" else "🤖"
        header = f"## {icon} {role.upper()}"

        if timestamp:
            header += f" — {format_timestamp(timestamp)}"

        # Format content
        formatted_content = format_message_content(content)

        # Add metadata if available
        metadata = []
        if entry_type == "assistant":
            model = message.get("model", "")
            if model:
                metadata.append(f"**Model:** `{model}`")

            usage = message.get("usage", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                metadata.append(f"**Tokens:** {input_tokens} in / {output_tokens} out")

        cwd = data.get("cwd", "")
        if cwd:
            metadata.append(f"**Working Dir:** `{cwd}`")

        result = f"{header}\n\n"
        if metadata:
            result += "\n".join(metadata) + "\n\n"
        result += f"{formatted_content}\n\n---\n"

        return result

    return None


def convert_jsonl_to_markdown(input_file, output_file=None):
    """Convert JSONL file to Markdown."""
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: File '{input_file}' not found.", file=sys.stderr)
        return 1

    # Determine output file
    if output_file is None:
        output_file = input_path.with_suffix(".md")

    output_path = Path(output_file)

    # Process file
    entries_processed = 0
    with (
        open(input_path, "r", encoding="utf-8") as infile,
        open(output_path, "w", encoding="utf-8") as outfile,
    ):

        # Write header
        outfile.write(f"# Claude Code Conversation Log\n\n")
        outfile.write(f"**Source:** `{input_path.name}`  \n")
        outfile.write(
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )
        outfile.write("---\n\n")

        # Process each line
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue

            try:
                markdown = process_jsonl_line(line)
                if markdown:
                    outfile.write(markdown)
                    entries_processed += 1
            except Exception as e:
                print(
                    f"Warning: Error processing line {line_num}: {e}", file=sys.stderr
                )
                continue

    print(f"✓ Converted {entries_processed} entries")
    print(f"✓ Output written to: {output_path}")
    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python claude_to_markdown.py <input.jsonl> [output.md]")
        print(
            "\nConverts Claude Code JSONL conversation logs to readable Markdown format."
        )
        return 1

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    return convert_jsonl_to_markdown(input_file, output_file)


if __name__ == "__main__":
    sys.exit(main())
