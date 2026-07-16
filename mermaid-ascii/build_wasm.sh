#!/bin/bash
# Rebuild ../mermaid-ascii.wasm, the WebAssembly module behind
# ../mermaid-ascii.html.
#
# The renderer is https://github.com/AlexanderGrooff/mermaid-ascii (MIT),
# compiled unmodified with the standard Go toolchain (GOOS=js GOARCH=wasm) —
# except that the cobra CLI and gin web-server entry points are removed,
# replaced by the two small files in this directory:
#
#   main.go          wasm/main.go in the build tree; exports
#                    renderMermaidAscii() to JavaScript via syscall/js
#   wasm_globals.go  cmd/wasm_globals.go in the build tree; re-declares the
#                    handful of package globals that lived in cmd/root.go
#
# Requires: go >= 1.21 (module targets 1.21; tested with 1.24), git, and
# optionally wasm-opt (binaryen) which shaves ~6% off the module size.
#
# Usage: ./build_wasm.sh

set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)

UPSTREAM=https://github.com/AlexanderGrooff/mermaid-ascii
# Pinned upstream commit this build is known to work against.
PIN=a4f23212201cbd62b5a8707b7502b281bb18543f

BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT

git clone "$UPSTREAM" "$BUILD/src"
git -C "$BUILD/src" checkout "$PIN"
cd "$BUILD/src"

# Strip the CLI (cobra) and web server (gin) so neither ends up in the
# module, along with tests and their fixtures. Only cmd/root.go and
# cmd/web.go import those dependencies; the layout/drawing code in cmd/
# and pkg/ is untouched.
rm main.go cmd/root.go cmd/web.go
rm -rf cmd/*_test.go cmd/testdata pkg/*/*_test.go pkg/diagram/testutil

cp "$HERE/wasm_globals.go" cmd/wasm_globals.go
mkdir wasm
cp "$HERE/main.go" wasm/main.go

go mod tidy
GOOS=js GOARCH=wasm go build -trimpath -ldflags="-s -w" \
    -o mermaid-ascii.wasm ./wasm

if command -v wasm-opt >/dev/null; then
    wasm-opt -Oz \
        --enable-bulk-memory --enable-nontrapping-float-to-int \
        mermaid-ascii.wasm -o mermaid-ascii.opt.wasm
    mv mermaid-ascii.opt.wasm mermaid-ascii.wasm
else
    echo "NOTE: wasm-opt not found; skipping size optimization." >&2
fi

cp mermaid-ascii.wasm "$HERE/../mermaid-ascii.wasm"
echo "Wrote $HERE/../mermaid-ascii.wasm ($(wc -c < "$HERE/../mermaid-ascii.wasm") bytes)"

# The page also needs Go's JS/wasm glue, which must match the compiler used.
cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" "$HERE/wasm_exec.js"
echo "Wrote $HERE/wasm_exec.js (from $(go version))"
