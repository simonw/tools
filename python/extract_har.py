# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import json
import zipfile
from pathlib import Path
import click
import mimetypes
from urllib.parse import urlparse


def get_extension_for_mimetype(mimetype):
    """Get the most common file extension for a given MIME type."""
    ext = mimetypes.guess_extension(mimetype)
    if ext:
        return ext

    # Fallback mappings for common types
    fallbacks = {
        "application/json": ".json",
        "image/svg+xml": ".svg",
        "text/html": ".html",
        "text/css": ".css",
        "application/javascript": ".js",
    }
    return fallbacks.get(mimetype, ".bin")


def extract_path_from_url(url):
    """Convert a URL into a filesystem path, preserving the path structure."""
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")

    # Handle empty paths
    if not path:
        path = "index"

    # Remove trailing slashes
    path = path.rstrip("/")

    return path


@click.command()
@click.argument("harzip", type=click.Path(exists=True))
@click.argument("mimetypes", nargs=-1, required=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default=".",
    help="Output directory for extracted files",
)
@click.option(
    "--paths",
    is_flag=True,
    help="Use URL paths for filenames instead of original names",
)
@click.option(
    "--pretty-json",
    is_flag=True,
    help="Pretty print JSON files with 2-space indentation",
)
def extract_har(harzip, mimetypes, output, paths, pretty_json):
    """Extract files of specified MIME types from a HAR archive."""
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(harzip) as zf:
        # Read the HAR JSON file
        try:
            har_content = json.loads(zf.read("har.har"))
        except KeyError:
            click.echo("Error: har.har not found in archive", err=True)
            return
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in har.har", err=True)
            return

        # Process each entry
        for entry in har_content.get("log", {}).get("entries", []):
            response = entry.get("response", {})
            content = response.get("content", {})

            # Check if this entry matches our MIME type filter
            if content.get("mimeType") not in mimetypes:
                continue

            # Get the file reference and URL
            file_ref = content.get("_file")
            if not file_ref:
                continue

            request_url = entry.get("request", {}).get("url", "")

            try:
                # Extract the file
                file_content = zf.read(file_ref)

                if paths:
                    # Use URL path for filename
                    path = extract_path_from_url(request_url)
                    # Add appropriate extension if not present
                    if not Path(path).suffix:
                        path += get_extension_for_mimetype(content["mimeType"])
                    outpath = output_dir / path
                else:
                    # Use original filename
                    outpath = output_dir / file_ref

                # Ensure parent directories exist
                outpath.parent.mkdir(parents=True, exist_ok=True)

                # Handle JSON pretty printing if requested
                if pretty_json and content["mimeType"] == "application/json":
                    try:
                        json_data = json.loads(file_content)
                        file_content = json.dumps(json_data, indent=2).encode("utf-8")
                    except json.JSONDecodeError:
                        click.echo(
                            f"Warning: Could not pretty print {outpath} - invalid JSON",
                            err=True,
                        )

                # Write the file
                outpath.write_bytes(file_content)
                click.echo(f"Extracted: {outpath}")

            except KeyError:
                click.echo(f"Warning: File {file_ref} not found in archive", err=True)
                continue


if __name__ == "__main__":
    extract_har()
