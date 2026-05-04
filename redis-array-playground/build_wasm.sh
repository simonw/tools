#!/bin/bash
# Rebuild redis-array.js (the SINGLE_FILE WASM bundle) from sparsearray.c on
# the antirez:array branch of redis/redis. Requires emscripten + a checkout
# of redis at REDIS_DIR (defaults to /tmp/redis on the array branch).
#
# Usage: ./build_wasm.sh [REDIS_DIR]

set -euo pipefail

REDIS_DIR=${1:-/tmp/redis}
HERE=$(cd "$(dirname "$0")" && pwd)

if ! command -v emcc >/dev/null; then
    echo "error: emcc not on PATH; activate emsdk first" >&2
    exit 1
fi
if [ ! -f "$REDIS_DIR/src/sparsearray.c" ]; then
    echo "error: $REDIS_DIR/src/sparsearray.c not found." >&2
    echo "Clone redis/redis and switch to the antirez:array branch first:" >&2
    echo "  git clone https://github.com/redis/redis $REDIS_DIR" >&2
    echo "  git -C $REDIS_DIR remote add antirez https://github.com/antirez/redis" >&2
    echo "  git -C $REDIS_DIR fetch antirez array" >&2
    echo "  git -C $REDIS_DIR checkout -b array antirez/array" >&2
    exit 1
fi

BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
cp "$REDIS_DIR/src/sparsearray.c" "$BUILD/"
cp "$REDIS_DIR/src/sparsearray.h" "$BUILD/"
cp "$HERE/wasm_wrapper.c" "$BUILD/"
cp "$HERE/server.h" "$BUILD/"

EXPORTS='["_wasm_init","_wasm_ar_new","_wasm_ar_free","_wasm_ar_count","_wasm_ar_len","_wasm_ar_set","_wasm_ar_promote_dense","_wasm_ar_del","_wasm_ar_delete_range","_wasm_ar_truncate","_wasm_ar_get","_wasm_ar_get_buf","_wasm_ar_value_len","_wasm_ar_next_index","_wasm_ar_alloc_size","_wasm_ar_num_slices","_wasm_ar_slice_size","_wasm_ar_get_insert_idx","_wasm_ar_set_insert_idx","_malloc","_free"]'
RUNTIME='["ccall","cwrap","HEAPU8","HEAP32","stringToUTF8","UTF8ToString","getValue","setValue"]'

emcc -O2 -DNDEBUG -I"$BUILD" \
    "$BUILD/wasm_wrapper.c" "$BUILD/sparsearray.c" \
    -o "$HERE/redis-array.js" \
    -s MODULARIZE=1 \
    -s EXPORT_NAME=createRedisArrayModule \
    -s ENVIRONMENT=web \
    -s SINGLE_FILE=1 \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s "EXPORTED_RUNTIME_METHODS=$RUNTIME" \
    -s "EXPORTED_FUNCTIONS=$EXPORTS"

echo "Wrote $HERE/redis-array.js ($(wc -c < "$HERE/redis-array.js") bytes)"
