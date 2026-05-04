#!/usr/bin/env python3
"""Combine src/commands/ar*.json from a Redis checkout into one file.

Usage: build_commands.py [REDIS_SRC_DIR] [OUT_PATH]

Defaults:
  REDIS_SRC_DIR = /tmp/redis
  OUT_PATH      = redis-array-playground/ar-commands.json

The result is a sorted dict keyed by uppercase command name (ARSET, ARGET, ...)
with the original definition under each key, plus a top-level "_meta" block
recording where each file came from. The playground HTML reads this JSON
directly to drive its dynamic forms and inline documentation.
"""

import json
import pathlib
import sys
from datetime import datetime, timezone

DEFAULT_REDIS_DIR = pathlib.Path("/tmp/redis")
DEFAULT_OUT = pathlib.Path(__file__).parent / "ar-commands.json"


def main(argv: list[str]) -> int:
    redis_dir = pathlib.Path(argv[1]) if len(argv) > 1 else DEFAULT_REDIS_DIR
    out_path = pathlib.Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT

    cmd_dir = redis_dir / "src" / "commands"
    if not cmd_dir.is_dir():
        print(f"error: {cmd_dir} does not exist", file=sys.stderr)
        return 1

    # ar*.json but not e.g. arena.json from a different repo state
    files = sorted(p for p in cmd_dir.glob("ar*.json"))
    if not files:
        print(f"error: no ar*.json under {cmd_dir}", file=sys.stderr)
        return 1

    combined: dict = {}
    sources: list[dict] = []
    for path in files:
        with path.open() as f:
            payload = json.load(f)
        if not isinstance(payload, dict) or len(payload) != 1:
            print(f"warning: skipping unexpected shape in {path}", file=sys.stderr)
            continue
        name, body = next(iter(payload.items()))
        combined[name.upper()] = body
        sources.append({"command": name.upper(), "file": path.name})

    out = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "github.com/antirez/redis@array",
            "files": sources,
            "count": len(combined),
        },
        "commands": dict(sorted(combined.items())),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(combined)} commands to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
