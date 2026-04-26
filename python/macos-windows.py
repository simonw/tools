# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyobjc-framework-Quartz",
# ]
# ///

import argparse
import Quartz


def n(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_window_list():
    return Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )


def main():
    parser = argparse.ArgumentParser(
        description="List visible macOS windows using CoreGraphics / Quartz."
    )
    parser.add_argument(
        "--min-width",
        type=float,
        default=100,
        help="Only show windows at least this wide. Default: 100",
    )
    parser.add_argument(
        "--min-height",
        type=float,
        default=100,
        help="Only show windows at least this tall. Default: 100",
    )
    parser.add_argument(
        "--hud",
        action="store_true",
        help="Show likely HUD/overlay windows: non-zero layer, modest size.",
    )
    parser.add_argument(
        "--owner",
        help="Case-insensitive owner/app name filter, e.g. --owner Transmit",
    )
    args = parser.parse_args()

    windows = get_window_list() or []

    rows = []
    for w in windows:
        owner = w.get("kCGWindowOwnerName", "")
        name = w.get("kCGWindowName", "")
        pid = w.get("kCGWindowOwnerPID", "")
        layer = int(w.get("kCGWindowLayer", 0))
        alpha = n(w.get("kCGWindowAlpha"), 1)

        bounds = w.get("kCGWindowBounds", {})
        x = n(bounds.get("X"))
        y = n(bounds.get("Y"))
        width = n(bounds.get("Width"))
        height = n(bounds.get("Height"))

        if width < args.min_width or height < args.min_height:
            continue

        if args.owner and args.owner.lower() not in owner.lower():
            continue

        if args.hud:
            # Most ordinary app windows are layer 0. HUDs/overlays often use
            # a higher layer and are relatively small.
            if layer == 0:
                continue
            if width > 600 or height > 600:
                continue

        rows.append((layer, owner, pid, alpha, x, y, width, height, name))

    rows.sort(key=lambda r: (r[0], r[1].lower(), r[4], r[5]), reverse=True)

    for layer, owner, pid, alpha, x, y, width, height, name in rows:
        print(
            f"{owner!r:30} "
            f"pid={pid!s:>7} "
            f"layer={layer:<4} "
            f"alpha={alpha:.2f} "
            f"bounds={{x:{x:.0f} y:{y:.0f} w:{width:.0f} h:{height:.0f}}} "
            f"name={name!r}"
        )


if __name__ == "__main__":
    main()
