#!/bin/bash
# Rebuild redis-array.js (the SINGLE_FILE WASM bundle).
#
# This compiles the *unmodified* sparsearray.c, t_array.c, util.c, sds.c,
# fast_float_strtod.c and fpconv_dtoa.c from a checkout of the
# antirez:array branch, plus the bundled TRE regex library
# (deps/tre/lib/*.c), against a small Redis-runtime shim that lives in
# src-stub/. Net effect: every AR* command runs the actual Redis C — no
# JavaScript reimplementation of iteration, predicates, aggregation, etc.
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

# Redis sources (unmodified)
mkdir -p "$BUILD/redis-src"
cp "$REDIS_DIR/src/sparsearray.c"        "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sparsearray.h"        "$BUILD/redis-src/"
cp "$REDIS_DIR/src/t_array.c"            "$BUILD/redis-src/"
cp "$REDIS_DIR/src/util.c"               "$BUILD/redis-src/"
cp "$REDIS_DIR/src/util.h"               "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sds.c"                "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sds.h"                "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sdsalloc.h"           "$BUILD/redis-src/"
cp "$REDIS_DIR/src/fast_float_strtod.c"  "$BUILD/redis-src/"
cp "$REDIS_DIR/src/fast_float_strtod.h"  "$BUILD/redis-src/"
cp "$REDIS_DIR/src/zmalloc.h"            "$BUILD/redis-src/" 2>/dev/null || true
cp "$REDIS_DIR/src/redisassert.h"        "$BUILD/redis-src/"
cp "$REDIS_DIR/src/fmacros.h"            "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sha256.c"             "$BUILD/redis-src/"
cp "$REDIS_DIR/src/sha256.h"             "$BUILD/redis-src/"
cp "$REDIS_DIR/src/config.h"             "$BUILD/redis-src/"
cp "$REDIS_DIR/src/solarisfixes.h"       "$BUILD/redis-src/" 2>/dev/null || true
# fpconv (vendored)
cp "$REDIS_DIR/deps/fpconv/fpconv_dtoa.c"      "$BUILD/redis-src/"
cp "$REDIS_DIR/deps/fpconv/fpconv_dtoa.h"      "$BUILD/redis-src/"
cp "$REDIS_DIR/deps/fpconv/fpconv_powers.h"    "$BUILD/redis-src/"
# TRE (vendored). t_array.c uses a relative `#include
# "../deps/tre/local_includes/tre.h"`, so we recreate that exact layout
# instead of flattening everything into one directory.
mkdir -p "$BUILD/deps/tre/local_includes" "$BUILD/deps/tre/lib"
cp "$REDIS_DIR/deps/tre/local_includes"/*  "$BUILD/deps/tre/local_includes/"
cp "$REDIS_DIR/deps/tre/lib"/*             "$BUILD/deps/tre/lib/"
ln -s "$BUILD/redis-src" "$BUILD/src"

# Our shim
cp "$HERE/src-stub/server.h"      "$BUILD/redis-src/"
cp "$HERE/src-stub/redis_stubs.c" "$BUILD/redis-src/"
cp "$HERE/src-stub/wasm_entry.c"  "$BUILD/redis-src/"

REDIS_C_SOURCES=(
    "$BUILD/redis-src/sparsearray.c"
    "$BUILD/redis-src/t_array.c"
    "$BUILD/redis-src/util.c"
    "$BUILD/redis-src/sds.c"
    "$BUILD/redis-src/sha256.c"
    "$BUILD/redis-src/fast_float_strtod.c"
    "$BUILD/redis-src/fpconv_dtoa.c"
    "$BUILD/redis-src/redis_stubs.c"
    "$BUILD/redis-src/wasm_entry.c"
)

TRE_C_SOURCES=(
    "$BUILD/deps/tre/lib/regcomp.c"
    "$BUILD/deps/tre/lib/regerror.c"
    "$BUILD/deps/tre/lib/regexec.c"
    "$BUILD/deps/tre/lib/tre-ast.c"
    "$BUILD/deps/tre/lib/tre-compile.c"
    "$BUILD/deps/tre/lib/tre-filter.c"
    "$BUILD/deps/tre/lib/tre-match-backtrack.c"
    "$BUILD/deps/tre/lib/tre-match-parallel.c"
    "$BUILD/deps/tre/lib/tre-mem.c"
    "$BUILD/deps/tre/lib/tre-parse.c"
    "$BUILD/deps/tre/lib/tre-stack.c"
    "$BUILD/deps/tre/lib/xmalloc.c"
)

EXPORTS='[
"_wasm_init","_wasm_dispatch","_wasm_reply_buf_ptr","_wasm_reply_buf_len",
"_wasm_drop_key","_wasm_flush_all","_wasm_list_keys","_wasm_key_stats",
"_malloc","_free"]'
RUNTIME='["ccall","cwrap","HEAPU8","HEAP32","stringToUTF8","UTF8ToString","getValue","setValue"]'

emcc -O2 -DNDEBUG \
    -I"$BUILD/redis-src" \
    -I"$BUILD/deps/tre/local_includes" \
    -I"$BUILD/deps/tre/lib" \
    -DTRE_REGEX_T_FIELD=value -DHAVE_CONFIG_H=0 \
    -Wno-incompatible-pointer-types-discards-qualifiers \
    -Wno-implicit-function-declaration \
    "${REDIS_C_SOURCES[@]}" "${TRE_C_SOURCES[@]}" \
    -o "$HERE/redis-array.js" \
    -s MODULARIZE=1 \
    -s EXPORT_NAME=createRedisArrayModule \
    -s ENVIRONMENT=web,worker,node \
    -s SINGLE_FILE=1 \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s INITIAL_MEMORY=8MB \
    -s STACK_SIZE=2MB \
    -s "EXPORTED_RUNTIME_METHODS=$RUNTIME" \
    -s "EXPORTED_FUNCTIONS=$EXPORTS"

echo "Wrote $HERE/redis-array.js ($(wc -c < "$HERE/redis-array.js") bytes)"
