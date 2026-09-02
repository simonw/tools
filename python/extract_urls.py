#!/usr/bin/env python3

"""Extract potential URLs from a local file or an HTTP(S) resource."""

import argparse
import re
import urllib.error
import urllib.request
from pathlib import Path


URL_RE = re.compile(
    r"""
    (?<![@\w.-])
    (?:
        https?://[^\s<>"']+
        |
        (?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+
        [a-z]{2,63}
        (?::[0-9]{1,5})?
        (?:[/?\#][^\s<>"']*)?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

TRAILING_PUNCTUATION = ".,;:!?"
CLOSING_DELIMITERS = {")": "(", "]": "[", "}": "{"}


def read_source(source: str) -> str:
    """Return text read from an HTTP(S) URL or a local file."""
    if source.lower().startswith(("http://", "https://")):
        request = urllib.request.Request(
            source, headers={"User-Agent": "extract_urls.py/1.0"}
        )
        with urllib.request.urlopen(request) as response:
            encoding = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(encoding, errors="replace")

    return Path(source).read_text(encoding="utf-8", errors="replace")


def clean_url(url: str) -> str:
    """Remove sentence punctuation and unmatched closing delimiters."""
    url = url.rstrip(TRAILING_PUNCTUATION)
    while url and url[-1] in CLOSING_DELIMITERS:
        closing = url[-1]
        opening = CLOSING_DELIMITERS[closing]
        if url.count(closing) <= url.count(opening):
            break
        url = url[:-1].rstrip(TRAILING_PUNCTUATION)
    return url


def extract_urls(text: str):
    """Yield potential URLs from text in their original order."""
    for match in URL_RE.finditer(text):
        url = clean_url(match.group(0))
        if url:
            yield url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract potential URLs from a URL or local text file."
    )
    parser.add_argument(
        "source",
        help="an http:// or https:// URL, or the path to a local file",
    )
    args = parser.parse_args()

    try:
        text = read_source(args.source)
    except (OSError, UnicodeError, urllib.error.URLError) as ex:
        parser.error(f"could not read {args.source!r}: {ex}")

    for url in extract_urls(text):
        print(url)


if __name__ == "__main__":
    main()
