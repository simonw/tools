# sqlite-sparql

Build artefacts and rebuild script for [`../sqlite-sparql.html`](../sqlite-sparql.html), a
browser playground for **sparqlite**: a SQLite extension written in Rust that stores RDF in
SQLite tables and runs SPARQL 1.1 queries and updates from SQL (`sparql_query()`,
`sparql_rows()`, `sparql_update()`, `sparql_load()`, the `sparql_view` virtual table, …).

sparqlite lives in [simonw/research, branch `claude/sqlite-sparql-rust`, directory
`sqlite-sparql-rust/`](https://github.com/simonw/research/tree/claude/sqlite-sparql-rust/sqlite-sparql-rust)
(pinned commit `70cbd8b`). Natively it is a loadable extension (`libsparqlite.so`). Here it is
compiled to WebAssembly and **statically linked into SQLite's official WASM build** (SQLite
3.54.0, the `sqlite3.mjs` ES module with the usual `oo1` / `capi` JavaScript API), and registered
as an auto-extension, so every database opened from JavaScript has the `sparql_*` functions.

```js
import sqlite3InitModule from './sqlite-sparql/sqlite3.mjs';
const sqlite3 = await sqlite3InitModule();
const db = new sqlite3.oo1.DB(':memory:');
db.selectValue("SELECT sparql_load('<http://ex/a> <http://ex/b> \"c\" .')");          // 1
db.selectValue("SELECT sparql_query('SELECT * WHERE { ?s ?p ?o }', 'csv')");           // "o,p,s\r\nc,..."
```

## Files

| File | What it is |
|---|---|
| `sqlite3.mjs`, `sqlite3.wasm` | The build: SQLite 3.54.0 + sparqlite (4.4 MB wasm, 1.7 MB gzipped; 440 KB JS, 94 KB gzipped) |
| `worker.mjs` | The playground's Web Worker: owns the database, runs requests, keeps snapshots |
| `data/` | The sparqlite tutorial dataset: `languages.ttl` (real, from Wikipedia infoboxes), `survey.trig` and `job_postings.sql` (fictional) |
| `build_wasm.sh` | Rebuilds `sqlite3.mjs` / `sqlite3.wasm` from pinned sources |
| `crate/` | A small Rust crate that builds sparqlite as a static library for `wasm32-unknown-emscripten` |
| `sqlite3_wasm_extra_init.c` | Registers the extension with `sqlite3_auto_extension()` when SQLite initializes |
| `wasm-threads.patch` | Two changes to sparqlite for a platform without threads (below) |

## How the build works

`build_wasm.sh` does everything from scratch (installing Emscripten 6.0.12 into `build/` if `emcc`
is not on the `PATH`). It needs git, curl, unzip, a C compiler, rustup and `wasm-strip` (wabt).
A clean run takes a few minutes.

1. **sparqlite → `libsparqlite_wasm.a`.** Sparse-checks out `sqlite-sparql-rust/` at the pinned
   commit, applies `wasm-threads.patch`, copies `crate/` in as `sqlite-sparql-rust/wasm/` and runs
   `cargo build --release --target wasm32-unknown-emscripten` (Rust 1.97, from the project's
   `rust-toolchain.toml`). The crate depends on `sq-api` and on rusqlite *without* the
   `loadable_extension` feature, so the Rust code calls `sqlite3_*` directly instead of through
   the extension API table (which is `NULL` in SQLite's WASM build: it is compiled with
   `SQLITE_OMIT_LOAD_EXTENSION`). Its one export, `sqlite3_sparqlite_init`, wraps
   `Connection::from_handle` + `sq_api::register`, catching panics.
2. **SQLite → `sqlite3.mjs` + `sqlite3.wasm`.** Downloads the canonical source tree
   (`sqlite-src-3540000.zip`, checksum verified), runs `./configure --with-emsdk=…`, then
   `make b-esm` in `ext/wasm` with:
   - `sqlite3_wasm_extra_init.c="…/sqlite3_wasm_extra_init.c …/libsparqlite_wasm.a"`. This is
     SQLite's documented hook for adding C code to `sqlite3.wasm`, and its value goes straight onto
     the `emcc` command line, so the Rust archive is linked in with it, no makefile patching.
   - `emcc.flags.esm="-fwasm-exceptions -sSTACK_SIZE=4MB"`. Rust's emscripten target unwinds
     panics with WebAssembly exception handling, so the link needs `-fwasm-exceptions` (without it:
     `undefined symbol: __cpp_exception`). sparqlite catches panics at every FFI boundary and
     reports them as SQL errors, and that works in the browser too. The 4 MB stack (default
     512 KB) is headroom for the recursive SPARQL parser and planner.
   - `emcc_opt=-Oz`, which is SQLite's shipping configuration. Rust is built with
     `opt-level = "s"`. Together they save 500 KB gzipped against `-O2` / `opt-level = 3`.
     `opt-level = "s"` benchmarked as fast as `3`, and `-Oz` was 0 to 15% slower.
   - `bin.wasm-opt=<wrapper>`: SQLite's makefile post-processes the module with
     `wasm-opt --all-features`, and the Binaryen in current Emscripten (version 133) then writes
     the import section in the not-yet-standard *compact imports* encoding, which browsers reject
     with `WebAssembly.instantiate(): unknown import kind 0x7f`. The wrapper appends
     `--disable-compact-imports`. This affects any SQLite WASM build with a current emsdk, not just
     this one.
3. **JS.** `sqlite3.mjs` goes through SQLite's own `stripccomments -k -k`, as `make dist` does
   (833 KB → 440 KB).

### `wasm-threads.patch`

WebAssembly without SharedArrayBuffer has no threads, and sparqlite spawns two:

- `sq-sqlite/src/loader.rs`: RDF inputs over 1 MiB are parsed on a producer thread. In WASM
  `std::thread::scope` panics with "failed to spawn thread" (the load fails with
  `unwinding panic`). The patch makes WASM builds always parse inline.
- `sq-api/src/query.rs`: with `engine=sql` and `timeout_ms`, a watchdog thread calls
  `sqlite3_interrupt()` to stop a single long `sqlite3_step()`. In WASM the patch skips the
  watchdog. The deadline is still checked between 1,024-row batches, and the native engine
  (the default) checks its own deadline as it works, so `timeout_ms` still works. It just can't
  interrupt a single long step of the SQL-translation engine.

## Checks

On top of the playground's Playwright tests (`tests/test_sqlite_sparql.py`, which run every one
of the page's 68 examples), the build was checked in headless Chromium for:

- loading a 1.7 MB N-Triples file (20,000 triples, the pipelined path natively): 366 ms;
- `timeout_ms` with both engines, and `max_memory_mb`;
- `RAND()`, `UUID()`, `STRUUID()`, `NOW()`, `BNODE()`, MD5 / SHA-256, REGEX, language tags;
- every nesting shape (parentheses, groups, OPTIONAL, sub-selects, UNION chains, operator
  chains, property-path sequences) at the deepest level sparqlite's nesting limiter accepts:
  no stack overflow;
- a deliberate panic inside a SQL function (in a test build): reported as a SQL error, and the
  connection keeps working;
- **the direct B-tree page reader**: on a database file in Emscripten's in-memory filesystem,
  sparqlite reads SQLite's index pages through the VFS itself (`btree_pages_read`, 0 fallbacks).
  Scan-heavy queries ran 2 to 3 times faster than on `:memory:`, which is why the playground
  uses a file;
- `sqlite3_js_db_export()` → `sqlite3_deserialize()` / reopening: the store survives a round trip
  (so a database built in the browser opens with the native extension, and vice versa).

In the browser, 120,000 triples load in about 1 second, and most of the playground's examples
run in 1 to 10 ms.

## Known issues

- The SPARQL parser (spargebra 0.4.7, upstream) takes exponential time on nested
  `!( !( … ) )`: about 1 second at depth 20, natively as well as in WASM. In the playground the
  query runs in a worker, so the page stays responsive and **Stop** restarts the worker from a
  snapshot of the database.
- Error messages for syntax errors include the parser's full "expected one of …" list. The
  playground shortens it.
- `sparql_load_file()` and `LOAD <file:…>` (off unless `allow_files` is set) can only see
  Emscripten's in-memory filesystem.

## Browser support

Needs module workers and WebAssembly exception handling (the legacy `try`/`catch` encoding, not
`exnref`): Chrome/Edge 95+, Firefox 114+, Safari 15.2+.
