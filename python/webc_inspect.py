# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cbor2"
# ]
# ///
"""
webc_inspect.py

Inspect Wasmer WebC archives (.webc) and print useful summary information.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import cbor2


def human_bytes(num: int) -> str:
    """Return a human-readable byte count."""
    step = 1024.0
    units = ["bytes", "KiB", "MiB", "GiB", "TiB"]
    size = float(num)
    for unit in units:
        if size < step or unit == units[-1]:
            if unit == "bytes":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= step
    return f"{size:.2f} PiB"


def read_header(blob: bytes) -> Dict[str, Any]:
    if len(blob) < 9:
        raise ValueError("File is too small to be a WebC archive")
    if not blob.startswith(b"\x00webc"):
        raise ValueError("Missing WebC magic header")
    version = blob[1:8].decode("ascii", "replace")
    return {
        "version": version,
        "raw": blob[:17],
    }


def locate_cbor_map(
    blob: bytes, required_keys: Iterable[str], *, search_limit: Optional[int] = None
) -> Tuple[int, Dict[str, Any]]:
    """Scan `blob` for a CBOR map that contains the required keys."""
    if search_limit is None:
        search_limit = len(blob)
    search_limit = min(search_limit, len(blob))
    required = tuple(required_keys)
    for offset in range(search_limit):
        initial = blob[offset]
        if 0xA0 <= initial <= 0xBF:  # definite length map (major type 5)
            try:
                obj = cbor2.loads(blob[offset:])
            except Exception:
                continue
            if isinstance(obj, dict) and all(key in obj for key in required):
                return offset, obj
    raise ValueError(
        f"Failed to locate CBOR map containing keys: {', '.join(required)}"
    )


def read_span(blob: bytes, span: Dict[str, Any]) -> bytes:
    start = span.get("start")
    length = span.get("len")
    if not isinstance(start, int) or not isinstance(length, int):
        raise ValueError("Invalid span metadata")
    end = start + length
    if end > len(blob):
        raise ValueError("Span exceeds file size")
    return blob[start:end]


def format_checksum(entry: Optional[Dict[str, Any]]) -> str:
    if not entry:
        return "(none)"
    tag = entry.get("tag", "")
    value = entry.get("value")
    if isinstance(value, bytes):
        hex_value = value.hex()
        b64_value = base64.b64encode(value).decode("ascii")
        return f"{tag} hex={hex_value} base64={b64_value}"
    return f"{tag} value={value!r}"


def format_timestamp(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts).isoformat()


def describe_manifest(manifest: Dict[str, Any]) -> None:
    print("Manifest:")
    entrypoint = manifest.get("entrypoint")
    if entrypoint is not None:
        print(f"  Entrypoint: {entrypoint}")
    package = manifest.get("package", {})
    fs_mounts = package.get("fs", [])
    if fs_mounts:
        print("  File system mounts:")
        for mount in fs_mounts:
            vol = mount.get("volume_name")
            mount_path = mount.get("mount_path")
            src = mount.get("from")
            details = f"{vol} -> {mount_path}"
            if src:
                details += f" (from {src})"
            print(f"    - {details}")
    commands = manifest.get("commands", {})
    if commands:
        print("  Commands:")
        for name, info in commands.items():
            runner = info.get("runner")
            print(f"    - {name}")
            if runner:
                print(f"      runner: {runner}")
            annotations = info.get("annotations", {})
            atom_ann = annotations.get("atom", {})
            atom_name = atom_ann.get("name") or atom_ann.get("atom")
            if atom_name:
                print(f"      atom: {atom_name}")
            wasi = annotations.get("wasi", {})
            wasi_atom = wasi.get("atom")
            if wasi_atom and wasi_atom != atom_name:
                print(f"      wasi atom: {wasi_atom}")
            env = wasi.get("env") or info.get("env")
            if env:
                print("      env:")
                for item in env:
                    print(f"        - {item}")
    atoms = manifest.get("atoms", {})
    if atoms:
        print("  Atoms:")
        for name, info in atoms.items():
            print(f"    - {name}")
            kind = info.get("kind")
            if kind:
                print(f"      kind: {kind}")
            signature = info.get("signature")
            if signature:
                print(f"      signature: {signature}")
            annotations = info.get("annotations", {})
            wasm = annotations.get("wasm", {})
            features = wasm.get("features", [])
            if features:
                feat_list = ", ".join(features)
                print(f"      wasm features: {feat_list}")


def describe_volumes(root: Dict[str, Any], blob: bytes) -> None:
    volumes = root.get("volumes", {})
    if not volumes:
        return
    print("Volumes:")
    for name, meta in volumes.items():
        span = meta.get("span", {})
        checksum = meta.get("checksum")
        start = span.get("start")
        length = span.get("len")
        length_text = human_bytes(length) if isinstance(length, int) else "unknown"
        print(f"  - {name}")
        if isinstance(start, int):
            print(f"    span: start={start} len={length} ({length_text})")
        print(f"    checksum: {format_checksum(checksum)}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Wasmer WebC archive")
    parser.add_argument("archive", help="Path to the .webc archive (or cache blob)")
    parser.add_argument(
        "--max-root-scan",
        type=int,
        default=1 << 20,
        help="Number of initial bytes to scan when locating the root CBOR map",
    )
    args = parser.parse_args(argv)

    path = Path(args.archive)
    if not path.is_file():
        print(f"error: {path} is not a file", file=sys.stderr)
        return 1

    data = path.read_bytes()
    header = read_header(data)
    try:
        root_offset, root = locate_cbor_map(
            data, ["manifest", "volumes", "signature"], search_limit=args.max_root_scan
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stat = path.stat()
    print(f"Archive: {path}")
    print(f"Size: {stat.st_size} bytes ({human_bytes(stat.st_size)})")
    print(f"Modified: {format_timestamp(stat.st_mtime)}")
    print(f"WebC version: {header['version']}")
    print(f"Root CBOR offset: {root_offset}")

    manifest_meta = root.get("manifest", {})
    print(f"Manifest checksum: {format_checksum(manifest_meta.get('checksum'))}")

    manifest = None
    span = manifest_meta.get("span")
    if isinstance(span, dict):
        try:
            manifest_chunk = read_span(data, span)
            _, manifest = locate_cbor_map(
                manifest_chunk,
                ["package", "commands"],
                search_limit=len(manifest_chunk),
            )
        except ValueError as exc:
            print(f"warning: could not decode manifest content: {exc}")
        except Exception as exc:
            print(f"warning: manifest parsing failed: {exc}")
    else:
        print("warning: manifest span missing")

    atoms_meta = root.get("atoms")
    if isinstance(atoms_meta, dict):
        print(
            f"Atoms blob: span={atoms_meta.get('span')} checksum={format_checksum(atoms_meta.get('checksum'))}"
        )

    signature = root.get("signature")
    if isinstance(signature, dict):
        print(f"Signature: {signature.get('tag')} value={signature.get('value')!r}")

    if manifest:
        describe_manifest(manifest)

    describe_volumes(root, data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
