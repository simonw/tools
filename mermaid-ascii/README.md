# mermaid-ascii

Build artefacts and rebuild script for [`../mermaid-ascii.html`](../mermaid-ascii.html),
an in-browser playground that renders [Mermaid](https://mermaid.js.org/)
diagram source as ASCII / Unicode box-drawing art using
[AlexanderGrooff/mermaid-ascii](https://github.com/AlexanderGrooff/mermaid-ascii),
a Go library, compiled to WebAssembly.

## Where the code comes from

The renderer is the upstream `cmd` and `pkg` packages from
[AlexanderGrooff/mermaid-ascii](https://github.com/AlexanderGrooff/mermaid-ascii),
used unmodified at pinned commit `a4f2321`. It supports `graph`/`flowchart`
diagrams (labeled edges, `A --> B & C` fan-out, subgraphs, `<br>` multi-line
labels, `classDef ... color:#hex` text coloring) and `sequenceDiagram`
(participants with aliases, solid/dotted arrows, self-messages, notes, and
`alt`/`opt`/`loop`/`par`/`critical`/`break` fragments).

Upstream ships as a cobra CLI with an optional gin web server. For the WASM
build, `build_wasm.sh` clones the repo, deletes those two entry points
(`main.go`, `cmd/root.go`, `cmd/web.go` — nothing else imports cobra or gin)
and adds two files from this directory:

- **`wasm_globals.go`** → `cmd/wasm_globals.go`: re-declares the four package
  globals that lived in the deleted `cmd/root.go`.
- **`main.go`** → `wasm/main.go`: the WASM entry point. It exports one
  JavaScript function via `syscall/js`:

  ```js
  renderMermaidAscii(source, {
      ascii: false,      // true = pure ASCII, false = Unicode box drawing
      styleType: "html", // "html" wraps classDef-colored text in spans
      paddingX: 5,       // horizontal space between nodes
      paddingY: 5,       // vertical space between nodes
      borderPadding: 1,  // padding between node text and its border
  })
  // -> {output: "..."} or {error: "..."}
  ```

  Renderer panics are caught with `recover()` and returned as errors, so a
  bad input can't kill the Go runtime living in the page.

**Security note:** with `styleType: "html"` the library wraps colored runes in
`<span style='color: ...'>` without escaping anything, so the page never
assigns the result to `innerHTML` — it tokenizes the output with a strict
regex and rebuilds the spans via `textContent` / `style.color`.

## Building the WASM module

```bash
./build_wasm.sh
```

Requires Go (the module declares 1.21; built with 1.24), `git`, and
optionally [binaryen](https://github.com/WebAssembly/binaryen)'s `wasm-opt`.
The script writes `../mermaid-ascii.wasm` (~3.7 MB — a standard Go runtime is
included; it gzips to ~1.1 MB) and refreshes `wasm_exec.js`, Go's JS loader
glue, which must match the compiler version used.

## Files

- `build_wasm.sh` — clone upstream, strip CLI/web entry points, build.
- `main.go`, `wasm_globals.go` — the two files added to the build tree.
- `wasm_exec.js` — Go's official JS/wasm runtime glue (BSD-3, from the Go
  distribution), loaded by `../mermaid-ascii.html`.
- `LICENSE` — upstream's MIT license.

## License

[AlexanderGrooff/mermaid-ascii](https://github.com/AlexanderGrooff/mermaid-ascii)
is copyright (c) 2023 Alexander Grooff, [MIT licensed](LICENSE). The wrapper
code in this directory is under the same license. `wasm_exec.js` is copyright
The Go Authors (BSD-3-Clause).
