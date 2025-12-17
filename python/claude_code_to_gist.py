#!/usr/bin/env python3
"""
Find recent .jsonl files and optionally publish one as a Gist.
"""

import argparse
import json
import shutil
import subprocess
import sys
import termios
import tty
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


def find_recent_jsonl_files(folder: Path, limit: int = 10) -> list[tuple[Path, str]]:
    """Find the most recent .jsonl files recursively, excluding agent files and boring sessions."""
    results = []
    for f in folder.glob("**/*.jsonl"):
        if f.name.startswith("agent-"):
            continue
        summary = get_session_summary(f)
        # Skip boring/empty sessions
        if summary.lower() == "warmup" or summary == "(no summary)":
            continue
        results.append((f, summary))

    # Sort by modification time, most recent first
    results.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
    return results[:limit]


def get_session_summary(filepath: Path, max_length: int = 200) -> str:
    """Extract a human-readable summary from the session file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # First priority: summary type entries
                    if obj.get("type") == "summary" and obj.get("summary"):
                        summary = obj["summary"]
                        if len(summary) > max_length:
                            return summary[:max_length - 3] + "..."
                        return summary
                except json.JSONDecodeError:
                    continue

        # Second pass: find first non-meta user message
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if (obj.get("type") == "user" and
                        not obj.get("isMeta") and
                        obj.get("message", {}).get("content")):
                        content = obj["message"]["content"]
                        if isinstance(content, str):
                            # Clean up the content
                            content = content.strip()
                            if content and not content.startswith("<"):
                                if len(content) > max_length:
                                    return content[:max_length - 3] + "..."
                                return content
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return "(no summary)"


def get_interesting_lines(filepath: Path, max_lines: int = 5) -> list[dict]:
    """Extract interesting JSON objects from the file."""
    interesting = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Consider lines with certain keys as "interesting"
                # Skip internal/metadata entries, prefer user messages and assistant responses
                if isinstance(obj, dict):
                    # Prioritize entries with actual content
                    if obj.get("type") in ("user", "assistant", "human", "ai"):
                        interesting.append(obj)
                    elif "message" in obj or "content" in obj or "text" in obj:
                        interesting.append(obj)
                    elif "role" in obj:
                        interesting.append(obj)
                    elif len(interesting) < max_lines:
                        # Fall back to any object if we don't have enough
                        interesting.append(obj)
                if len(interesting) >= max_lines:
                    break
            except json.JSONDecodeError:
                continue
    return interesting[:max_lines]


def format_json_preview(obj: dict, max_width: int = 100) -> str:
    """Format a JSON object for preview, truncating long values."""
    preview = json.dumps(obj, ensure_ascii=False)
    if len(preview) > max_width:
        return preview[:max_width - 3] + "..."
    return preview


def get_key():
    """Read a single keypress, handling arrow keys."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # Escape sequence
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'up'
                elif ch3 == 'B':
                    return 'down'
        elif ch == '\r' or ch == '\n':
            return 'enter'
        elif ch == 'q' or ch == '\x03':  # q or Ctrl+C
            return 'quit'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_lines(n: int):
    """Move cursor up n lines and clear them."""
    for _ in range(n):
        sys.stdout.write('\x1b[A')  # Move up
        sys.stdout.write('\x1b[2K')  # Clear line
    sys.stdout.flush()


def display_file_list(files: list[Path], summaries: list[str], selected: int):
    """Display the file list with the selected item highlighted."""
    term_width = shutil.get_terminal_size().columns
    lines = []
    lines.append("")
    lines.append("Recent sessions (use \u2191\u2193 to select, Enter to confirm, q to quit):")
    lines.append("")

    # Fixed width columns: prefix(3) + date(16) + spaces(2) + size(6) + " KB"(3) + spaces(2) = 32
    fixed_width = 32
    summary_width = term_width - fixed_width - 1  # -1 for safety margin

    for i, f in enumerate(files):
        stat = f.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        size_kb = stat.st_size / 1024
        date_str = mod_time.strftime('%Y-%m-%d %H:%M')
        summary = summaries[i]

        # Truncate or pad summary to fill available width
        if len(summary) > summary_width:
            summary = summary[:summary_width - 3] + "..."
        else:
            summary = summary.ljust(summary_width)

        prefix = " \u25b6 " if i == selected else "   "
        highlight = "\x1b[7m" if i == selected else ""  # Reverse video
        reset = "\x1b[0m" if i == selected else ""

        lines.append(f"{prefix}{highlight}{date_str}  {size_kb:6.0f} KB  {summary}{reset}")

    return lines


def interactive_select(files: list[Path], summaries: list[str]) -> Path | None:
    """Let user select a file using arrow keys."""
    selected = 0
    num_files = len(files)

    # Initial display
    lines = display_file_list(files, summaries, selected)
    sys.stdout.write('\n'.join(lines))
    sys.stdout.flush()
    num_lines = len(lines)

    while True:
        key = get_key()

        if key == 'up':
            selected = (selected - 1) % num_files
        elif key == 'down':
            selected = (selected + 1) % num_files
        elif key == 'enter':
            print()  # New line after selection
            return files[selected]
        elif key == 'quit':
            print("\nCancelled.")
            return None

        # Move cursor to start of display area and clear
        sys.stdout.write(f'\x1b[{num_lines - 1}A')  # Move up to first line
        sys.stdout.write('\x1b[G')  # Move to column 0
        for _ in range(num_lines):
            sys.stdout.write('\x1b[2K')  # Clear line
            sys.stdout.write('\x1b[B')   # Move down
        sys.stdout.write(f'\x1b[{num_lines}A')  # Move back up

        # Redraw
        lines = display_file_list(files, summaries, selected)
        sys.stdout.write('\n'.join(lines))
        sys.stdout.flush()


def create_gist(filepath: Path, public: bool = False) -> dict | None:
    """Create a gist using the gh CLI and return the response."""
    cmd = ["gh", "gist", "create", str(filepath)]
    if public:
        cmd.append("--public")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error creating gist: {result.stderr}")
        return None

    # gh gist create returns the gist URL
    gist_url = result.stdout.strip()

    # Extract gist ID from URL (e.g., https://gist.github.com/user/abc123)
    gist_id = gist_url.rstrip("/").split("/")[-1]

    # Get gist details to find raw URL
    cmd = ["gh", "api", f"/gists/{gist_id}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting gist details: {result.stderr}")
        return None

    return json.loads(result.stdout)


def get_raw_url(gist_data: dict) -> str | None:
    """Extract the raw URL from gist API response."""
    files = gist_data.get("files", {})
    if not files:
        return None
    # Get the first (and typically only) file's raw_url
    first_file = next(iter(files.values()))
    return first_file.get("raw_url")


def print_file_list(files: list[Path], summaries: list[str]):
    """Print the file list without interactive selection."""
    term_width = shutil.get_terminal_size().columns

    print("\nRecent sessions:")
    print("")

    # Fixed width columns: date(16) + spaces(2) + size(6) + " KB"(3) + spaces(2) = 29
    fixed_width = 29
    summary_width = term_width - fixed_width - 1

    for i, f in enumerate(files):
        stat = f.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        size_kb = stat.st_size / 1024
        date_str = mod_time.strftime('%Y-%m-%d %H:%M')
        summary = summaries[i]

        if len(summary) > summary_width:
            summary = summary[:summary_width - 3] + "..."

        print(f"{date_str}  {size_kb:6.0f} KB  {summary}")


def main():
    parser = argparse.ArgumentParser(description="Find and publish recent .jsonl sessions as Gists")
    parser.add_argument("--list", action="store_true", help="List recent sessions and exit")
    args = parser.parse_args()

    projects_folder = Path.home() / ".claude" / "projects"

    if not projects_folder.exists():
        print(f"Projects folder not found: {projects_folder}")
        sys.exit(1)

    # Find recent .jsonl files recursively (also loads summaries and filters)
    if not args.list:
        print("Loading sessions...", end="", flush=True)
    results = find_recent_jsonl_files(projects_folder, limit=10)
    if not args.list:
        sys.stdout.write('\r\x1b[2K')

    if not results:
        print("No .jsonl files found in the projects folder.")
        sys.exit(1)

    jsonl_files = [r[0] for r in results]
    summaries = [r[1] for r in results]

    # If --list flag, just print and exit
    if args.list:
        print_file_list(jsonl_files, summaries)
        sys.exit(0)

    # Let user select a file
    jsonl_file = interactive_select(jsonl_files, summaries)
    if jsonl_file is None:
        sys.exit(0)

    # Get file info
    stat = jsonl_file.stat()
    mod_time = datetime.fromtimestamp(stat.st_mtime)
    size_kb = stat.st_size / 1024

    # Display file info
    print(f"\nSelected file:")
    print(f"  Path: {jsonl_file.resolve()}")
    print(f"  Folder: {jsonl_file.parent.resolve()}")
    print(f"  Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Size: {size_kb:.2f} KB")

    # Show interesting content
    print(f"\nFirst few interesting entries:")
    print("-" * 80)
    interesting = get_interesting_lines(jsonl_file)
    for i, obj in enumerate(interesting, 1):
        print(f"{i}. {format_json_preview(obj)}")
    print("-" * 80)

    # Ask user
    response = input("\nPublish as a Gist? [y/N]: ").strip().lower()
    if response not in ("y", "yes"):
        print("Cancelled.")
        sys.exit(0)

    # Create gist
    print("\nCreating gist...")
    gist_data = create_gist(jsonl_file, public=True)
    if not gist_data:
        sys.exit(1)

    raw_url = get_raw_url(gist_data)
    if not raw_url:
        print("Could not find raw URL in gist response.")
        sys.exit(1)

    print(f"\nGist created!")
    print(f"Raw URL: {raw_url}")

    # Build the timeline URL
    encoded_url = quote(raw_url, safe="")
    timeline_url = f"https://tools.simonwillison.net/claude-code-timeline?url={encoded_url}"

    print(f"\nTimeline URL:")
    print(timeline_url)


if __name__ == "__main__":
    main()
