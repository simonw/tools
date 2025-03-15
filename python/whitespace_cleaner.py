#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///

import os
import sys
import argparse
from pathlib import Path


def is_text_file(file_path):
    """
    Check if a file is a text file by attempting to read it as UTF-8.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(1024)  # Try reading a small chunk
        return True
    except UnicodeDecodeError:
        return False
    except Exception:
        return False


def process_file(file_path, dry_run=False):
    """
    Process a single file, replacing lines with only whitespace with empty lines.
    Returns a tuple of (file_path, changes_made, lines_changed)
    """
    if not is_text_file(file_path):
        return file_path, False, 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        changes_needed = False
        lines_changed = 0
        new_lines = []

        for line in lines:
            # Check if the line contains only whitespace characters (spaces, tabs)
            # but is not already just a newline
            if line.strip() == "" and line != "\n":
                new_lines.append("\n")
                changes_needed = True
                lines_changed += 1
            else:
                new_lines.append(line)

        if changes_needed and not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return file_path, changes_needed, lines_changed

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return file_path, False, 0


def main():
    parser = argparse.ArgumentParser(
        description="Replace whitespace-only lines with blank lines in text files."
    )
    parser.add_argument(
        "paths", nargs="+", help="One or more files or directories to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()

    total_files_processed = 0
    total_files_changed = 0
    total_lines_changed = 0

    for path_str in args.paths:
        path = Path(path_str)

        if not path.exists():
            print(f"Path does not exist: {path}", file=sys.stderr)
            continue

        if path.is_file():
            # Process a single file
            filepath, changed, lines = process_file(path, args.dry_run)
            total_files_processed += 1
            if changed:
                total_files_changed += 1
                total_lines_changed += lines
                action = "Would replace" if args.dry_run else "Replaced"
                print(f"{action} {lines} whitespace-only line(s) in {filepath}")

        elif path.is_dir():
            # Recursively process a directory
            for root, _, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    filepath_obj = Path(filepath)

                    # Skip hidden files and directories
                    if filepath_obj.name.startswith(".") or any(
                        part.startswith(".") for part in filepath_obj.parts
                    ):
                        continue

                    filepath, changed, lines = process_file(filepath, args.dry_run)
                    total_files_processed += 1
                    if changed:
                        total_files_changed += 1
                        total_lines_changed += lines
                        action = "Would replace" if args.dry_run else "Replaced"
                        print(f"{action} {lines} whitespace-only line(s) in {filepath}")

    # Print summary
    print(f"\nSummary:")
    print(f"Files processed: {total_files_processed}")

    if args.dry_run:
        print(f"Files that would be changed: {total_files_changed}")
        print(f"Lines that would be changed: {total_lines_changed}")
    else:
        print(f"Files changed: {total_files_changed}")
        print(f"Lines changed: {total_lines_changed}")


if __name__ == "__main__":
    main()
