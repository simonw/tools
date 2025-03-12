# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "click",
# ]
# ///

import sys
import re
from dataclasses import dataclass
from typing import List, Union, Tuple
import click


@dataclass
class Text:
    """Represents non-matching text"""

    content: str


@dataclass
class Match:
    """Represents matching text that should be highlighted"""

    content: str


@dataclass
class Ellipsis:
    """Represents ... for truncated content"""

    pass


def find_matches(
    text: str, terms: List[str], context: int = 30
) -> List[Union[Text, Match, Ellipsis]]:
    """
    Find all matches of the given terms in the text, with surrounding context.
    Returns a list of Text, Match, and Ellipsis objects.
    """
    if not terms:
        return [Text(text)]

    # Create pattern that matches any of the terms
    pattern = "|".join(re.escape(term) for term in terms)
    regex = re.compile(pattern, re.IGNORECASE)

    # Find all matches with their positions
    matches = list(regex.finditer(text))
    if not matches:
        return [Text(text)]

    # Create segments with context
    segments: List[Tuple[int, int]] = []  # List of (start, end) for context regions
    match_positions: List[Tuple[int, int]] = (
        []
    )  # List of (start, end) for actual matches

    for match in matches:
        start, end = match.span()
        match_positions.append((start, end))
        context_start = max(0, start - context)
        context_end = min(len(text), end + context)
        segments.append((context_start, context_end))

    # Merge overlapping context segments
    merged_segments = []
    current = segments[0]
    for next_seg in segments[1:]:
        if next_seg[0] <= current[1]:
            # Segments overlap, merge them
            current = (current[0], max(current[1], next_seg[1]))
        else:
            merged_segments.append(current)
            current = next_seg
    merged_segments.append(current)

    # Convert segments to result objects
    result = []
    last_end = 0

    for seg_start, seg_end in merged_segments:
        # Add ellipsis if there's a gap
        if seg_start > last_end:
            if last_end > 0:  # Only add if not at the start
                result.append(Ellipsis())

        # Find all matches within this segment
        segment_matches = [
            (s, e) for s, e in match_positions if s >= seg_start and e <= seg_end
        ]

        # Add content with proper highlighting
        pos = seg_start
        for match_start, match_end in segment_matches:
            # Add text before match
            if match_start > pos:
                result.append(Text(text[pos:match_start]))
            # Add match
            result.append(Match(text[match_start:match_end]))
            pos = match_end

        # Add remaining text in segment
        if pos < seg_end:
            result.append(Text(text[pos:seg_end]))

        last_end = seg_end

    # Add final ellipsis if we're not at the end
    if last_end < len(text):
        result.append(Ellipsis())

    return result


@click.command()
@click.argument("terms", nargs=-1, required=True)
@click.option(
    "-c", "--context", default=30, help="Number of context characters around matches"
)
def main(terms: List[str], context: int):
    """Search for terms in stdin and output colored matches with context."""
    text = sys.stdin.read()
    results = find_matches(text, terms, context)

    # ANSI color codes
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"

    # Convert results to colored output
    for item in results:
        if isinstance(item, Text):
            print(item.content, end="")
        elif isinstance(item, Match):
            print(f"{RED}{item.content}{END}", end="")
        elif isinstance(item, Ellipsis):
            print(f"{YELLOW}...{END}", end="")
    print()  # Final newline


if __name__ == "__main__":
    main()
