#!/usr/bin/env python3
"""Generate screenshots of all HTML tools using shot-scraper."""
import hashlib
import subprocess
import sys
from pathlib import Path


def get_file_hash(file_path):
    """Calculate SHA256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def generate_screenshots():
    """Generate screenshots for all HTML tools."""
    # Create screenshots directory if it doesn't exist
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    # Find all HTML files except index.html and colophon.html
    html_files = [
        f for f in Path(".").glob("*.html")
        if f.name not in ["index.html", "colophon.html"]
    ]

    print(f"Found {len(html_files)} HTML files to screenshot")

    # Check if shot-scraper is available
    try:
        subprocess.run(
            ["shot-scraper", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: shot-scraper is not installed or not available")
        print("Install it with: pip install shot-scraper")
        sys.exit(1)

    for html_file in sorted(html_files):
        # Calculate hash of the file content
        file_hash = get_file_hash(html_file)

        # Generate screenshot filename
        screenshot_name = f"{html_file.stem}.{file_hash}.jpeg"
        screenshot_path = screenshots_dir / screenshot_name

        # Skip if screenshot already exists
        if screenshot_path.exists():
            print(f"Screenshot already exists: {screenshot_name}")
            continue

        print(f"Generating screenshot for {html_file.name}...")

        # Generate the screenshot using shot-scraper
        try:
            subprocess.run(
                [
                    "shot-scraper",
                    str(html_file),
                    "--width", "1024",
                    "--height", "768",
                    "--quality", "90",
                    "--output", str(screenshot_path)
                ],
                check=True,
                capture_output=True
            )
            print(f"  Created: {screenshot_name}")
        except subprocess.CalledProcessError as e:
            print(f"  Error generating screenshot for {html_file.name}: {e}")
            print(f"  stdout: {e.stdout.decode()}")
            print(f"  stderr: {e.stderr.decode()}")

    print(f"\nScreenshot generation complete!")


if __name__ == "__main__":
    generate_screenshots()
