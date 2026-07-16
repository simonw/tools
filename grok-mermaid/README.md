# grok-mermaid

Build artefacts and rebuild script for [`../grok-mermaid.html`](../grok-mermaid.html),
an in-browser playground that renders [Mermaid](https://mermaid.js.org/)
diagram source as terminal-style Unicode box-drawing art.

## Where the code comes from

The renderer is `src/mermaid.rs`, copied from
[xai-org/grok-build](https://github.com/xai-org/grok-build)
(`crates/codegen/xai-grok-markdown/src/mermaid.rs`) — the component the Grok
CLI uses to draw ```` ```mermaid ```` blocks in the terminal. It supports
`graph`/`flowchart` (including subgraphs), `sequenceDiagram`,
`stateDiagram`, `classDiagram` and `erDiagram`; anything else falls back to
the raw source in a framed box.

That file is **used unmodified except for two import lines**: upstream it
imports `Style`/`Modifier`/`Span`/`Line` from [ratatui](https://ratatui.rs/),
and here those imports point at `src/shim.rs`, a ~70-line stand-in for just
those four types. Instead of terminal colors, the shim's `Style` carries a
CSS class name, which is how the playground colors the output. Everything
else — parsing, layout, edge routing, the box-drawing canvas — runs
exactly as upstream wrote it, including its 148 unit tests (`cargo test`).

`src/lib.rs` adds safe `render_plain`/`render_html` entry points and a tiny
wasm-bindgen-free FFI (`wasm_alloc` / `wasm_render_html` / `wasm_result_ptr`)
for the browser page.

## License

`src/mermaid.rs` is copyright 2023-2026 SpaceXAI, licensed under the
[Apache License 2.0](LICENSE) (the upstream repository's license, included
here in full). The wrapper code in this directory is under the same license.

## Building the WASM module

```bash
rustup target add wasm32-unknown-unknown
./build_wasm.sh
```

This compiles the crate with `cargo build --release --target
wasm32-unknown-unknown` and copies the result to `../grok-mermaid.wasm`
(~163 KB), which `../grok-mermaid.html` fetches at load time.

Install [binaryen](https://github.com/WebAssembly/binaryen)'s `wasm-opt`
before building: besides shrinking the module, it rewrites the overlong
`call_indirect` table-index LEB that wasm-ld emits (a reference-types
encoding) into the canonical MVP form. Without that rewrite the module is
rejected by WebAssembly engines lacking reference-types support (such as
Safari before 15) with a "zero byte expected" parse error.

## FFI protocol

The module deliberately avoids wasm-bindgen so the build needs nothing but
cargo. JavaScript talks to it like this:

1. `wasm_alloc(len)` → pointer; write UTF-8 mermaid source there.
2. `wasm_render_html(ptr, len, max_width)` → renders (freeing the input
   buffer) and returns the byte length of the HTML result. `max_width <= 0`
   means unlimited columns.
3. Read that many bytes at `wasm_result_ptr()` and UTF-8 decode. The HTML
   is the box art with each styled run wrapped in `<span class="...">`:
   `b` border, `n` node text, `e` edge, `el` edge label, `t` title, plus
   `i` for italic.
