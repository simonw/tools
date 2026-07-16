//! Minimal stand-ins for the `ratatui` style/text types that `mermaid.rs`
//! uses (`Style`, `Modifier`, `Span`, `Line`), so the renderer compiles
//! without pulling in ratatui. Instead of terminal colors, a `Style` carries
//! an optional CSS class name; `lib.rs` turns styled lines into HTML spans.

use std::borrow::Cow;

#[derive(Clone, Copy, PartialEq, Eq, Default, Debug)]
pub struct Modifier(u8);

impl Modifier {
    pub const ITALIC: Modifier = Modifier(1);
}

#[derive(Clone, Copy, PartialEq, Eq, Default, Debug)]
pub struct Style {
    pub class: Option<&'static str>,
    modifiers: u8,
}

impl Style {
    /// A style tagged with a CSS class name.
    pub const fn class(name: &'static str) -> Self {
        Style {
            class: Some(name),
            modifiers: 0,
        }
    }

    pub fn add_modifier(mut self, modifier: Modifier) -> Self {
        self.modifiers |= modifier.0;
        self
    }

    pub fn is_italic(&self) -> bool {
        self.modifiers & Modifier::ITALIC.0 != 0
    }
}

#[derive(Clone, PartialEq, Debug)]
pub struct Span<'a> {
    pub content: Cow<'a, str>,
    pub style: Style,
}

impl<'a> Span<'a> {
    pub fn styled<T: Into<Cow<'a, str>>>(content: T, style: Style) -> Self {
        Span {
            content: content.into(),
            style,
        }
    }
}

#[derive(Clone, PartialEq, Debug, Default)]
pub struct Line<'a> {
    pub spans: Vec<Span<'a>>,
}

impl<'a> From<Vec<Span<'a>>> for Line<'a> {
    fn from(spans: Vec<Span<'a>>) -> Self {
        Line { spans }
    }
}

impl<'a> From<Span<'a>> for Line<'a> {
    fn from(span: Span<'a>) -> Self {
        Line { spans: vec![span] }
    }
}
