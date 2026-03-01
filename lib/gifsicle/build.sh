#!/bin/bash
# Build gifsicle as a WASM module using Emscripten
# Requires: emcc (Emscripten), autoconf, automake
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GIFSICLE_COMMIT="07f5c4c"
GIFSICLE_REPO="https://github.com/kohler/gifsicle.git"
BUILD_DIR="/tmp/gifsicle-wasm-build"

echo "==> Cleaning previous build..."
rm -rf "$BUILD_DIR"

echo "==> Cloning gifsicle..."
git clone "$GIFSICLE_REPO" "$BUILD_DIR"
cd "$BUILD_DIR"
git checkout "$GIFSICLE_COMMIT"

echo "==> Applying patches..."
patch -p1 < "$SCRIPT_DIR/gifsicle-wasm.patch"

echo "==> Running autoreconf..."
autoreconf -fi

echo "==> Configuring for Emscripten..."
emconfigure ./configure \
  --host=wasm32-unknown-emscripten \
  --disable-gifview \
  --disable-gifdiff \
  --disable-threads \
  --disable-simd

echo "==> Compiling with emcc..."
emcc -O2 -g0 \
  -DHAVE_CONFIG_H -I. -Iinclude \
  src/gifsicle.c src/clp.c src/fmalloc.c src/giffunc.c src/gifread.c \
  src/gifwrite.c src/gifunopt.c src/merge.c src/optimize.c src/quantize.c \
  src/support.c src/xform.c src/kcolor.c entry.c \
  -o gifsicle.js \
  -s MODULARIZE=1 \
  -s EXPORT_NAME="createGifsicle" \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s 'EXPORTED_FUNCTIONS=["_run_gifsicle","_malloc","_free"]' \
  -s 'EXPORTED_RUNTIME_METHODS=["FS","ccall","cwrap","allocateUTF8","UTF8ToString"]' \
  -s INVOKE_RUN=0 \
  -s FORCE_FILESYSTEM=1 \
  -lm

echo "==> Copying output..."
cp gifsicle.js "$SCRIPT_DIR/gifsicle.js"
cp gifsicle.wasm "$SCRIPT_DIR/gifsicle.wasm"

echo "==> Done! Output files:"
ls -la "$SCRIPT_DIR/gifsicle.js" "$SCRIPT_DIR/gifsicle.wasm"
