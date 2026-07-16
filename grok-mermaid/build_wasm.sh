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

# wasm-opt (binaryen) is strongly recommended, and not just for size: wasm-ld
# emits the call_indirect table-index immediate as an overlong LEB — a
# reference-types encoding that engines without that feature (e.g. Safari
# before 15) reject with "zero byte expected". wasm-opt rewrites it to the
# canonical MVP encoding. The --enable flags describe the features the raw
# LLVM output uses so wasm-opt can parse it.
if command -v wasm-opt >/dev/null; then
    wasm-opt -Oz \
        --enable-mutable-globals --enable-sign-ext \
        --enable-bulk-memory --enable-nontrapping-float-to-int \
        --enable-reference-types \
        "$WASM" -o "$WASM.opt" && mv "$WASM.opt" "$WASM"
else
    echo "WARNING: wasm-opt not found; output keeps LLVM's overlong" >&2
    echo "call_indirect encoding, which needs reference-types support" >&2
    echo "and is rejected by some WebAssembly engines." >&2
fi

cp "$WASM" "$HERE/../grok-mermaid.wasm"
echo "Wrote $HERE/../grok-mermaid.wasm ($(wc -c < "$HERE/../grok-mermaid.wasm") bytes)"
