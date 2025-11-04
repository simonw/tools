# /// script
# dependencies = [
#   "rich",
#   "rich-pixels",
#   "pillow",
# ]
# ///
"""
Show an image inline in the terminal using rich-pixels, resized to fit the
current terminal width *and* height (no upscaling).

Usage:
  python show_image_cli.py path/to/image.png
"""

from argparse import ArgumentParser
from pathlib import Path

from PIL import Image
from rich.console import Console
from rich_pixels import Pixels


def fit_to_terminal(
    im: Image.Image, cols: int, rows: int, margin_rows: int = 0
) -> tuple[int, int]:
    """Return (new_w, new_h) in *image pixels* to fit terminal size.

    rich-pixels uses half-block characters, so 1 terminal row ≈ 2 image rows.
    We avoid upscaling and keep aspect ratio.
    """
    max_w_px = max(1, cols)
    usable_rows = max(1, rows - max(0, margin_rows))
    max_h_px = max(2, usable_rows * 2)

    # Prevent upscaling by capping to 1.0
    width_scale = min(1.0, max_w_px / im.width)
    height_scale = min(1.0, max_h_px / im.height)
    scale = min(width_scale, height_scale)

    new_w = max(1, int(im.width * scale))
    new_h = max(2, int(im.height * scale))

    # Ensure even height for half-block rendering and clamp to max_h_px
    if new_h % 2:
        new_h -= 1
    new_h = min(new_h, max_h_px - (max_h_px % 2))

    return new_w, new_h


def main() -> None:
    parser = ArgumentParser(
        description="Display an image inline in the terminal using rich-pixels, "
        "resized to fit current terminal width and height."
    )
    parser.add_argument("image", type=Path, help="Path to the image file")
    parser.add_argument(
        "--margin-rows",
        type=int,
        default=0,
        help="Rows to reserve at the bottom (e.g., for prompts). Default: 0",
    )
    parser.add_argument(
        "--lanczos",
        action="store_true",
        help="Use high-quality downscaling (Lanczos). Default is NEAREST (crisp pixel art).",
    )
    args = parser.parse_args()

    console = Console()
    term_cols = console.size.width
    term_rows = console.size.height

    if not args.image.exists():
        console.print(f"[red]File not found:[/red] {args.image}")
        raise SystemExit(1)

    with Image.open(args.image) as im:
        new_w, new_h = fit_to_terminal(im, term_cols, term_rows, args.margin_rows)
        resample = Image.LANCZOS if args.lanczos else Image.NEAREST
        im_resized = im.resize((new_w, new_h), resample)
        pixels = Pixels.from_image(im_resized)

    console.print(pixels)


if __name__ == "__main__":
    main()
