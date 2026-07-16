#!/bin/bash
# Rebuild ../grok-mermaid.wasm, the WebAssembly module behind
# ../grok-mermaid.html.
#
# The renderer itself is src/mermaid.rs, copied unmodified (except for two
# import lines — see the file header) from
# https://github.com/xai-org/grok-build
# crates/codegen/xai-grok-markdown/src/mermaid.rs (Apache-2.0).
#
# Requires a Rust toolchain with the wasm32-unknown-unknown target:
#   rustup target add wasm32-unknown-unknown
#
# Usage: ./build_wasm.sh

set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)

cargo build --manifest-path "$HERE/Cargo.toml" \
    --release --target wasm32-unknown-unknown

WASM="$HERE/target/wasm32-unknown-unknown/release/grok_mermaid.wasm"

# Optional: shrink further if wasm-opt (binaryen) is installed.
if command -v wasm-opt >/dev/null; then
    wasm-opt -Oz "$WASM" -o "$WASM.opt" && mv "$WASM.opt" "$WASM"
fi

cp "$WASM" "$HERE/../grok-mermaid.wasm"
echo "Wrote $HERE/../grok-mermaid.wasm ($(wc -c < "$HERE/../grok-mermaid.wasm") bytes)"
