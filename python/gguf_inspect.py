#!/usr/bin/env python3
"""
gguf_inspect.py  –  Dump ALL metadata key/value pairs from a GGUF file.

 • Default output: YAML (each value in a literal block scalar).
 • --json              Pretty-print JSON instead.
 • --exclude PREFIX    Skip keys that begin with PREFIX. May be repeated.

Example:
    ./gguf_dump_meta.py llama.gguf                            # YAML
    ./gguf_dump_meta.py --json llama.gguf                     # JSON
    ./gguf_dump_meta.py --exclude tokenizer.ggml. llama.gguf  # YAML, filtered
"""

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List

# ──────────────────────────────────────────────────────
# gguf helpers
# ──────────────────────────────────────────────────────

_PRIM_FMT = {
    0: "B",
    1: "b",
    2: "H",
    3: "h",
    4: "I",
    5: "i",
    6: "f",
    7: "B",  # BOOL
    10: "Q",
    11: "q",
    12: "d",
}
_PRIM_SIZE = {k: struct.calcsize(v) for k, v in _PRIM_FMT.items()}

STRING, ARRAY = 8, 9


def _read(fmt: str, fh):
    size = struct.calcsize(fmt)
    data = fh.read(size)
    if len(data) != size:
        raise EOFError("unexpected EOF")
    return struct.unpack("<" + fmt, data)


def _read_string(fh) -> str:
    (length,) = _read("Q", fh)
    raw = fh.read(length)
    if len(raw) != length:
        raise EOFError("unexpected EOF in string")
    return raw.decode("utf-8", errors="replace")


def _read_scalar(typ: int, fh):
    (val,) = _read(_PRIM_FMT[typ], fh)
    return bool(val) if typ == 7 else val


def _read_array(elem_type: int, count: int, fh) -> List[Any]:
    if elem_type == STRING:
        return [_read_string(fh) for _ in range(count)]

    elem_size = _PRIM_SIZE[elem_type]
    data = fh.read(elem_size * count)
    if len(data) != elem_size * count:
        raise EOFError("unexpected EOF in array")
    fmt = f"<{count}{_PRIM_FMT[elem_type]}"
    out = list(struct.unpack(fmt, data))
    if elem_type == 7:
        out = [bool(v) for v in out]
    return out


def extract_metadata(path: Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    with path.open("rb") as fh:
        if fh.read(4) != b"GGUF":
            raise ValueError("not a GGUF file")
        (_version,) = _read("I", fh)
        _ntensors, n_kv = _read("QQ", fh)

        for _ in range(n_kv):
            key = _read_string(fh)
            (val_type,) = _read("I", fh)

            if val_type == STRING:
                value = _read_string(fh)
            elif val_type == ARRAY:
                (elem_type,) = _read("I", fh)
                (count,) = _read("Q", fh)
                value = _read_array(elem_type, count, fh)
            else:
                value = _read_scalar(val_type, fh)

            meta[key] = value
    return meta


# ──────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────


def dump_yaml(meta: Dict[str, Any]) -> None:
    for key in sorted(meta):
        print(f"{key}: |")
        lines = json.dumps(meta[key], ensure_ascii=False, indent=2).splitlines()
        for ln in lines or [""]:
            print(f"  {ln}")
        print()  # blank line between keys


def dump_json(meta: Dict[str, Any]) -> None:
    print(json.dumps(meta, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────


def parse_args():
    p = argparse.ArgumentParser(
        description="Dump metadata key/value pairs from a GGUF file."
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="output as pretty-printed JSON instead of YAML",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PREFIX",
        help="exclude keys that start with PREFIX (can be given multiple times)",
    )
    p.add_argument("gguf", metavar="MODEL.GGUF", help="path to GGUF file")
    return p.parse_args()


def should_include(key: str, prefixes: List[str]) -> bool:
    return not any(key.startswith(pref) for pref in prefixes)


def main():
    args = parse_args()

    path = Path(args.gguf)
    if not path.is_file():
        sys.exit(f"File not found: {path}")

    meta = extract_metadata(path)
    if args.exclude:
        meta = {k: v for k, v in meta.items() if should_include(k, args.exclude)}

    if args.json:
        dump_json(meta)
    else:
        dump_yaml(meta)


if __name__ == "__main__":
    main()
