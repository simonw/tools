#!/bin/bash
# Rebuilds sqlite3.mjs + sqlite3.wasm in this directory: SQLite's official WebAssembly
# build (the ESM flavour of the oo1/capi JavaScript API) with the sparqlite SPARQL
# extension, written in Rust, statically linked in and registered as an auto-extension.
#
# Needs: git, curl, unzip, a C compiler (SQLite's configure builds jimsh), rustup,
# and wasm-strip from wabt (apt install wabt). Emscripten is installed into the work
# directory if emcc is not already on the PATH.
#
# Usage: ./build_wasm.sh             (work files go in ./build, which is gitignored)
#        WORK=/tmp/x ./build_wasm.sh
set -euo pipefail

# simonw/research, branch claude/sqlite-sparql-rust, directory sqlite-sparql-rust/
RESEARCH_REPO=https://github.com/simonw/research
RESEARCH_BRANCH=claude/sqlite-sparql-rust
RESEARCH_COMMIT=70cbd8b2d84ddef7fe68ba980611cb9be6cf38ba
SQLITE_URL=https://sqlite.org/2026/sqlite-src-3540000.zip
SQLITE_SHA256=8847659821e0c5116bd14a94644c82ba932b2d9a05ac81af2e34af814aad7c58
EMSDK_VERSION=6.0.12

HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-$HERE/build}
mkdir -p "$WORK"
WORK=$(cd "$WORK" && pwd)

command -v wasm-strip >/dev/null || { echo "wasm-strip not found: install wabt" >&2; exit 1; }

# --- Emscripten -------------------------------------------------------------------
if ! command -v emcc >/dev/null; then
    if [ ! -d "$WORK/emsdk" ]; then
        git clone --depth 1 https://github.com/emscripten-core/emsdk.git "$WORK/emsdk"
    fi
    "$WORK/emsdk/emsdk" install "$EMSDK_VERSION"
    "$WORK/emsdk/emsdk" activate "$EMSDK_VERSION"
    # shellcheck disable=SC1091
    source "$WORK/emsdk/emsdk_env.sh"
fi
EMSDK_DIR=$(cd "$(dirname "$(command -v emcc)")/../.." && pwd)
echo "emcc: $(emcc --version | head -1)"

# --- sparqlite (Rust) -> libsparqlite_wasm.a ---------------------------------------
SRC=$WORK/research
if [ ! -d "$SRC/.git" ]; then
    git init -q "$SRC"
    git -C "$SRC" remote add origin "$RESEARCH_REPO"
    git -C "$SRC" sparse-checkout set sqlite-sparql-rust
fi
if ! git -C "$SRC" cat-file -e "$RESEARCH_COMMIT^{commit}" 2>/dev/null; then
    git -C "$SRC" fetch -q --depth 1 origin "$RESEARCH_COMMIT" \
        || git -C "$SRC" fetch -q --depth 50 origin "$RESEARCH_BRANCH"
fi
git -C "$SRC" checkout -q --force "$RESEARCH_COMMIT"
git -C "$SRC" clean -q -fdx -e target -e '**/target'
# WebAssembly has no threads: parse large RDF inputs inline instead of on a parser
# thread, and skip the baseline engine's timeout watchdog thread.
git -C "$SRC" apply "$HERE/wasm-threads.patch"

CRATE=$SRC/sqlite-sparql-rust/wasm
mkdir -p "$CRATE/src"
cp "$HERE/crate/Cargo.toml" "$CRATE/Cargo.toml"
cp "$HERE/crate/src/lib.rs" "$CRATE/src/lib.rs"
cp "$SRC/sqlite-sparql-rust/ext/Cargo.lock" "$CRATE/Cargo.lock"   # same pinned dependencies
# rust-toolchain.toml in sqlite-sparql-rust/ selects the Rust version.
(cd "$CRATE" && rustup target add wasm32-unknown-emscripten \
    && cargo build --release --target wasm32-unknown-emscripten)
LIB=$CRATE/target/wasm32-unknown-emscripten/release/libsparqlite_wasm.a

# --- SQLite canonical source tree -> ext/wasm build ---------------------------------
ZIP=$WORK/$(basename "$SQLITE_URL")
[ -f "$ZIP" ] || curl -sSfL -o "$ZIP" "$SQLITE_URL"
echo "$SQLITE_SHA256  $ZIP" | sha256sum -c -
SQLITE=$WORK/$(basename "$SQLITE_URL" .zip)
if [ ! -f "$SQLITE/sqlite3.c" ]; then
    rm -rf "$SQLITE"
    (cd "$WORK" && unzip -q "$ZIP")
    (cd "$SQLITE" && ./configure --with-emsdk="$EMSDK_DIR" >/dev/null && make sqlite3.c >/dev/null)
fi

# SQLite's makefile runs `wasm-opt --all-features`; Binaryen 133+ then writes imports in
# the not-yet-standard "compact imports" encoding, which browsers reject ("unknown import
# kind 0x7f"). This wrapper turns that feature back off.
cat > "$WORK/wasm-opt-wrapper.sh" <<EOF
#!/bin/sh
exec "$EMSDK_DIR/upstream/bin/wasm-opt" "\$@" --disable-compact-imports
EOF
chmod +x "$WORK/wasm-opt-wrapper.sh"

# sqlite3_wasm_extra_init.c is SQLite's documented hook for adding C code to sqlite3.wasm;
# its value goes straight onto the emcc command line, so the Rust archive rides along.
# emcc.flags.esm is appended after the default flags:
#   -fwasm-exceptions  Rust's emscripten target unwinds panics with WASM exceptions
#   -sSTACK_SIZE=4MB   the default 512KB is tight for the recursive SPARQL parser/planner
cd "$SQLITE/ext/wasm"
rm -rf jswasm/esm
make b-esm emcc_opt=-Oz \
    bin.wasm-opt="$WORK/wasm-opt-wrapper.sh" \
    sqlite3_wasm_extra_init.c="$HERE/sqlite3_wasm_extra_init.c $LIB" \
    emcc.flags.esm="-fwasm-exceptions -sSTACK_SIZE=4MB"
make t-stripccomments >/dev/null

# Same comment stripping as SQLite's `make dist` (keeps the license headers).
../../tool/stripccomments -k -k < jswasm/esm/sqlite3.mjs > "$HERE/sqlite3.mjs"
cp jswasm/esm/sqlite3.wasm "$HERE/sqlite3.wasm"
ls -l "$HERE/sqlite3.mjs" "$HERE/sqlite3.wasm"
