//! grok-mermaid: render Mermaid diagram source as Unicode box-drawing art.
//!
//! The actual renderer lives in `mermaid.rs`, copied (Apache-2.0) from
//! <https://github.com/xai-org/grok-build>
//! (`crates/codegen/xai-grok-markdown/src/mermaid.rs`) — see LICENSE and
//! README.md in this directory. This file adds:
//!
//! - `render_plain` / `render_html`: safe Rust entry points. The HTML flavor
//!   wraps each styled run in `<span class="...">` using the class names
//!   `b` (border), `n` (node text), `e` (edge), `el` (edge label),
//!   `t` (title), plus `i` for italic, so a page can color the art the way
//!   the original TUI does.
//! - `wasm_alloc` / `wasm_render_html` / `wasm_result_ptr`: a tiny
//!   wasm-bindgen-free FFI surface for the browser playground
//!   (`../grok-mermaid.html`), built by `build_wasm.sh`.

mod mermaid;
mod shim;

use std::alloc::Layout;
use std::cell::RefCell;

use mermaid::MermaidStyles;
use shim::Style;

fn styles() -> MermaidStyles {
    MermaidStyles {
        border: Style::class("b"),
        node_text: Style::class("n"),
        edge: Style::class("e"),
        edge_label: Style::class("el"),
        title: Style::class("t"),
    }
}

/// Render mermaid source to plain (uncolored) box-drawing text, or `None`
/// for blank input. `max_width` bounds the diagram width in display columns;
/// diagrams that cannot fit fall back to the framed raw source.
pub fn render_plain(src: &str, max_width: Option<usize>) -> Option<String> {
    mermaid::render(src, &styles(), max_width).map(|art| art.plain_lines.join("\n"))
}

/// Render mermaid source to HTML: box-drawing text with each styled run
/// wrapped in a classed `<span>` (see module docs for the class names).
pub fn render_html(src: &str, max_width: Option<usize>) -> Option<String> {
    let art = mermaid::render(src, &styles(), max_width)?;
    let mut out = String::new();
    for line in &art.styled_lines {
        for span in &line.spans {
            if span.content.is_empty() {
                continue;
            }
            let text = escape_html(&span.content);
            match span.style.class {
                None => out.push_str(&text),
                Some(class) => {
                    out.push_str("<span class=\"");
                    out.push_str(class);
                    if span.style.is_italic() {
                        out.push_str(" i");
                    }
                    out.push_str("\">");
                    out.push_str(&text);
                    out.push_str("</span>");
                }
            }
        }
        out.push('\n');
    }
    Some(out)
}

fn escape_html(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            _ => out.push(c),
        }
    }
    out
}

// ---------------------------------------------------------------------------
// WASM FFI. Deliberately wasm-bindgen-free so the build needs nothing beyond
// `cargo build --target wasm32-unknown-unknown`. Protocol:
//
//   1. JS calls `wasm_alloc(len)` and writes UTF-8 mermaid source at the
//      returned pointer.
//   2. JS calls `wasm_render_html(ptr, len, max_width)` (which frees that
//      input buffer); it returns the byte length of the rendered HTML.
//   3. JS reads that many bytes from `wasm_result_ptr()` and UTF-8 decodes.
//
// `max_width <= 0` means unlimited. Blank input renders to an empty string.
// ---------------------------------------------------------------------------

thread_local! {
    static RESULT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

fn buf_layout(len: usize) -> Layout {
    Layout::from_size_align(len.max(1), 1).unwrap()
}

/// Allocate `len` bytes for passing input in. Ownership passes to the caller;
/// `wasm_render_html` takes it back and frees it.
#[unsafe(no_mangle)]
pub extern "C" fn wasm_alloc(len: usize) -> *mut u8 {
    // SAFETY: buf_layout never has zero size.
    unsafe { std::alloc::alloc(buf_layout(len)) }
}

/// Render the UTF-8 mermaid source at `ptr..ptr+len` (a buffer obtained from
/// `wasm_alloc(len)`, freed by this call) and return the byte length of the
/// resulting HTML, readable at `wasm_result_ptr()`.
///
/// # Safety
/// `ptr` must come from `wasm_alloc(len)` with this exact `len`, fully
/// initialized, and must not be used again after this call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wasm_render_html(ptr: *mut u8, len: usize, max_width: i32) -> usize {
    // SAFETY: caller contract — ptr came from wasm_alloc(len), is initialized,
    // and is not reused after this call.
    let src = unsafe {
        let src = String::from_utf8_lossy(std::slice::from_raw_parts(ptr, len)).into_owned();
        std::alloc::dealloc(ptr, buf_layout(len));
        src
    };
    let max_width = usize::try_from(max_width).ok().filter(|&w| w > 0);
    let html = render_html(&src, max_width).unwrap_or_default();
    RESULT.with(|r| {
        let mut r = r.borrow_mut();
        *r = html.into_bytes();
        r.len()
    })
}

/// Pointer to the result of the most recent `wasm_render_html` call. Only
/// valid until the next call.
#[unsafe(no_mangle)]
pub extern "C" fn wasm_result_ptr() -> *const u8 {
    RESULT.with(|r| r.borrow().as_ptr())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn renders_plain_flowchart() {
        let out = render_plain("graph TD\n  A[Start] --> B[End]", Some(80)).unwrap();
        assert!(out.contains("Start"), "missing node label:\n{out}");
        assert!(out.contains('▼'), "missing arrowhead:\n{out}");
    }

    #[test]
    fn renders_classed_html() {
        let out = render_html("graph LR\n  A[a & b] -->|go| C{c}", Some(120)).unwrap();
        assert!(out.contains("<span class=\"b\">"), "missing border span:\n{out}");
        assert!(out.contains("<span class=\"el\">"), "missing edge label span:\n{out}");
        assert!(out.contains("a &amp; b"), "unescaped ampersand:\n{out}");
    }

    #[test]
    fn blank_input_is_none() {
        assert!(render_html("  \n ", None).is_none());
    }
}
