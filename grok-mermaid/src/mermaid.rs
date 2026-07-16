//! Self-contained terminal renderer for Mermaid diagrams.
//!
//! Renders `graph`/`flowchart`, `sequenceDiagram`, and `stateDiagram` blocks
//! as Unicode box-drawing art; unsupported diagram types fall back to the raw
//! source in a framed box.
//!
//! Copied from <https://github.com/xai-org/grok-build>
//! (`crates/codegen/xai-grok-markdown/src/mermaid.rs`), Apache-2.0 licensed,
//! Copyright 2023-2026 SpaceXAI. See the LICENSE file in this directory.
//! The only modification: the two `use ratatui::...` imports below now point
//! at `crate::shim`, a minimal local stand-in for the handful of `ratatui`
//! style/text types this module uses, so it compiles without ratatui.

use std::collections::HashMap;

use crate::shim::{Modifier, Style};
use crate::shim::{Line, Span};
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};

/// Theme-derived styles used when painting a diagram.
#[derive(Clone, Copy)]
pub(crate) struct MermaidStyles {
    pub border: Style,
    pub node_text: Style,
    pub edge: Style,
    pub edge_label: Style,
    pub title: Style,
}

/// Rendered diagram: styled lines for the TUI and plain lines for ANSI output.
pub(crate) struct MermaidArt {
    pub styled_lines: Vec<Line<'static>>,
    pub plain_lines: Vec<String>,
}

const MAX_LABEL: usize = 28;
const PAD: usize = 1;
const GAP_X: usize = 3;
const GAP_Y: usize = 2;
/// Node labels wrap to at most this many display columns per line, and at most
/// this many lines (overflow is truncated with an ellipsis).
const WRAP_WIDTH: usize = 24;
const MAX_LINES: usize = 4;
/// Identifier-boundary characters preferred as break points when a single word
/// is too wide to fit, so it is not sliced mid-segment.
/// Mirrors `TOKEN_BREAK_CHARS` in `third_party/mermaid-to-svg/src/text_wrap.rs`;
/// the two renderers are deliberately independent, so keep these two in sync.
const LABEL_BREAK_CHARS: [char; 4] = ['_', '-', '.', '/'];
/// Sentinel marking the trailing column of a wide glyph (never emitted).
const CONT: char = '\u{0}';
const MAX_NODES: usize = 128;
const MAX_EDGES: usize = 512;
const MAX_GROUPS: usize = 24;
const MAX_GROUP_DEPTH: usize = 6;
const MAX_CANVAS_CELLS: usize = 1 << 21;

fn char_width(c: char) -> usize {
    UnicodeWidthChar::width(c).unwrap_or(0)
}

#[derive(Clone, Copy)]
enum Oversize {
    Width,
    Cells,
}

/// Render a mermaid source block, or `None` for blank input.
pub(crate) fn render(
    src: &str,
    styles: &MermaidStyles,
    max_width: Option<usize>,
) -> Option<MermaidArt> {
    if src.trim().is_empty() {
        return None;
    }

    let outcome: Option<Result<MermaidArt, Oversize>> = parse_graph(src)
        .map(|graph| {
            if graph.groups.is_empty() {
                layout_flowchart(&graph, styles, max_width)
            } else {
                render_grouped(&graph, styles, max_width)
            }
        })
        .or_else(|| parse_state(src).map(|graph| layout_flowchart(&graph, styles, max_width)))
        .or_else(|| {
            parse_class(src).map(|(graph, infos)| render_class(&graph, &infos, styles, max_width))
        })
        .or_else(|| {
            parse_er(src).map(|(graph, infos)| render_class(&graph, &infos, styles, max_width))
        })
        .or_else(|| parse_sequence(src).map(|seq| layout_sequence(&seq, styles, max_width)));

    let too_wide = match outcome {
        Some(Ok(art)) => return Some(art),
        Some(Err(Oversize::Width)) => true,
        Some(Err(Oversize::Cells)) | None => false,
    };
    Some(fallback(src, styles, max_width, too_wide))
}

#[derive(Clone, Copy, PartialEq)]
enum Shape {
    Rect,
    Round,
    Diamond,
}

struct Node {
    label: String,
    shape: Shape,
}

#[derive(Clone, Copy, PartialEq, Debug)]
enum Head {
    None,
    Arrow,
    Circle,
    Cross,
    Triangle,
    DiamondFill,
    DiamondOpen,
}

#[derive(Clone, Copy, PartialEq)]
enum LineKind {
    Solid,
    Dotted,
    Thick,
}

struct Edge {
    from: usize,
    to: usize,
    label: Option<String>,
    head_to: Head,
    head_from: Head,
    line: LineKind,
}

#[derive(Clone, Copy, PartialEq)]
enum Dir {
    Down,
    Up,
    Right,
    Left,
}

struct Group {
    id: String,
    label: String,
    parent: Option<usize>,
}

struct Graph {
    nodes: Vec<Node>,
    edges: Vec<Edge>,
    index: HashMap<String, usize>,
    groups: Vec<Group>,
    node_group: Vec<Option<usize>>,
    cur_group: Option<usize>,
    over_cap: bool,
    dir: Dir,
}

impl Graph {
    fn node_index(&mut self, id: &str, label: Option<&str>, shape: Shape) -> Option<usize> {
        if let Some(&i) = self.index.get(id) {
            if let Some(label) = label {
                self.nodes[i].label = label.to_string();
                self.nodes[i].shape = shape;
            }
            return Some(i);
        }
        if self.nodes.len() >= MAX_NODES {
            self.over_cap = true;
            return None;
        }
        let label = label.unwrap_or(id).to_string();
        self.index.insert(id.to_string(), self.nodes.len());
        self.nodes.push(Node { label, shape });
        self.node_group.push(self.cur_group);
        Some(self.nodes.len() - 1)
    }

    fn node_label(&mut self, id: &str, label: &str) -> Option<usize> {
        if let Some(&i) = self.index.get(id) {
            self.nodes[i].label = label.to_string();
            return Some(i);
        }
        self.node_index(id, Some(label), Shape::Round)
    }
}

fn parse_graph(src: &str) -> Option<Graph> {
    let mut statements: Vec<String> = Vec::new();
    for raw_line in src.lines() {
        split_statements(raw_line, &mut statements);
    }

    let header = statements.first()?;
    let mut header_tokens = header.split_whitespace();
    let kind = header_tokens.next()?.to_ascii_lowercase();
    if kind != "graph" && kind != "flowchart" {
        return None;
    }
    let dir = match header_tokens
        .next()
        .unwrap_or("TB")
        .to_ascii_uppercase()
        .as_str()
    {
        "LR" => Dir::Right,
        "RL" => Dir::Left,
        "BT" => Dir::Up,
        _ => Dir::Down,
    };

    let mut graph = Graph {
        nodes: Vec::new(),
        edges: Vec::new(),
        index: HashMap::new(),
        groups: Vec::new(),
        node_group: Vec::new(),
        cur_group: None,
        over_cap: false,
        dir,
    };

    let mut stack: Vec<usize> = Vec::new();
    for st in &statements[1..] {
        let first_word = st.split_whitespace().next().unwrap_or("");
        match first_word.to_ascii_lowercase().as_str() {
            "subgraph" => {
                if graph.groups.len() >= MAX_GROUPS || stack.len() >= MAX_GROUP_DEPTH {
                    return None;
                }
                let (id, label) = parse_subgraph_decl(st["subgraph".len()..].trim());
                graph.groups.push(Group {
                    id,
                    label,
                    parent: stack.last().copied(),
                });
                stack.push(graph.groups.len() - 1);
                graph.cur_group = stack.last().copied();
                continue;
            }
            "end" => {
                stack.pop();
                graph.cur_group = stack.last().copied();
                continue;
            }
            "classdef" | "class" | "style" | "linkstyle" | "click" | "direction" => continue,
            _ => {}
        }
        parse_statement(st, &mut graph);
        if graph.over_cap {
            return None;
        }
    }

    if graph.nodes.is_empty() {
        return None;
    }
    Some(graph)
}

fn parse_subgraph_decl(rest: &str) -> (String, String) {
    if let Some(q) = rest.strip_prefix('"')
        && let Some((label, _)) = q.split_once('"')
    {
        return (label.to_string(), decode_html_entities(label));
    }
    if let Some(open) = rest.find('[') {
        let id = rest[..open].trim();
        let label = rest[open + 1..].trim_end_matches(']').trim();
        let label = clean_label(label);
        if !id.is_empty() && !label.is_empty() {
            return (id.to_string(), label);
        }
    }
    (rest.to_string(), rest.to_string())
}

fn split_statements(line: &str, out: &mut Vec<String>) {
    let mut cur = String::new();
    let mut in_quotes = false;
    let mut chars = line.chars().peekable();
    while let Some(c) = chars.next() {
        if in_quotes {
            if c == '"' {
                in_quotes = false;
            }
            cur.push(c);
        } else {
            match c {
                '"' => {
                    in_quotes = true;
                    cur.push(c);
                }
                '%' if chars.peek() == Some(&'%') => break,
                ';' => flush_statement(&mut cur, out),
                _ => cur.push(c),
            }
        }
    }
    flush_statement(&mut cur, out);
}

fn flush_statement(cur: &mut String, out: &mut Vec<String>) {
    let trimmed = cur.trim();
    if !trimmed.is_empty() {
        out.push(trimmed.to_string());
    }
    cur.clear();
}

fn parse_statement(st: &str, graph: &mut Graph) {
    let chars: Vec<char> = st.chars().collect();
    let mut i = 0;

    let Some((mut prev, ni)) = parse_node_group(&chars, i, graph) else {
        return;
    };
    i = ni;

    loop {
        i = skip_spaces(&chars, i);
        if i >= chars.len() {
            break;
        }
        let Some((left, right, line, label, ni)) = parse_link(&chars, i) else {
            break;
        };
        i = skip_spaces(&chars, ni);
        let Some((next, ni)) = parse_node_group(&chars, i, graph) else {
            break;
        };
        i = ni;
        for &f in &prev {
            for &t in &next {
                if graph.edges.len() >= MAX_EDGES {
                    graph.over_cap = true;
                    return;
                }
                let (from, to, head_to, head_from) = if left == Head::Arrow && right != Head::Arrow
                {
                    (t, f, Head::Arrow, right)
                } else {
                    (f, t, right, left)
                };
                graph.edges.push(Edge {
                    from,
                    to,
                    label: label.clone(),
                    head_to,
                    head_from,
                    line,
                });
            }
        }
        prev = next;
    }
}

fn parse_node_group(
    chars: &[char],
    start: usize,
    graph: &mut Graph,
) -> Option<(Vec<usize>, usize)> {
    let (first, mut i) = parse_node(chars, start, graph)?;
    let mut group = vec![first];
    loop {
        let j = skip_spaces(chars, i);
        if chars.get(j) != Some(&'&') {
            break;
        }
        let (next, k) = parse_node(chars, j + 1, graph)?;
        group.push(next);
        i = k;
    }
    Some((group, i))
}

fn skip_spaces(chars: &[char], mut i: usize) -> usize {
    while i < chars.len() && (chars[i] == ' ' || chars[i] == '\t') {
        i += 1;
    }
    i
}

fn is_id_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn parse_node(chars: &[char], start: usize, graph: &mut Graph) -> Option<(usize, usize)> {
    let mut i = skip_spaces(chars, start);
    let id_start = i;
    while i < chars.len() && is_id_char(chars[i]) {
        i += 1;
    }
    if i == id_start {
        return None;
    }
    let id: String = chars[id_start..i].iter().collect();

    let (shape, label, after) = match chars.get(i) {
        Some('[') => {
            if chars.get(i + 1) == Some(&'[') {
                read_shape(chars, i + 2, "]]", Shape::Rect)
            } else if chars.get(i + 1) == Some(&'(') {
                read_shape(chars, i + 2, ")]", Shape::Round)
            } else {
                read_shape(chars, i + 1, "]", Shape::Rect)
            }
        }
        Some('(') => {
            if chars.get(i + 1) == Some(&'(') {
                read_shape(chars, i + 2, "))", Shape::Round)
            } else if chars.get(i + 1) == Some(&'[') {
                read_shape(chars, i + 2, "])", Shape::Round)
            } else {
                read_shape(chars, i + 1, ")", Shape::Round)
            }
        }
        Some('{') => {
            if chars.get(i + 1) == Some(&'{') {
                read_shape(chars, i + 2, "}}", Shape::Diamond)
            } else {
                read_shape(chars, i + 1, "}", Shape::Diamond)
            }
        }
        Some('>') => read_shape(chars, i + 1, "]", Shape::Rect),
        _ => (None, None, i),
    };

    let shape = shape.unwrap_or(Shape::Rect);
    let label = label.as_deref();
    let idx = graph.node_index(&id, label, shape)?;
    Some((idx, after))
}

fn read_shape(
    chars: &[char],
    start: usize,
    closer: &str,
    shape: Shape,
) -> (Option<Shape>, Option<String>, usize) {
    let closer: Vec<char> = closer.chars().collect();
    let mut i = start;
    let mut text = String::new();
    let quoted = {
        let mut j = start;
        while matches!(chars.get(j), Some(' ') | Some('\t')) {
            j += 1;
        }
        chars.get(j) == Some(&'"')
    };
    let mut in_quotes = false;
    while i < chars.len() {
        let c = chars[i];
        if quoted && c == '"' {
            in_quotes = !in_quotes;
            text.push(c);
            i += 1;
            continue;
        }
        if !in_quotes && chars[i..].starts_with(closer.as_slice()) {
            let label = clean_label(&text);
            return (Some(shape), Some(label), i + closer.len());
        }
        text.push(c);
        i += 1;
    }
    (Some(shape), Some(clean_label(&text)), chars.len())
}

fn clean_label(raw: &str) -> String {
    let stripped = strip_html_tags(raw.trim());
    let trimmed = stripped.trim();
    let unquoted = trimmed
        .strip_prefix('"')
        .and_then(|t| t.strip_suffix('"'))
        .or_else(|| {
            trimmed
                .strip_prefix('\'')
                .and_then(|t| t.strip_suffix('\''))
        })
        .unwrap_or(trimmed)
        .trim();
    let text = if let Some(md) = unquoted.strip_prefix('`').and_then(|t| t.strip_suffix('`')) {
        strip_markdown(md.trim())
    } else {
        unquoted.to_string()
    };
    // Decode after tag-stripping so `<b>` is removed as markup while `&lt;b&gt;`
    // survives as a literal `<b>`; one decode at the single return covers both paths.
    decode_html_entities(&text)
}

const ENTITY_LOOKAHEAD: usize = 10;

// Label text decodes HTML entities once: via clean_label for bracketed labels, or explicitly at each direct-push sink.
fn decode_html_entities(s: &str) -> String {
    if !s.contains('&') {
        return s.to_string();
    }
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < chars.len() {
        if chars[i] != '&' {
            out.push(chars[i]);
            i += 1;
            continue;
        }
        // Scan window (includes the terminating `;`) so a stray `&` or over-long run stays literal.
        let hi = (i + 1 + ENTITY_LOOKAHEAD).min(chars.len());
        let semi = (i + 1..hi).find(|&j| chars[j] == ';');
        let decoded = semi.and_then(|j| {
            let body: String = chars[i + 1..j].iter().collect();
            decode_entity_body(&body).map(|c| (c, j))
        });
        match decoded {
            // Resume past the `;`; the single pass never re-scans emitted text, so
            // `&amp;lt;` decodes to the literal `&lt;` rather than to `<`.
            Some((c, j)) => {
                out.push(c);
                i = j + 1;
            }
            None => {
                out.push('&');
                i += 1;
            }
        }
    }
    out
}

fn decode_entity_body(body: &str) -> Option<char> {
    match body {
        "lt" => Some('<'),
        "gt" => Some('>'),
        "amp" => Some('&'),
        "quot" => Some('"'),
        "apos" => Some('\''),
        _ => {
            let num = body.strip_prefix('#')?;
            let code = match num.strip_prefix(['x', 'X']) {
                Some(hex) => u32::from_str_radix(hex, 16).ok()?,
                None => num.parse::<u32>().ok()?,
            };
            // Reject control chars: NUL collides with the CONT sentinel and ESC would inject ANSI into scrollback.
            char::from_u32(code).filter(|c| !c.is_control())
        }
    }
}

fn strip_markdown(s: &str) -> String {
    let no_code: String = s.chars().filter(|&c| c != '`').collect();
    let no_strong = no_code.replace("**", "").replace("__", "");
    let chars: Vec<char> = no_strong.chars().collect();
    let mut out = String::with_capacity(no_strong.len());
    for (i, &c) in chars.iter().enumerate() {
        if (c == '*' || c == '_')
            && !(i > 0
                && chars[i - 1].is_alphanumeric()
                && chars.get(i + 1).is_some_and(|n| n.is_alphanumeric()))
        {
            continue;
        }
        out.push(c);
    }
    out.trim().to_string()
}

const HTML_FORMAT_TAGS: &[&str] = &[
    "b", "strong", "i", "em", "u", "s", "strike", "del", "ins", "mark", "small", "big", "sub",
    "sup", "code", "kbd", "samp", "var", "tt", "span", "font", "q", "abbr", "cite", "pre",
];

fn strip_html_tags(s: &str) -> String {
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '<'
            && let Some((name, end)) = html_tag_at(&chars, i)
        {
            let lower = name.to_ascii_lowercase();
            if lower == "br" {
                out.push(' ');
                i = end;
                continue;
            }
            if HTML_FORMAT_TAGS.contains(&lower.as_str()) {
                i = end;
                continue;
            }
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

fn html_tag_at(chars: &[char], start: usize) -> Option<(String, usize)> {
    let mut i = start + 1;
    if chars.get(i) == Some(&'/') {
        i += 1;
    }
    let name_start = i;
    while i < chars.len() && chars[i].is_ascii_alphanumeric() {
        i += 1;
    }
    if i == name_start {
        return None;
    }
    let name: String = chars[name_start..i].iter().collect();
    while i < chars.len() && chars[i] != '>' {
        if chars[i] == '<' {
            return None;
        }
        i += 1;
    }
    if chars.get(i) == Some(&'>') {
        Some((name, i + 1))
    } else {
        None
    }
}

fn is_link_char(c: char) -> bool {
    matches!(c, '-' | '.' | '=' | '<' | '>')
}

fn parse_link(
    chars: &[char],
    start: usize,
) -> Option<(Head, Head, LineKind, Option<String>, usize)> {
    let mut i = skip_spaces(chars, start);
    let mut left = Head::None;
    if let Some(&c) = chars.get(i)
        && matches!(c, 'o' | 'x')
        && matches!(chars.get(i + 1), Some('-' | '.' | '='))
    {
        left = if c == 'o' { Head::Circle } else { Head::Cross };
        i += 1;
    }
    let op_start = i;
    while i < chars.len() && matches!(chars[i], '-' | '.' | '=' | '<' | '>') {
        i += 1;
    }
    if i == op_start {
        return None;
    }
    let op1: String = chars[op_start..i].iter().collect();
    if left == Head::None && op1.starts_with('<') {
        left = Head::Arrow;
    }
    let mut line = line_kind(&op1);
    let mut right = if op1.contains('>') {
        Head::Arrow
    } else {
        Head::None
    };
    if right == Head::None
        && let Some((head, ni)) = trailing_head(chars, i)
    {
        right = head;
        i = ni;
    }

    if chars.get(i) == Some(&'|') {
        i += 1;
        let l_start = i;
        while i < chars.len() && chars[i] != '|' {
            i += 1;
        }
        let label = clean_label(&chars[l_start..i].iter().collect::<String>());
        if chars.get(i) == Some(&'|') {
            i += 1;
        }
        return Some((left, right, line, non_empty(label), i));
    }

    if right == Head::None {
        let text_start = skip_spaces(chars, i);
        let mut j = text_start;
        while j < chars.len() && !is_link_char(chars[j]) {
            j += 1;
        }
        if j < chars.len() && j > text_start && matches!(chars[j], '-' | '.' | '=' | '>') {
            let text: String = chars[text_start..j].iter().collect();
            let op2_start = j;
            while j < chars.len() && is_link_char(chars[j]) {
                j += 1;
            }
            let op2: String = chars[op2_start..j].iter().collect();
            right = if op2.contains('>') {
                Head::Arrow
            } else if let Some((head, nj)) = trailing_head(chars, j) {
                j = nj;
                head
            } else {
                Head::None
            };
            if line == LineKind::Solid {
                line = line_kind(&op2);
            }
            return Some((left, right, line, non_empty(clean_label(&text)), j));
        }
    }

    Some((left, right, line, None, i))
}

fn line_kind(op: &str) -> LineKind {
    if op.contains('=') {
        LineKind::Thick
    } else if op.contains('.') {
        LineKind::Dotted
    } else {
        LineKind::Solid
    }
}

fn trailing_head(chars: &[char], i: usize) -> Option<(Head, usize)> {
    let head = match chars.get(i) {
        Some('o') => Head::Circle,
        Some('x') => Head::Cross,
        _ => return None,
    };
    match chars.get(i + 1) {
        None | Some(' ') | Some('\t') | Some('|') | Some('&') | Some(';') => Some((head, i + 1)),
        _ => None,
    }
}

fn non_empty(s: String) -> Option<String> {
    if s.is_empty() { None } else { Some(s) }
}

fn parse_state(src: &str) -> Option<Graph> {
    let mut statements: Vec<String> = Vec::new();
    for raw_line in src.lines() {
        split_statements(raw_line, &mut statements);
    }
    let header = statements.first()?;
    if !header
        .split_whitespace()
        .next()?
        .to_ascii_lowercase()
        .starts_with("statediagram")
    {
        return None;
    }

    let mut graph = Graph {
        nodes: Vec::new(),
        edges: Vec::new(),
        index: HashMap::new(),
        groups: Vec::new(),
        node_group: Vec::new(),
        cur_group: None,
        over_cap: false,
        dir: Dir::Down,
    };

    let mut in_note = false;
    for st in &statements[1..] {
        if in_note {
            if st.eq_ignore_ascii_case("end note") {
                in_note = false;
            }
            continue;
        }
        let first = st.split_whitespace().next().unwrap_or("");
        match first.to_ascii_lowercase().as_str() {
            "direction" => {
                graph.dir = match st
                    .split_whitespace()
                    .nth(1)
                    .unwrap_or("")
                    .to_ascii_uppercase()
                    .as_str()
                {
                    "LR" => Dir::Right,
                    "RL" => Dir::Left,
                    "BT" => Dir::Up,
                    _ => Dir::Down,
                };
            }
            "note" => {
                if !st.contains(':') {
                    in_note = true;
                }
            }
            "state" => parse_state_decl(st, &mut graph)?,
            "classdef" | "class" | "hide" | "scale" | "}" | "--" => {}
            _ => {
                if st.contains("-->") {
                    parse_transition(st, &mut graph)?;
                } else {
                    parse_state_desc(st, &mut graph)?;
                }
            }
        }
        if graph.over_cap {
            return None;
        }
    }

    if graph.nodes.is_empty() {
        return None;
    }
    Some(graph)
}

fn parse_state_decl(st: &str, graph: &mut Graph) -> Option<()> {
    let rest = st["state".len()..].trim().trim_end_matches('{').trim();
    if rest.is_empty() {
        return Some(());
    }
    if let Some(q) = rest.strip_prefix('"') {
        let (label, after) = q.split_once('"')?;
        let id = after
            .trim()
            .strip_prefix("as")
            .map(str::trim)
            .unwrap_or(label);
        graph.node_label(id, &decode_html_entities(label))?;
        return Some(());
    }
    let mut shape = Shape::Round;
    let mut id = rest;
    let mut stereotyped = false;
    if let Some(pos) = rest.find("<<") {
        let stereo = rest[pos + 2..].trim_end_matches(">>").trim();
        if stereo == "choice" {
            shape = Shape::Diamond;
        }
        id = rest[..pos].trim();
        stereotyped = true;
    }
    if id.is_empty() || id.contains(char::is_whitespace) {
        return None;
    }
    let label = if stereotyped { Some(id) } else { None };
    graph.node_index(id, label, shape)?;
    Some(())
}

fn parse_transition(st: &str, graph: &mut Graph) -> Option<()> {
    let mut rest = st;
    let mut prev: Option<usize> = None;
    while let Some((lhs, rhs)) = rest.split_once("-->") {
        let from_id = lhs.trim_end().trim_end_matches('-').trim();
        let from = match prev {
            Some(p) => {
                if !from_id.is_empty() {
                    return None;
                }
                p
            }
            None => {
                if from_id.is_empty() {
                    return None;
                }
                state_endpoint(graph, from_id, true)?
            }
        };
        let (to_part, tail) = match rhs.split_once("-->") {
            Some((t, _)) => (t, &rhs[t.len()..]),
            None => (rhs, ""),
        };
        let (to_part, label) = match to_part.split_once(':') {
            Some((t, l)) => (t, non_empty(decode_html_entities(l.trim()))),
            None => (to_part, None),
        };
        let to_id = to_part
            .trim_start()
            .trim_start_matches('>')
            .trim_end()
            .trim_end_matches('-')
            .trim();
        if to_id.is_empty() {
            return None;
        }
        let to = state_endpoint(graph, to_id, false)?;
        if graph.edges.len() >= MAX_EDGES {
            graph.over_cap = true;
            return Some(());
        }
        graph.edges.push(Edge {
            from,
            to,
            label,
            head_to: Head::Arrow,
            head_from: Head::None,
            line: LineKind::Solid,
        });
        prev = Some(to);
        rest = tail;
    }
    Some(())
}

fn state_endpoint(graph: &mut Graph, id: &str, is_source: bool) -> Option<usize> {
    if id == "[*]" {
        let key = if is_source { "[*]start" } else { "[*]end" };
        return graph.node_index(key, Some("●"), Shape::Round);
    }
    graph.node_index(id, None, Shape::Round)
}

fn parse_state_desc(st: &str, graph: &mut Graph) -> Option<()> {
    if let Some((id, desc)) = st.split_once(':') {
        let id = id.trim();
        let desc = desc.trim();
        if id.is_empty() || id.contains(char::is_whitespace) || desc.is_empty() {
            return None;
        }
        graph.node_label(id, &decode_html_entities(desc))?;
    } else if !st.contains(char::is_whitespace) {
        graph.node_index(st, None, Shape::Round)?;
    } else {
        return None;
    }
    Some(())
}

const MAX_MEMBERS: usize = 8;
const CLASS_OPS: &[(&str, Head, Head, LineKind)] = &[
    ("<|--", Head::Triangle, Head::None, LineKind::Solid),
    ("--|>", Head::None, Head::Triangle, LineKind::Solid),
    ("<|..", Head::Triangle, Head::None, LineKind::Dotted),
    ("..|>", Head::None, Head::Triangle, LineKind::Dotted),
    ("*--", Head::DiamondFill, Head::None, LineKind::Solid),
    ("--*", Head::None, Head::DiamondFill, LineKind::Solid),
    ("o--", Head::DiamondOpen, Head::None, LineKind::Solid),
    ("--o", Head::None, Head::DiamondOpen, LineKind::Solid),
    ("<--", Head::Arrow, Head::None, LineKind::Solid),
    ("-->", Head::None, Head::Arrow, LineKind::Solid),
    ("<..", Head::Arrow, Head::None, LineKind::Dotted),
    ("..>", Head::None, Head::Arrow, LineKind::Dotted),
    ("--", Head::None, Head::None, LineKind::Solid),
    ("..", Head::None, Head::None, LineKind::Dotted),
];

#[derive(Default, Clone)]
struct ClassInfo {
    annotation: Option<String>,
    attrs: Vec<String>,
    methods: Vec<String>,
}

fn parse_class(src: &str) -> Option<(Graph, Vec<ClassInfo>)> {
    let mut statements: Vec<String> = Vec::new();
    for raw_line in src.lines() {
        split_statements(raw_line, &mut statements);
    }
    let header = statements.first()?;
    if !header
        .split_whitespace()
        .next()?
        .to_ascii_lowercase()
        .starts_with("classdiagram")
    {
        return None;
    }

    let mut graph = Graph {
        nodes: Vec::new(),
        edges: Vec::new(),
        index: HashMap::new(),
        groups: Vec::new(),
        node_group: Vec::new(),
        cur_group: None,
        over_cap: false,
        dir: Dir::Down,
    };
    let mut infos: Vec<ClassInfo> = Vec::new();
    let mut cur_class: Option<usize> = None;

    for st in &statements[1..] {
        if let Some(ci) = cur_class {
            if st == "}" {
                cur_class = None;
            } else {
                push_member(&mut infos[ci], st);
            }
            continue;
        }
        let first = st.split_whitespace().next().unwrap_or("");
        match first.to_ascii_lowercase().as_str() {
            "direction" => {
                graph.dir = match st
                    .split_whitespace()
                    .nth(1)
                    .unwrap_or("")
                    .to_ascii_uppercase()
                    .as_str()
                {
                    "LR" => Dir::Right,
                    "RL" => Dir::Left,
                    "BT" => Dir::Up,
                    _ => Dir::Down,
                };
                continue;
            }
            "note" | "callback" | "click" | "link" | "style" | "cssclass" | "classdef"
            | "namespace" | "}" => continue,
            "class" => {
                let rest = st["class".len()..].trim();
                let (name, open) = match rest.strip_suffix('{') {
                    Some(n) => (n.trim(), true),
                    None => (rest, false),
                };
                if name.is_empty() || name.contains(char::is_whitespace) {
                    return None;
                }
                let idx = graph.node_index(name, None, Shape::Rect)?;
                sync_infos(&graph, &mut infos);
                if open {
                    cur_class = Some(idx);
                }
                continue;
            }
            _ => {}
        }
        if let Some(ann) = st.strip_prefix("<<") {
            let (ann, rest) = ann.split_once(">>")?;
            let name = rest.trim();
            if name.is_empty() || name.contains(char::is_whitespace) {
                return None;
            }
            let idx = graph.node_index(name, None, Shape::Rect)?;
            sync_infos(&graph, &mut infos);
            infos[idx].annotation = Some(ann.trim().to_string());
            continue;
        }
        if let Some((from, to, head_from, head_to, line, label)) = parse_class_relation(st) {
            let f = graph.node_index(&from, None, Shape::Rect)?;
            sync_infos(&graph, &mut infos);
            let t = graph.node_index(&to, None, Shape::Rect)?;
            sync_infos(&graph, &mut infos);
            if graph.edges.len() >= MAX_EDGES {
                return None;
            }
            graph.edges.push(Edge {
                from: f,
                to: t,
                label,
                head_to,
                head_from,
                line,
            });
            continue;
        }
        if let Some((id, member)) = st.split_once(':') {
            let id = id.trim();
            let member = member.trim();
            if id.is_empty() || id.contains(char::is_whitespace) || member.is_empty() {
                return None;
            }
            let idx = graph.node_index(id, None, Shape::Rect)?;
            sync_infos(&graph, &mut infos);
            push_member(&mut infos[idx], member);
            continue;
        }
        return None;
    }

    if graph.nodes.is_empty() {
        return None;
    }
    sync_infos(&graph, &mut infos);
    Some((graph, infos))
}

fn sync_infos(graph: &Graph, infos: &mut Vec<ClassInfo>) {
    while infos.len() < graph.nodes.len() {
        infos.push(ClassInfo::default());
    }
}

fn push_member(info: &mut ClassInfo, raw: &str) {
    if let Some(ann) = raw.strip_prefix("<<") {
        if let Some((ann, _)) = ann.split_once(">>") {
            info.annotation = Some(ann.trim().to_string());
        }
        return;
    }
    let member = decode_html_entities(&display_generics(raw.trim()));
    let list = if member.contains('(') {
        &mut info.methods
    } else {
        &mut info.attrs
    };
    if list.len() < MAX_MEMBERS {
        list.push(member);
    } else if list.len() == MAX_MEMBERS {
        list.push("…".to_string());
    }
}

fn parse_class_relation(
    st: &str,
) -> Option<(String, String, Head, Head, LineKind, Option<String>)> {
    let chars: Vec<char> = st.chars().collect();
    let mut found: Option<(usize, &str, Head, Head, LineKind)> = None;
    'outer: for pos in 0..chars.len() {
        for &(op, hf, ht, line) in CLASS_OPS {
            if st[char_byte(st, pos)..].starts_with(op) {
                if op.starts_with('o') && pos > 0 && is_id_char(chars[pos - 1]) {
                    continue;
                }
                if op.ends_with('o')
                    && chars
                        .get(pos + op.chars().count())
                        .is_some_and(|&c| is_id_char(c))
                {
                    continue;
                }
                found = Some((pos, op, hf, ht, line));
                break 'outer;
            }
        }
    }
    let (pos, op, head_from, head_to, line) = found?;
    let lhs = st[..char_byte(st, pos)].trim();
    let rhs = st[char_byte(st, pos) + op.len()..].trim();

    let (lhs, card_from) = strip_cardinality_suffix(lhs);
    let (rhs, card_to) = strip_cardinality_prefix(rhs);
    let (to_id, rel_label) = match rhs.split_once(':') {
        Some((t, l)) => (t.trim(), non_empty(decode_html_entities(l.trim()))),
        None => (rhs.trim(), None),
    };
    if lhs.is_empty()
        || to_id.is_empty()
        || lhs.contains(char::is_whitespace)
        || to_id.contains(char::is_whitespace)
    {
        return None;
    }
    let label = non_empty(
        [card_from, rel_label.unwrap_or_default(), card_to]
            .iter()
            .filter(|s| !s.is_empty())
            .cloned()
            .collect::<Vec<_>>()
            .join(" "),
    );
    Some((
        lhs.to_string(),
        to_id.to_string(),
        head_from,
        head_to,
        line,
        label,
    ))
}

fn char_byte(s: &str, char_pos: usize) -> usize {
    s.char_indices()
        .nth(char_pos)
        .map(|(b, _)| b)
        .unwrap_or(s.len())
}

fn strip_cardinality_suffix(s: &str) -> (&str, String) {
    let t = s.trim_end();
    if let Some(rest) = t.strip_suffix('"')
        && let Some(q) = rest.rfind('"')
    {
        return (rest[..q].trim_end(), rest[q + 1..].to_string());
    }
    (t, String::new())
}

fn strip_cardinality_prefix(s: &str) -> (&str, String) {
    let t = s.trim_start();
    if let Some(rest) = t.strip_prefix('"')
        && let Some(q) = rest.find('"')
    {
        return (rest[q + 1..].trim_start(), rest[..q].to_string());
    }
    (t, String::new())
}

fn display_generics(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut open = false;
    for c in s.chars() {
        if c == '~' {
            out.push(if open { '>' } else { '<' });
            open = !open;
        } else {
            out.push(c);
        }
    }
    out
}

fn parse_er(src: &str) -> Option<(Graph, Vec<ClassInfo>)> {
    let mut statements: Vec<String> = Vec::new();
    for raw_line in src.lines() {
        split_statements(raw_line, &mut statements);
    }
    let header = statements.first()?;
    if !header
        .split_whitespace()
        .next()?
        .eq_ignore_ascii_case("erdiagram")
    {
        return None;
    }

    let mut graph = Graph {
        nodes: Vec::new(),
        edges: Vec::new(),
        index: HashMap::new(),
        groups: Vec::new(),
        node_group: Vec::new(),
        cur_group: None,
        over_cap: false,
        dir: Dir::Down,
    };
    let mut infos: Vec<ClassInfo> = Vec::new();
    let mut cur_entity: Option<usize> = None;

    for st in &statements[1..] {
        if let Some(ei) = cur_entity {
            if st == "}" {
                cur_entity = None;
            } else {
                push_er_attribute(&mut infos[ei], st);
            }
            continue;
        }
        if let Some((rel, label_part)) = split_er_relationship(st) {
            let tokens: Vec<&str> = rel.split_whitespace().collect();
            let [lhs, op, rhs] = tokens.as_slice() else {
                return None;
            };
            let (card_l, card_r, line) = parse_er_op(op)?;
            let f = er_entity(&mut graph, &mut infos, lhs)?;
            let t = er_entity(&mut graph, &mut infos, rhs)?;
            if graph.edges.len() >= MAX_EDGES {
                return None;
            }
            let rel_label = label_part.map(clean_label).unwrap_or_default();
            let label = non_empty(
                [card_l.to_string(), rel_label, card_r.to_string()]
                    .iter()
                    .filter(|s| !s.is_empty())
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(" "),
            );
            graph.edges.push(Edge {
                from: f,
                to: t,
                label,
                head_to: Head::None,
                head_from: Head::None,
                line,
            });
            continue;
        }
        let (decl, open) = match st.strip_suffix('{') {
            Some(d) => (d.trim(), true),
            None => (st.as_str(), false),
        };
        if decl.is_empty() || decl.split_whitespace().count() != 1 {
            return None;
        }
        let idx = er_entity(&mut graph, &mut infos, decl)?;
        if open {
            cur_entity = Some(idx);
        }
    }

    if graph.nodes.is_empty() {
        return None;
    }
    sync_infos(&graph, &mut infos);
    Some((graph, infos))
}

fn er_entity(graph: &mut Graph, infos: &mut Vec<ClassInfo>, token: &str) -> Option<usize> {
    let idx = if let Some(open) = token.find('[') {
        let id = &token[..open];
        let label = clean_label(token[open + 1..].trim_end_matches(']'));
        if id.is_empty() || label.is_empty() {
            return None;
        }
        graph.node_label(id, &label)?
    } else {
        graph.node_index(token, None, Shape::Rect)?
    };
    sync_infos(graph, infos);
    Some(idx)
}

fn split_er_relationship(st: &str) -> Option<(&str, Option<&str>)> {
    let (rel, label) = match st.split_once(':') {
        Some((r, l)) => (r, Some(l.trim())),
        None => (st, None),
    };
    let has_op = rel.split_whitespace().any(|t| parse_er_op(t).is_some());
    if has_op { Some((rel, label)) } else { None }
}

fn parse_er_op(tok: &str) -> Option<(&'static str, &'static str, LineKind)> {
    if !tok.is_ascii() || tok.len() != 6 {
        return None;
    }
    let line = match &tok[2..4] {
        "--" => LineKind::Solid,
        ".." => LineKind::Dotted,
        _ => return None,
    };
    Some((er_card(&tok[..2])?, er_card(&tok[4..6])?, line))
}

fn er_card(tok: &str) -> Option<&'static str> {
    match tok {
        "|o" | "o|" => Some("0..1"),
        "||" => Some("1"),
        "}o" | "o{" => Some("0..*"),
        "}|" | "|{" => Some("1..*"),
        _ => None,
    }
}

fn push_er_attribute(info: &mut ClassInfo, raw: &str) {
    let mut parts: Vec<&str> = Vec::new();
    for tok in raw.split_whitespace() {
        if tok.starts_with('"') {
            break;
        }
        parts.push(tok);
    }
    if parts.is_empty() {
        return;
    }
    let line = decode_html_entities(&parts.join(" "));
    if info.attrs.len() < MAX_MEMBERS {
        info.attrs.push(line);
    } else if info.attrs.len() == MAX_MEMBERS {
        info.attrs.push("…".to_string());
    }
}

fn render_class(
    graph: &Graph,
    infos: &[ClassInfo],
    styles: &MermaidStyles,
    max_width: Option<usize>,
) -> Result<MermaidArt, Oversize> {
    let extras: Vec<NodeExtra> = graph
        .nodes
        .iter()
        .zip(infos)
        .map(|(node, info)| {
            let mut title = Vec::new();
            if let Some(a) = &info.annotation {
                title.push(format!("«{a}»"));
            }
            title.push(display_generics(&node.label));
            NodeExtra::Compartments(vec![title, info.attrs.clone(), info.methods.clone()])
        })
        .collect();
    let mut canvas = layout_canvas(graph, &extras, max_width)?;
    match graph.dir {
        Dir::Up => canvas.flip_vertical(),
        Dir::Left => canvas.flip_horizontal(),
        _ => {}
    }
    let (styled_lines, plain_lines) = canvas.to_lines(styles);
    Ok(MermaidArt {
        styled_lines,
        plain_lines,
    })
}

const U: u8 = 1;
const D: u8 = 2;
const L: u8 = 4;
const R: u8 = 8;

#[derive(Clone, Copy, PartialEq)]
enum Cls {
    Empty,
    Border,
    Text,
    Edge,
    EdgeLabel,
}

const STY_DOT: u8 = 1;
const STY_THICK: u8 = 2;
const STY_SOLID: u8 = 4;

struct Canvas {
    w: usize,
    h: usize,
    ch: Vec<char>,
    cls: Vec<Cls>,
    mask: Vec<u8>,
    style: Vec<u8>,
    occupied: Vec<bool>,
    cur_style: u8,
}

impl Canvas {
    fn new(w: usize, h: usize) -> Self {
        let n = w * h;
        Self {
            w,
            h,
            ch: vec![' '; n],
            cls: vec![Cls::Empty; n],
            mask: vec![0; n],
            style: vec![0; n],
            occupied: vec![false; n],
            cur_style: STY_SOLID,
        }
    }

    fn idx(&self, x: usize, y: usize) -> usize {
        y * self.w + x
    }

    fn set(&mut self, x: usize, y: usize, c: char, cls: Cls) {
        if x >= self.w || y >= self.h {
            return;
        }
        let i = self.idx(x, y);
        self.ch[i] = c;
        self.cls[i] = cls;
    }

    fn add_bits(&mut self, x: usize, y: usize, bits: u8) {
        if x >= self.w || y >= self.h {
            return;
        }
        let i = self.idx(x, y);
        if self.occupied[i] {
            return;
        }
        self.mask[i] |= bits;
        self.style[i] |= self.cur_style;
        if self.cls[i] != Cls::Border {
            self.cls[i] = Cls::Edge;
        }
    }

    fn blit(&mut self, sub: &Canvas, ox: usize, oy: usize) {
        for sy in 0..sub.h {
            for sx in 0..sub.w {
                let (x, y) = (ox + sx, oy + sy);
                if x >= self.w || y >= self.h {
                    continue;
                }
                let si = sub.idx(sx, sy);
                let di = self.idx(x, y);
                self.ch[di] = sub.ch[si];
                self.cls[di] = sub.cls[si];
                self.style[di] = sub.style[si];
                self.occupied[di] = true;
            }
        }
    }

    fn junction(&mut self, x: usize, y: usize, bits: u8) {
        if x >= self.w || y >= self.h {
            return;
        }
        let i = self.idx(x, y);
        self.mask[i] |= bits;
        if self.cls[i] != Cls::Border {
            self.cls[i] = Cls::Edge;
        }
    }

    fn seg_v(&mut self, x: usize, y0: usize, y1: usize) {
        let (a, b) = (y0.min(y1), y0.max(y1));
        for y in a..=b {
            let mut bits = 0;
            if y > a {
                bits |= U;
            }
            if y < b {
                bits |= D;
            }
            self.add_bits(x, y, bits);
        }
    }

    fn seg_h(&mut self, y: usize, x0: usize, x1: usize) {
        let (a, b) = (x0.min(x1), x0.max(x1));
        for x in a..=b {
            let mut bits = 0;
            if x > a {
                bits |= L;
            }
            if x < b {
                bits |= R;
            }
            self.add_bits(x, y, bits);
        }
    }

    fn finalize_mask(&mut self) {
        for i in 0..self.ch.len() {
            if self.mask[i] != 0 && self.ch[i] == ' ' {
                let c = mask_char(self.mask[i]);
                self.ch[i] = match self.style[i] {
                    STY_DOT => dotted_char(c),
                    STY_THICK => thick_char(c),
                    _ => c,
                };
            }
        }
    }

    /// Mirror top-to-bottom for `BT` (rows reorder; within-row text is
    /// unaffected, so labels stay readable). Box-drawing glyphs flip too.
    fn flip_vertical(&mut self) {
        for y in 0..self.h / 2 {
            let y2 = self.h - 1 - y;
            for x in 0..self.w {
                let (i, j) = (self.idx(x, y), self.idx(x, y2));
                self.ch.swap(i, j);
                self.cls.swap(i, j);
            }
        }
        for c in self.ch.iter_mut() {
            *c = flip_glyph_v(*c);
        }
    }

    /// Mirror left-to-right for `RL`. Mirroring reverses each row, so after
    /// flipping glyphs we reverse each text/label run back to reading order.
    fn flip_horizontal(&mut self) {
        for y in 0..self.h {
            for x in 0..self.w / 2 {
                let x2 = self.w - 1 - x;
                let (i, j) = (self.idx(x, y), self.idx(x2, y));
                self.ch.swap(i, j);
                self.cls.swap(i, j);
            }
        }
        for c in self.ch.iter_mut() {
            *c = flip_glyph_h(*c);
        }
        for y in 0..self.h {
            let mut x = 0;
            while x < self.w {
                let cls = self.cls[self.idx(x, y)];
                if cls == Cls::Text || cls == Cls::EdgeLabel {
                    let start = self.idx(x, y);
                    while x < self.w && self.cls[self.idx(x, y)] == cls {
                        x += 1;
                    }
                    let end = self.idx(x, y);
                    self.ch[start..end].reverse();
                } else {
                    x += 1;
                }
            }
        }
    }

    fn to_lines(&self, styles: &MermaidStyles) -> (Vec<Line<'static>>, Vec<String>) {
        let mut styled = Vec::with_capacity(self.h);
        let mut plain = Vec::with_capacity(self.h);
        for y in 0..self.h {
            let mut last = self.w;
            for x in (0..self.w).rev() {
                let c = self.ch[self.idx(x, y)];
                if c != ' ' && c != CONT {
                    last = x + 1;
                    break;
                }
            }
            let mut spans: Vec<Span<'static>> = Vec::new();
            let mut plain_row = String::new();
            let mut run = String::new();
            let mut run_cls = Cls::Empty;
            for x in 0..last {
                let i = self.idx(x, y);
                let c = self.ch[i];
                if c == CONT {
                    continue;
                }
                let cls = self.cls[i];
                plain_row.push(c);
                if cls != run_cls && !run.is_empty() {
                    spans.push(Span::styled(
                        std::mem::take(&mut run),
                        style_for(run_cls, styles),
                    ));
                }
                run_cls = cls;
                run.push(c);
            }
            if !run.is_empty() {
                spans.push(Span::styled(run, style_for(run_cls, styles)));
            }
            styled.push(Line::from(spans));
            plain.push(plain_row.trim_end().to_string());
        }
        (styled, plain)
    }
}

fn style_for(cls: Cls, styles: &MermaidStyles) -> Style {
    match cls {
        Cls::Empty => Style::default(),
        Cls::Border => styles.border,
        Cls::Text => styles.node_text,
        Cls::Edge => styles.edge,
        Cls::EdgeLabel => styles.edge_label,
    }
}

fn mask_char(mask: u8) -> char {
    match mask {
        0 => ' ',
        m if m == U || m == D || m == U | D => '│',
        m if m == L || m == R || m == L | R => '─',
        m if m == D | R => '┌',
        m if m == D | L => '┐',
        m if m == U | R => '└',
        m if m == U | L => '┘',
        m if m == U | D | R => '├',
        m if m == U | D | L => '┤',
        m if m == D | L | R => '┬',
        m if m == U | L | R => '┴',
        _ => '┼',
    }
}

fn dotted_char(c: char) -> char {
    match c {
        '─' => '╌',
        '│' => '╎',
        other => other,
    }
}

fn thick_char(c: char) -> char {
    match c {
        '─' => '━',
        '│' => '┃',
        '┌' => '┏',
        '┐' => '┓',
        '└' => '┗',
        '┘' => '┛',
        '├' => '┣',
        '┤' => '┫',
        '┬' => '┳',
        '┴' => '┻',
        '┼' => '╋',
        other => other,
    }
}

fn flip_glyph_v(c: char) -> char {
    match c {
        '┌' => '└',
        '└' => '┌',
        '┐' => '┘',
        '┘' => '┐',
        '┏' => '┗',
        '┗' => '┏',
        '┓' => '┛',
        '┛' => '┓',
        '╭' => '╰',
        '╰' => '╭',
        '╮' => '╯',
        '╯' => '╮',
        '┬' => '┴',
        '┴' => '┬',
        '┳' => '┻',
        '┻' => '┳',
        '▼' => '▲',
        '▲' => '▼',
        '▽' => '△',
        '△' => '▽',
        other => other,
    }
}

fn flip_glyph_h(c: char) -> char {
    match c {
        '┌' => '┐',
        '┐' => '┌',
        '└' => '┘',
        '┘' => '└',
        '┏' => '┓',
        '┓' => '┏',
        '┗' => '┛',
        '┛' => '┗',
        '╭' => '╮',
        '╮' => '╭',
        '╰' => '╯',
        '╯' => '╰',
        '├' => '┤',
        '┤' => '├',
        '┣' => '┫',
        '┫' => '┣',
        '▶' => '◄',
        '◄' => '▶',
        '▷' => '◁',
        '◁' => '▷',
        other => other,
    }
}

struct Placed {
    x: usize,
    y: usize,
    w: usize,
    h: usize,
    cx: usize,
    cy: usize,
    rank: usize,
}

struct NodeSizes {
    box_w: Vec<usize>,
    box_h: Vec<usize>,
    lay_w: Vec<usize>,
    lay_h: Vec<usize>,
    extra_h: Vec<usize>,
    self_label_w: Vec<usize>,
}

fn layout_flowchart(
    graph: &Graph,
    styles: &MermaidStyles,
    max_width: Option<usize>,
) -> Result<MermaidArt, Oversize> {
    let extras: Vec<NodeExtra> = (0..graph.nodes.len()).map(|_| NodeExtra::Plain).collect();
    let mut canvas = layout_canvas(graph, &extras, max_width)?;
    match graph.dir {
        Dir::Up => canvas.flip_vertical(),
        Dir::Left => canvas.flip_horizontal(),
        _ => {}
    }
    let (styled_lines, plain_lines) = canvas.to_lines(styles);
    Ok(MermaidArt {
        styled_lines,
        plain_lines,
    })
}

enum NodeExtra {
    Plain,
    Frame(Canvas),
    Compartments(Vec<Vec<String>>),
}

fn layout_canvas(
    graph: &Graph,
    extras: &[NodeExtra],
    max_width: Option<usize>,
) -> Result<Canvas, Oversize> {
    let n = graph.nodes.len();
    if n == 0 {
        return Err(Oversize::Cells);
    }

    let ranks = compute_ranks(graph);
    let max_rank = *ranks.iter().max().unwrap_or(&0);

    let mut by_rank: Vec<Vec<usize>> = vec![Vec::new(); max_rank + 1];
    for (idx, &r) in ranks.iter().enumerate() {
        by_rank[r].push(idx);
    }
    order_ranks(&mut by_rank, &graph.edges, &ranks);

    let wrapped: Vec<Vec<String>> = graph
        .nodes
        .iter()
        .map(|node| wrap_label(&node.label, WRAP_WIDTH, MAX_LINES))
        .collect();
    let mut box_w: Vec<usize> = (0..n)
        .map(|i| match &extras[i] {
            NodeExtra::Frame(sub) => {
                let title_w = fit_label(&graph.nodes[i].label, WRAP_WIDTH).width();
                (sub.w + 2).max(title_w + 4)
            }
            NodeExtra::Compartments(sections) => {
                sections
                    .iter()
                    .flatten()
                    .map(|l| l.width())
                    .max()
                    .unwrap_or(1)
                    .max(1)
                    + 2 * PAD
                    + 2
            }
            NodeExtra::Plain => {
                wrapped[i]
                    .iter()
                    .map(|l| l.width())
                    .max()
                    .unwrap_or(1)
                    .max(1)
                    + 2 * PAD
                    + 2
            }
        })
        .collect();
    let box_h: Vec<usize> = (0..n)
        .map(|i| match &extras[i] {
            NodeExtra::Frame(sub) => sub.h + 2,
            NodeExtra::Compartments(sections) => {
                let filled = sections.iter().filter(|s| !s.is_empty()).count();
                sections.iter().map(|s| s.len()).sum::<usize>() + filled.saturating_sub(1) + 2
            }
            NodeExtra::Plain => wrapped[i].len() + 2,
        })
        .collect();

    let mut extra_h = vec![0usize; n];
    let mut self_label_w = vec![0usize; n];
    for e in &graph.edges {
        if e.from == e.to {
            extra_h[e.from] = 2;
            if let Some(l) = &e.label {
                self_label_w[e.from] = self_label_w[e.from].max(l.width().min(MAX_LABEL));
            }
        }
    }
    for i in 0..n {
        if extra_h[i] > 0 {
            box_w[i] = box_w[i].max(7);
        }
    }
    let lay_w: Vec<usize> = (0..n)
        .map(|i| {
            box_w[i]
                + if self_label_w[i] > 0 {
                    2 * (self_label_w[i] + 3)
                } else {
                    0
                }
        })
        .collect();
    let lay_h: Vec<usize> = (0..n).map(|i| box_h[i] + extra_h[i]).collect();
    let sizes = NodeSizes {
        box_w,
        box_h,
        lay_w,
        lay_h,
        extra_h,
        self_label_w,
    };

    let mut placed: Vec<Placed> = (0..n)
        .map(|_| Placed {
            x: 0,
            y: 0,
            w: 0,
            h: 0,
            cx: 0,
            cy: 0,
            rank: 0,
        })
        .collect();

    // BT/RL reuse the TD/LR layout, then flip the finished canvas (so text
    // stays readable) into the bottom-up / right-to-left orientation.
    let vertical = matches!(graph.dir, Dir::Down | Dir::Up);
    let plan = if vertical {
        place_td(&ranks, max_rank, &by_rank, &sizes, graph, &mut placed)
    } else {
        place_lr(&ranks, max_rank, &by_rank, &sizes, graph, &mut placed)
    };
    let (canvas_w, canvas_h) = plan.canvas;

    if let Some(mw) = max_width
        && canvas_w > mw
    {
        return Err(Oversize::Width);
    }
    if canvas_w.saturating_mul(canvas_h) > MAX_CANVAS_CELLS {
        return Err(Oversize::Cells);
    }

    let mut canvas = Canvas::new(canvas_w, canvas_h);
    for idx in 0..n {
        match &extras[idx] {
            NodeExtra::Frame(sub) => {
                draw_frame(&mut canvas, &placed[idx], &graph.nodes[idx].label, sub)
            }
            NodeExtra::Compartments(sections) => {
                draw_class_box(&mut canvas, &placed[idx], sections)
            }
            NodeExtra::Plain => draw_box(
                &mut canvas,
                &placed[idx],
                &wrapped[idx],
                graph.nodes[idx].shape,
            ),
        }
    }
    for (i, edge) in graph.edges.iter().enumerate() {
        canvas.cur_style = match edge.line {
            LineKind::Solid => STY_SOLID,
            LineKind::Dotted => STY_DOT,
            LineKind::Thick => STY_THICK,
        };
        if edge.from == edge.to {
            route_self(&mut canvas, &placed[edge.from], edge);
            continue;
        }
        let (from, to) = (&placed[edge.from], &placed[edge.to]);
        let adjacent = to.rank == from.rank + 1;
        let bus = plan.band_end[from.rank] + plan.edge_bus[i];
        let lane = plan.lane_base + plan.edge_lane[i];
        match (vertical, adjacent) {
            (true, true) => route_forward(&mut canvas, from, to, edge, bus),
            (true, false) => route_back(&mut canvas, from, to, edge, lane),
            (false, true) => route_forward_lr(&mut canvas, from, to, edge, bus),
            (false, false) => route_back_lr(&mut canvas, from, to, edge, lane),
        }
    }

    canvas.finalize_mask();
    Ok(canvas)
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
enum Item {
    Node(usize),
    Group(usize),
}

fn render_grouped(
    graph: &Graph,
    styles: &MermaidStyles,
    max_width: Option<usize>,
) -> Result<MermaidArt, Oversize> {
    let mut proxy: HashMap<usize, usize> = HashMap::new();
    for (gi, g) in graph.groups.iter().enumerate() {
        if let Some(&ni) = graph.index.get(&g.id) {
            proxy.insert(ni, gi);
        }
    }

    let group_chain = |g: Option<usize>| -> Vec<usize> {
        let mut chain = Vec::new();
        let mut cur = g;
        while let Some(gi) = cur {
            chain.push(gi);
            cur = graph.groups[gi].parent;
        }
        chain.reverse();
        chain
    };
    let endpoint = |n: usize| -> (Item, Vec<usize>) {
        match proxy.get(&n) {
            Some(&gi) => (Item::Group(gi), group_chain(graph.groups[gi].parent)),
            None => (Item::Node(n), group_chain(graph.node_group[n])),
        }
    };

    let mut scope_edges: HashMap<Option<usize>, Vec<(Item, Item, usize)>> = HashMap::new();
    let mut referenced: Vec<bool> = vec![false; graph.groups.len()];
    for (ei, e) in graph.edges.iter().enumerate() {
        let (item_f, chain_f) = endpoint(e.from);
        let (item_t, chain_t) = endpoint(e.to);
        let k = chain_f
            .iter()
            .zip(&chain_t)
            .take_while(|(a, b)| a == b)
            .count();
        let scope = if k == 0 { None } else { Some(chain_f[k - 1]) };
        let f = if chain_f.len() > k {
            Item::Group(chain_f[k])
        } else {
            item_f
        };
        let t = if chain_t.len() > k {
            Item::Group(chain_t[k])
        } else {
            item_t
        };
        if let Item::Group(gi) = f {
            referenced[gi] = true;
        }
        if let Item::Group(gi) = t {
            referenced[gi] = true;
        }
        scope_edges.entry(scope).or_default().push((f, t, ei));
    }

    let mut direct_nodes: HashMap<Option<usize>, Vec<usize>> = HashMap::new();
    for (ni, g) in graph.node_group.iter().enumerate() {
        if !proxy.contains_key(&ni) {
            direct_nodes.entry(*g).or_default().push(ni);
        }
    }
    let mut keep = vec![false; graph.groups.len()];
    for gi in (0..graph.groups.len()).rev() {
        let has_nodes = direct_nodes.get(&Some(gi)).is_some_and(|v| !v.is_empty());
        let has_children =
            (0..graph.groups.len()).any(|c| graph.groups[c].parent == Some(gi) && keep[c]);
        keep[gi] = has_nodes || has_children || referenced[gi];
    }

    let mut canvas = build_scope(graph, None, &scope_edges, &direct_nodes, &keep, max_width)?;
    match graph.dir {
        Dir::Up => canvas.flip_vertical(),
        Dir::Left => canvas.flip_horizontal(),
        _ => {}
    }
    let (styled_lines, plain_lines) = canvas.to_lines(styles);
    Ok(MermaidArt {
        styled_lines,
        plain_lines,
    })
}

fn build_scope(
    graph: &Graph,
    scope: Option<usize>,
    scope_edges: &HashMap<Option<usize>, Vec<(Item, Item, usize)>>,
    direct_nodes: &HashMap<Option<usize>, Vec<usize>>,
    keep: &[bool],
    max_width: Option<usize>,
) -> Result<Canvas, Oversize> {
    let mut items: Vec<Item> = Vec::new();
    if let Some(nodes) = direct_nodes.get(&scope) {
        items.extend(nodes.iter().map(|&n| Item::Node(n)));
    }
    let child_groups: Vec<usize> = (0..graph.groups.len())
        .filter(|&gi| graph.groups[gi].parent == scope && keep[gi])
        .collect();
    items.extend(child_groups.iter().map(|&gi| Item::Group(gi)));

    if items.is_empty() {
        return Ok(Canvas::new(1, 1));
    }

    let mut index_of: HashMap<Item, usize> = HashMap::new();
    let mut nodes: Vec<Node> = Vec::new();
    let mut extras: Vec<NodeExtra> = Vec::new();
    for item in &items {
        index_of.insert(*item, nodes.len());
        match item {
            Item::Node(ni) => {
                nodes.push(Node {
                    label: graph.nodes[*ni].label.clone(),
                    shape: graph.nodes[*ni].shape,
                });
                extras.push(NodeExtra::Plain);
            }
            Item::Group(gi) => {
                let sub = build_scope(graph, Some(*gi), scope_edges, direct_nodes, keep, None)?;
                nodes.push(Node {
                    label: graph.groups[*gi].label.clone(),
                    shape: Shape::Rect,
                });
                extras.push(NodeExtra::Frame(sub));
            }
        }
    }

    let mut edges: Vec<Edge> = Vec::new();
    if let Some(list) = scope_edges.get(&scope) {
        for (f, t, ei) in list {
            let (Some(&fi), Some(&ti)) = (index_of.get(f), index_of.get(t)) else {
                continue;
            };
            let e = &graph.edges[*ei];
            edges.push(Edge {
                from: fi,
                to: ti,
                label: e.label.clone(),
                head_to: e.head_to,
                head_from: e.head_from,
                line: e.line,
            });
        }
    }

    let synth = Graph {
        nodes,
        edges,
        index: HashMap::new(),
        groups: Vec::new(),
        node_group: Vec::new(),
        cur_group: None,
        over_cap: false,
        dir: graph.dir,
    };
    layout_canvas(&synth, &extras, max_width)
}

fn draw_class_box(canvas: &mut Canvas, p: &Placed, sections: &[Vec<String>]) {
    draw_box(canvas, p, &[], Shape::Rect);
    let inner = p.w.saturating_sub(2 * PAD + 2).max(1);
    let mut row = p.y + 1;
    let mut first = true;
    for (si, section) in sections.iter().enumerate() {
        if section.is_empty() {
            continue;
        }
        if !first {
            canvas.set(p.x, row, '├', Cls::Border);
            for x in (p.x + 1)..(p.x + p.w - 1) {
                canvas.set(x, row, '─', Cls::Border);
            }
            canvas.set(p.x + p.w - 1, row, '┤', Cls::Border);
            row += 1;
        }
        first = false;
        for line in section {
            let text = fit_label(line, inner);
            let tx = if si == 0 {
                p.x + 1 + PAD + inner.saturating_sub(text.width()) / 2
            } else {
                p.x + 1 + PAD
            };
            draw_seq_text(canvas, &text, tx, row, Cls::Text);
            row += 1;
        }
    }
}

fn draw_frame(canvas: &mut Canvas, p: &Placed, title: &str, sub: &Canvas) {
    draw_box(canvas, p, &[], Shape::Rect);
    let t = fit_label(title, p.w.saturating_sub(4));
    draw_seq_text(canvas, &format!(" {t} "), p.x + 1, p.y, Cls::Text);
    let ox = p.x + 1 + (p.w - 2 - sub.w) / 2;
    let oy = p.y + 1 + (p.h - 2 - sub.h) / 2;
    canvas.blit(sub, ox, oy);
}

fn bus_spans_td(
    graph: &Graph,
    ranks: &[usize],
    centers: &[usize],
    r: usize,
    exact: bool,
) -> Vec<(usize, usize, usize, usize, usize)> {
    graph
        .edges
        .iter()
        .enumerate()
        .filter(|(_, e)| {
            let jogs = if exact {
                centers[e.from] != centers[e.to]
            } else {
                centers[e.from].abs_diff(centers[e.to]) > 1
            };
            e.from != e.to && ranks[e.from] == r && ranks[e.to] == r + 1 && jogs
        })
        .map(|(i, e)| {
            let a = centers[e.from].min(centers[e.to]);
            let b = centers[e.from].max(centers[e.to]);
            (a, b, e.from, e.to, i)
        })
        .collect()
}

fn lane_spans(
    graph: &Graph,
    ranks: &[usize],
    placed: &[Placed],
    vertical: bool,
) -> Vec<(usize, usize, usize, usize, usize)> {
    graph
        .edges
        .iter()
        .enumerate()
        .filter(|(_, e)| e.from != e.to && ranks[e.to] != ranks[e.from] + 1)
        .map(|(i, e)| {
            let (pf, pt) = (&placed[e.from], &placed[e.to]);
            let (a, b) = if vertical {
                (pf.cy.min(pt.cy), pf.cy.max(pt.cy))
            } else {
                (pf.cx.min(pt.cx), pf.cx.max(pt.cx))
            };
            (a, b, e.from, e.to, i)
        })
        .collect()
}

fn place_td(
    ranks: &[usize],
    max_rank: usize,
    by_rank: &[Vec<usize>],
    sizes: &NodeSizes,
    graph: &Graph,
    placed: &mut [Placed],
) -> RoutePlan {
    let centers = assign_positions(by_rank, &sizes.lay_w, GAP_X, &graph.edges, ranks);

    let mut edge_bus = vec![0usize; graph.edges.len()];
    let mut bus_tracks = vec![0usize; max_rank + 1];
    for (r, tracks) in bus_tracks.iter_mut().enumerate().take(max_rank) {
        let spans = bus_spans_td(graph, ranks, &centers, r, false);
        if spans.is_empty() {
            continue;
        }
        let (assigned, count) = assign_tracks(&spans);
        for (idx, slot) in assigned {
            edge_bus[idx] = slot;
        }
        *tracks = count;
    }

    let rank_h: Vec<usize> = by_rank
        .iter()
        .map(|row| {
            row.iter()
                .map(|&i| sizes.box_h[i] + sizes.extra_h[i])
                .max()
                .unwrap_or(3)
        })
        .collect();
    let mut rank_y = vec![0usize; max_rank + 1];
    for r in 1..=max_rank {
        let gap = GAP_Y.max(bus_tracks[r - 1] + 1);
        rank_y[r] = rank_y[r - 1] + rank_h[r - 1] + gap;
    }
    let canvas_h = rank_y[max_rank] + rank_h[max_rank];
    let band_end: Vec<usize> = (0..=max_rank).map(|r| rank_y[r] + rank_h[r]).collect();

    let mut diagram_w = 1;
    for (r, row) in by_rank.iter().enumerate() {
        for &idx in row {
            let w = sizes.box_w[idx];
            let h = sizes.box_h[idx];
            let cx = centers[idx];
            let x = cx.saturating_sub(w / 2);
            let y = rank_y[r] + (rank_h[r] - h - sizes.extra_h[idx]) / 2;
            placed[idx] = Placed {
                x,
                y,
                w,
                h,
                cx,
                cy: y + h / 2,
                rank: r,
            };
            diagram_w = diagram_w.max(x + w);
            if sizes.extra_h[idx] > 0 && sizes.self_label_w[idx] > 0 {
                diagram_w = diagram_w.max(x + w + 2 + sizes.self_label_w[idx]);
            }
        }
    }

    let mut content_w = diagram_w;
    for e in &graph.edges {
        if e.from == e.to {
            continue;
        }
        if let Some(label) = &e.label {
            let lw = label.width().min(MAX_LABEL);
            if ranks[e.to] == ranks[e.from] + 1 {
                content_w = content_w.max(placed[e.to].cx + 2 + lw);
            } else {
                content_w = content_w.max(diagram_w + lw + 1);
            }
        }
    }

    let mut edge_lane = vec![0usize; graph.edges.len()];
    let lanes = lane_spans(graph, ranks, placed, true);
    let (canvas_w, lane_base) = if lanes.is_empty() {
        (content_w, 0)
    } else {
        let (assigned, count) = assign_tracks(&lanes);
        for (idx, slot) in assigned {
            edge_lane[idx] = slot;
        }
        (content_w + 1 + count, content_w + 1)
    };

    RoutePlan {
        canvas: (canvas_w, canvas_h),
        band_end,
        edge_bus,
        lane_base,
        edge_lane,
    }
}

fn place_lr(
    ranks: &[usize],
    max_rank: usize,
    by_rank: &[Vec<usize>],
    sizes: &NodeSizes,
    graph: &Graph,
    placed: &mut [Placed],
) -> RoutePlan {
    let col_w: Vec<usize> = by_rank
        .iter()
        .map(|row| row.iter().map(|&i| sizes.box_w[i]).max().unwrap_or(0))
        .collect();

    let max_label = graph
        .edges
        .iter()
        .filter(|e| e.from == e.to || ranks[e.to] == ranks[e.from] + 1)
        .filter_map(|e| e.label.as_ref().map(|l| l.width().min(MAX_LABEL)))
        .max()
        .unwrap_or(0);
    let base_gap = (GAP_X + 1).max(max_label + 3);

    let centers = assign_positions(by_rank, &sizes.lay_h, 1, &graph.edges, ranks);

    let mut edge_bus = vec![0usize; graph.edges.len()];
    let mut bus_tracks = vec![0usize; max_rank + 1];
    for (r, tracks) in bus_tracks.iter_mut().enumerate().take(max_rank) {
        let spans = bus_spans_td(graph, ranks, &centers, r, true);
        if spans.is_empty() {
            continue;
        }
        let (assigned, count) = assign_tracks(&spans);
        for (idx, slot) in assigned {
            edge_bus[idx] = slot;
        }
        *tracks = count;
    }

    let mut rank_x = vec![0usize; max_rank + 1];
    for r in 1..=max_rank {
        let gap = base_gap.max(bus_tracks[r - 1] + 1);
        rank_x[r] = rank_x[r - 1] + col_w[r - 1] + gap;
    }
    let canvas_w = rank_x[max_rank]
        + col_w[max_rank]
        + by_rank[max_rank]
            .iter()
            .filter(|&&i| sizes.extra_h[i] > 0 && sizes.self_label_w[i] > 0)
            .map(|&i| 2 + sizes.self_label_w[i])
            .max()
            .unwrap_or(0);
    let band_end: Vec<usize> = (0..=max_rank).map(|r| rank_x[r] + col_w[r]).collect();

    let mut diagram_h = 1;
    for (r, row) in by_rank.iter().enumerate() {
        let x = rank_x[r];
        for &idx in row {
            let w = sizes.box_w[idx];
            let h = sizes.box_h[idx];
            let cy = centers[idx];
            let y = cy.saturating_sub((h + sizes.extra_h[idx]) / 2);
            placed[idx] = Placed {
                x,
                y,
                w,
                h,
                cx: x + w / 2,
                cy: y + h / 2,
                rank: r,
            };
            diagram_h = diagram_h.max(y + h + sizes.extra_h[idx]);
        }
    }

    let mut edge_lane = vec![0usize; graph.edges.len()];
    let lanes = lane_spans(graph, ranks, placed, false);
    let (canvas_h, lane_base) = if lanes.is_empty() {
        (diagram_h, 0)
    } else {
        let (assigned, count) = assign_tracks(&lanes);
        for (idx, slot) in assigned {
            edge_lane[idx] = slot;
        }
        (diagram_h + 1 + count, diagram_h + 1)
    };

    RoutePlan {
        canvas: (canvas_w, canvas_h),
        band_end,
        edge_bus,
        lane_base,
        edge_lane,
    }
}

struct RoutePlan {
    canvas: (usize, usize),
    band_end: Vec<usize>,
    edge_bus: Vec<usize>,
    lane_base: usize,
    edge_lane: Vec<usize>,
}

fn assign_tracks(spans: &[(usize, usize, usize, usize, usize)]) -> (Vec<(usize, usize)>, usize) {
    let mut sorted = spans.to_vec();
    sorted.sort_unstable();
    let mut tracks: Vec<Vec<(usize, usize, usize, usize)>> = Vec::new();
    let mut out = Vec::with_capacity(sorted.len());
    for &(s, e, f, t, idx) in &sorted {
        let compatible = |members: &Vec<(usize, usize, usize, usize)>| {
            members
                .iter()
                .all(|&(s2, e2, f2, t2)| e2 + 2 <= s || e + 2 <= s2 || f2 == f || t2 == t)
        };
        let slot = match tracks.iter().position(compatible) {
            Some(x) => x,
            None => {
                tracks.push(Vec::new());
                tracks.len() - 1
            }
        };
        tracks[slot].push((s, e, f, t));
        out.push((idx, slot));
    }
    (out, tracks.len())
}

/// Reorder nodes within each rank to minimize edge crossings (Sugiyama-style
/// barycenter sweeps): alternate down/up passes sort each rank by the mean
/// position of its forward neighbours, keeping the ordering with the fewest
/// crossings between adjacent ranks.
fn order_ranks(by_rank: &mut [Vec<usize>], edges: &[Edge], ranks: &[usize]) {
    let n = ranks.len();
    if by_rank.len() < 2 || n < 3 {
        return;
    }
    let mut parents: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); n];
    for e in edges {
        if e.from != e.to && ranks[e.to] > ranks[e.from] {
            parents[e.to].push(e.from);
            children[e.from].push(e.to);
        }
    }

    let mut pos = vec![0usize; n];
    let set_pos = |by_rank: &[Vec<usize>], pos: &mut Vec<usize>| {
        for row in by_rank {
            for (i, &v) in row.iter().enumerate() {
                pos[v] = i;
            }
        }
    };
    set_pos(by_rank, &mut pos);

    let mut best: Vec<Vec<usize>> = by_rank.to_vec();
    let mut best_crossings = count_crossings(edges, ranks, &pos);
    if best_crossings == 0 {
        return;
    }

    for it in 0..8 {
        if it % 2 == 0 {
            for row in by_rank.iter_mut().skip(1) {
                sort_by_barycenter(row, &parents, &pos);
                for (i, &v) in row.iter().enumerate() {
                    pos[v] = i;
                }
            }
        } else {
            let last = by_rank.len() - 1;
            for row in by_rank[..last].iter_mut().rev() {
                sort_by_barycenter(row, &children, &pos);
                for (i, &v) in row.iter().enumerate() {
                    pos[v] = i;
                }
            }
        }
        let crossings = count_crossings(edges, ranks, &pos);
        if crossings < best_crossings {
            best_crossings = crossings;
            best = by_rank.to_vec();
        }
        if best_crossings == 0 {
            break;
        }
    }

    for (row, b) in by_rank.iter_mut().zip(best) {
        *row = b;
    }
}

fn sort_by_barycenter(row: &mut [usize], neigh: &[Vec<usize>], pos: &[usize]) {
    let mut keyed: Vec<(f64, usize)> = row
        .iter()
        .map(|&v| {
            let key = if neigh[v].is_empty() {
                pos[v] as f64
            } else {
                neigh[v].iter().map(|&u| pos[u] as f64).sum::<f64>() / neigh[v].len() as f64
            };
            (key, v)
        })
        .collect();
    keyed.sort_by(|a, b| a.0.total_cmp(&b.0));
    for (slot, (_, v)) in row.iter_mut().zip(keyed) {
        *slot = v;
    }
}

fn count_crossings(edges: &[Edge], ranks: &[usize], pos: &[usize]) -> usize {
    let adjacent: Vec<(usize, usize, usize)> = edges
        .iter()
        .filter(|e| e.from != e.to && ranks[e.to] == ranks[e.from] + 1)
        .map(|e| (ranks[e.from], pos[e.from], pos[e.to]))
        .collect();
    let mut crossings = 0;
    for (i, a) in adjacent.iter().enumerate() {
        for b in &adjacent[i + 1..] {
            if a.0 == b.0 && ((a.1 < b.1 && a.2 > b.2) || (a.1 > b.1 && a.2 < b.2)) {
                crossings += 1;
            }
        }
    }
    crossings
}

/// Assign a center coordinate (along the cross-axis) to every node so nodes line
/// up under their neighbours. Iterative barycenter relaxation: each node drifts
/// toward the average of its forward neighbours while ranks keep order and a
/// minimum `sep` between boxes, which straightens chains and centers branches.
fn assign_positions(
    by_rank: &[Vec<usize>],
    size: &[usize],
    sep: usize,
    edges: &[Edge],
    ranks: &[usize],
) -> Vec<usize> {
    let n = size.len();
    let mut parents: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); n];
    for e in edges {
        if e.from != e.to && ranks[e.to] > ranks[e.from] {
            parents[e.to].push(e.from);
            children[e.from].push(e.to);
        }
    }

    let mut pos = vec![0f64; n];
    for row in by_rank {
        let mut x = 0f64;
        for &v in row {
            let half = size[v] as f64 / 2.0;
            x += half;
            pos[v] = x;
            x += half + sep as f64;
        }
    }

    for it in 0..10 {
        if it % 2 == 0 {
            for row in by_rank.iter() {
                relax_rank(row, &parents, &mut pos, size, sep);
            }
        } else {
            for row in by_rank.iter().rev() {
                relax_rank(row, &children, &mut pos, size, sep);
            }
        }
    }

    let min_left = (0..n)
        .map(|v| pos[v] - size[v] as f64 / 2.0)
        .fold(f64::INFINITY, f64::min);
    let min_left = if min_left.is_finite() { min_left } else { 0.0 };
    (0..n)
        .map(|v| (pos[v] - min_left).round().max(0.0) as usize)
        .collect()
}

fn relax_rank(nodes: &[usize], neigh: &[Vec<usize>], pos: &mut [f64], size: &[usize], sep: usize) {
    let n = nodes.len();
    if n == 0 {
        return;
    }
    let desired: Vec<f64> = nodes
        .iter()
        .map(|&v| {
            if neigh[v].is_empty() {
                pos[v]
            } else {
                neigh[v].iter().map(|&u| pos[u]).sum::<f64>() / neigh[v].len() as f64
            }
        })
        .collect();

    let half = |i: usize| size[nodes[i]] as f64 / 2.0;
    let mut left = vec![0f64; n];
    let mut right = vec![0f64; n];
    for i in 0..n {
        left[i] = if i == 0 {
            desired[i]
        } else {
            desired[i].max(left[i - 1] + half(i - 1) + sep as f64 + half(i))
        };
    }
    for i in (0..n).rev() {
        right[i] = if i == n - 1 {
            desired[i]
        } else {
            desired[i].min(right[i + 1] - half(i + 1) - sep as f64 - half(i))
        };
    }
    for i in 0..n {
        pos[nodes[i]] = (left[i] + right[i]) / 2.0;
    }
    for i in 1..n {
        let min_p = pos[nodes[i - 1]] + half(i - 1) + sep as f64 + half(i);
        if pos[nodes[i]] < min_p {
            pos[nodes[i]] = min_p;
        }
    }
}

fn wrap_label(label: &str, width: usize, max_lines: usize) -> Vec<String> {
    let width = width.max(1);
    let char_w = |c: char| char_width(c).max(1);
    let mut lines: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut cur_w = 0usize;
    for word in label.split_whitespace() {
        let ww = word.width();
        if ww > width {
            if !cur.is_empty() {
                lines.push(std::mem::take(&mut cur));
            }
            let mut chunk = String::new();
            let mut chunk_w = 0usize;
            for ch in word.chars() {
                let cw = char_w(ch);
                if chunk_w + cw > width && !chunk.is_empty() {
                    // Prefer breaking after the last identifier boundary so a long
                    // token is not sliced mid-segment; fall back to a per-char break.
                    let carry = match chunk.rfind(LABEL_BREAK_CHARS) {
                        Some(p) => chunk.split_off(p + 1),
                        None => String::new(),
                    };
                    lines.push(std::mem::take(&mut chunk));
                    chunk_w = carry.chars().map(char_w).sum();
                    chunk = carry;
                }
                chunk.push(ch);
                chunk_w += cw;
            }
            cur = chunk;
            cur_w = chunk_w;
        } else if cur.is_empty() {
            cur.push_str(word);
            cur_w = ww;
        } else if cur_w + 1 + ww <= width {
            cur.push(' ');
            cur.push_str(word);
            cur_w += 1 + ww;
        } else {
            lines.push(std::mem::take(&mut cur));
            cur.push_str(word);
            cur_w = ww;
        }
    }
    if !cur.is_empty() {
        lines.push(cur);
    }
    if lines.is_empty() {
        lines.push(String::new());
    }
    if lines.len() > max_lines {
        lines.truncate(max_lines);
        if let Some(last) = lines.last_mut() {
            let target = width.saturating_sub(1).max(1);
            let mut s = String::new();
            let mut sw = 0usize;
            for ch in last.chars() {
                let cw = char_w(ch);
                if sw + cw > target {
                    break;
                }
                s.push(ch);
                sw += cw;
            }
            s.push('…');
            *last = s;
        }
    }
    lines
}

fn fit_label(label: &str, inner: usize) -> String {
    if label.width() <= inner {
        return label.to_string();
    }
    let mut out = String::new();
    let mut used = 0usize;
    for c in label.chars() {
        let cw = char_width(c);
        if used + cw + 1 > inner {
            break;
        }
        out.push(c);
        used += cw;
    }
    out.push('…');
    out
}

fn draw_box(canvas: &mut Canvas, p: &Placed, lines: &[String], shape: Shape) {
    let (x, y, w, h) = (p.x, p.y, p.w, p.h);
    let right = x + w - 1;
    let bottom = y + h - 1;

    let (tl, tr, bl, br) = match shape {
        Shape::Round | Shape::Diamond => ('╭', '╮', '╰', '╯'),
        Shape::Rect => ('┌', '┐', '└', '┘'),
    };
    canvas.set(x, y, tl, Cls::Border);
    canvas.set(right, y, tr, Cls::Border);
    canvas.set(x, bottom, bl, Cls::Border);
    canvas.set(right, bottom, br, Cls::Border);

    for cx in (x + 1)..right {
        canvas.add_bits(cx, y, L | R);
        canvas.add_bits(cx, bottom, L | R);
    }
    for cy in (y + 1)..bottom {
        canvas.add_bits(x, cy, U | D);
        canvas.add_bits(right, cy, U | D);
    }

    for cy in y..=bottom {
        for cx in x..=right {
            let i = canvas.idx(cx, cy);
            canvas.occupied[i] = true;
        }
    }

    let inner = w.saturating_sub(2 * PAD + 2).max(1);
    for (li, line) in lines.iter().enumerate() {
        let row = y + 1 + li;
        let text = fit_label(line, inner);
        let tw = text.width();
        let text_x = x + 1 + PAD + inner.saturating_sub(tw) / 2;
        let mut cur = text_x;
        for c in text.chars() {
            let cw = char_width(c).max(1);
            canvas.set(cur, row, c, Cls::Text);
            // Wide glyphs (CJK, emoji) own a second column; mark it as a
            // continuation so the line builder doesn't emit a stray space.
            for k in 1..cw {
                canvas.set(cur + k, row, CONT, Cls::Text);
            }
            cur += cw;
        }
    }
}

fn route_forward(canvas: &mut Canvas, from: &Placed, to: &Placed, edge: &Edge, bus: usize) {
    let tx = to.cx;
    let bx = if from.cx.abs_diff(tx) <= 1 {
        tx
    } else {
        from.cx
    };
    let by = from.y + from.h - 1;
    let head_row = to.y - 1;

    canvas.junction(bx, by, D);
    canvas.seg_v(bx, by, bus);
    if bx == tx {
        canvas.seg_v(bx, bus, head_row);
    } else {
        canvas.seg_h(bus, bx, tx);
        canvas.seg_v(tx, bus, head_row);
    }

    if edge.head_to == Head::None {
        canvas.add_bits(tx, head_row, U);
    } else {
        canvas.set(tx, head_row, head_glyph(edge.head_to, '▼'), Cls::Edge);
    }
    if edge.head_from != Head::None {
        canvas.set(bx, by, head_glyph(edge.head_from, '▲'), Cls::Edge);
    }

    if let Some(label) = &edge.label {
        place_label(canvas, label, head_row, tx + 1);
    }
}

fn head_glyph(head: Head, arrow: char) -> char {
    match head {
        Head::Circle => 'o',
        Head::Cross => '×',
        Head::DiamondFill => '◆',
        Head::DiamondOpen => '◇',
        Head::Triangle => match arrow {
            '▼' => '▽',
            '▲' => '△',
            '◄' => '◁',
            '▶' => '▷',
            other => other,
        },
        _ => arrow,
    }
}

fn route_self(canvas: &mut Canvas, p: &Placed, edge: &Edge) {
    let bottom = p.y + p.h - 1;
    let exit_x = p.cx + 1;
    let ret_x = p.x + p.w - 2;
    if ret_x <= exit_x || bottom + 2 >= canvas.h {
        return;
    }
    let (v, h, bl, br) = match edge.line {
        LineKind::Dotted => ('╎', '╌', '╰', '╯'),
        LineKind::Thick => ('┃', '━', '┗', '┛'),
        LineKind::Solid => ('│', '─', '╰', '╯'),
    };
    canvas.junction(exit_x, bottom, D);
    canvas.set(exit_x, bottom + 1, v, Cls::Edge);
    canvas.set(exit_x, bottom + 2, bl, Cls::Edge);
    for x in (exit_x + 1)..ret_x {
        canvas.set(x, bottom + 2, h, Cls::Edge);
    }
    canvas.set(ret_x, bottom + 2, br, Cls::Edge);
    canvas.set(ret_x, bottom + 1, head_glyph(edge.head_to, '▲'), Cls::Edge);
    if let Some(label) = &edge.label {
        place_label(canvas, label, bottom + 1, p.x + p.w + 1);
    }
}

fn route_back(canvas: &mut Canvas, from: &Placed, to: &Placed, edge: &Edge, lane_x: usize) {
    let sx = from.x + from.w - 1;
    let sy = from.cy;
    let tx = to.x + to.w - 1;
    let tyc = to.cy;

    canvas.junction(sx, sy, R);
    canvas.seg_h(sy, sx, lane_x);
    canvas.seg_v(lane_x, sy, tyc);
    canvas.seg_h(tyc, tx + 1, lane_x);

    if edge.head_to == Head::None {
        canvas.add_bits(tx + 1, tyc, R);
    } else {
        canvas.set(tx + 1, tyc, head_glyph(edge.head_to, '◄'), Cls::Edge);
    }
    if edge.head_from != Head::None {
        canvas.set(sx, sy, head_glyph(edge.head_from, '◄'), Cls::Edge);
    }

    if let Some(label) = &edge.label {
        place_label(
            canvas,
            label,
            tyc.saturating_sub(1),
            lane_x.saturating_sub(label.width() + 1),
        );
    }
}

fn route_forward_lr(canvas: &mut Canvas, from: &Placed, to: &Placed, edge: &Edge, bus: usize) {
    let rx = from.x + from.w - 1;
    let ry = from.cy;
    let ly = to.cy;
    let head_col = to.x - 1;

    canvas.junction(rx, ry, R);
    canvas.seg_h(ry, rx, bus);
    if ry == ly {
        canvas.seg_h(ry, bus, head_col);
    } else {
        canvas.seg_v(bus, ry, ly);
        canvas.seg_h(ly, bus, head_col);
    }

    if edge.head_to == Head::None {
        canvas.add_bits(head_col, ly, R);
    } else {
        canvas.set(head_col, ly, head_glyph(edge.head_to, '▶'), Cls::Edge);
    }
    if edge.head_from != Head::None {
        canvas.set(rx, ry, head_glyph(edge.head_from, '◄'), Cls::Edge);
    }

    if let Some(label) = &edge.label {
        place_label(canvas, label, ly.saturating_sub(1), bus + 1);
    }
}

fn route_back_lr(canvas: &mut Canvas, from: &Placed, to: &Placed, edge: &Edge, lane_y: usize) {
    let sx = from.cx;
    let sy = from.y + from.h - 1;
    let tx = to.cx;
    let ty = to.y + to.h - 1;

    canvas.junction(sx, sy, D);
    canvas.seg_v(sx, sy, lane_y);
    canvas.seg_h(lane_y, sx, tx);
    canvas.seg_v(tx, lane_y, ty + 1);

    if edge.head_to == Head::None {
        canvas.add_bits(tx, ty + 1, D);
    } else {
        canvas.set(tx, ty + 1, head_glyph(edge.head_to, '▲'), Cls::Edge);
    }
    if edge.head_from != Head::None {
        canvas.set(sx, sy, head_glyph(edge.head_from, '▲'), Cls::Edge);
    }

    if let Some(label) = &edge.label {
        place_label(canvas, label, lane_y.saturating_sub(1), (sx + tx) / 2);
    }
}

fn place_label(canvas: &mut Canvas, label: &str, row: usize, start_x: usize) {
    if row >= canvas.h {
        return;
    }
    let text = fit_label(label, MAX_LABEL);
    let mut x = start_x;
    for c in text.chars() {
        let cw = char_width(c).max(1);
        if x + cw > canvas.w {
            break;
        }
        let blocked = (0..cw).any(|k| {
            let i = canvas.idx(x + k, row);
            canvas.ch[i] != ' ' || canvas.mask[i] != 0 || canvas.occupied[i]
        });
        if blocked {
            break;
        }
        canvas.set(x, row, c, Cls::EdgeLabel);
        for k in 1..cw {
            canvas.set(x + k, row, CONT, Cls::EdgeLabel);
        }
        x += cw;
    }
}

fn compute_ranks(graph: &Graph) -> Vec<usize> {
    let n = graph.nodes.len();
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut indeg = vec![0usize; n];
    for e in &graph.edges {
        if e.from != e.to {
            children[e.from].push(e.to);
            indeg[e.to] += 1;
        }
    }

    let mut color = vec![0u8; n];
    let mut dag: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut order: Vec<usize> = Vec::with_capacity(n);

    let roots: Vec<usize> = (0..n).filter(|&i| indeg[i] == 0).collect();
    for start in roots.iter().copied().chain(0..n) {
        if color[start] == 0 {
            dfs_dag(start, &children, &mut color, &mut dag, &mut order);
        }
    }

    let mut rank = vec![0usize; n];
    for &u in order.iter().rev() {
        for &v in &dag[u] {
            rank[v] = rank[v].max(rank[u] + 1);
        }
    }
    rank
}

fn dfs_dag(
    start: usize,
    children: &[Vec<usize>],
    color: &mut [u8],
    dag: &mut [Vec<usize>],
    order: &mut Vec<usize>,
) {
    let mut stack: Vec<(usize, usize)> = vec![(start, 0)];
    color[start] = 1;
    while let Some(frame) = stack.last_mut() {
        let u = frame.0;
        if frame.1 < children[u].len() {
            let v = children[u][frame.1];
            frame.1 += 1;
            if color[v] == 1 {
                continue;
            }
            dag[u].push(v);
            if color[v] == 0 {
                color[v] = 1;
                stack.push((v, 0));
            }
        } else {
            color[u] = 2;
            order.push(u);
            stack.pop();
        }
    }
}

const SEQ_GAP: usize = 5;
const SEQ_OPS: &[(&str, bool, SeqHead)] = &[
    ("-->>", true, SeqHead::Arrow),
    ("->>", false, SeqHead::Arrow),
    ("--x", true, SeqHead::Cross),
    ("-x", false, SeqHead::Cross),
    ("--)", true, SeqHead::Arrow),
    ("-)", false, SeqHead::Arrow),
    ("-->", true, SeqHead::Arrow),
    ("->", false, SeqHead::Arrow),
];

#[derive(Clone, Copy, PartialEq)]
enum SeqHead {
    Arrow,
    Cross,
}

enum NoteAnchor {
    Over(usize, usize),
    Left(usize),
    Right(usize),
}

enum SeqItem {
    Message {
        from: usize,
        to: usize,
        text: Option<String>,
        dashed: bool,
        head: SeqHead,
    },
    Note {
        anchor: NoteAnchor,
        text: String,
    },
    Divider {
        text: String,
    },
}

struct Sequence {
    labels: Vec<String>,
    index: HashMap<String, usize>,
    items: Vec<SeqItem>,
}

impl Sequence {
    fn participant(&mut self, id: &str, label: Option<&str>) -> Option<usize> {
        if let Some(&i) = self.index.get(id) {
            if let Some(label) = label {
                self.labels[i] = label.to_string();
            }
            return Some(i);
        }
        if self.labels.len() >= MAX_NODES {
            return None;
        }
        self.index.insert(id.to_string(), self.labels.len());
        self.labels.push(label.unwrap_or(id).to_string());
        Some(self.labels.len() - 1)
    }
}

fn parse_sequence(src: &str) -> Option<Sequence> {
    let mut statements: Vec<String> = Vec::new();
    for raw_line in src.lines() {
        split_statements(raw_line, &mut statements);
    }
    let header = statements.first()?;
    if !header
        .split_whitespace()
        .next()?
        .eq_ignore_ascii_case("sequencediagram")
    {
        return None;
    }

    let mut seq = Sequence {
        labels: Vec::new(),
        index: HashMap::new(),
        items: Vec::new(),
    };
    let mut autonumber = false;
    let mut msg_count = 0usize;
    let mut blocks: Vec<bool> = Vec::new();

    for st in &statements[1..] {
        let first = st.split_whitespace().next().unwrap_or("");
        match first.to_ascii_lowercase().as_str() {
            "participant" | "actor" => {
                let rest = st[first.len()..].trim();
                if rest.is_empty() {
                    return None;
                }
                let (id, label) = match rest.split_once(" as ") {
                    Some((id, label)) => (id.trim(), Some(clean_label(label))),
                    None => (rest, None),
                };
                seq.participant(id, label.as_deref())?;
            }
            "autonumber" => autonumber = true,
            "activate" | "deactivate" | "create" | "destroy" | "title" | "acctitle"
            | "accdescr" | "links" | "link" | "properties" => {}
            "note" => {
                let rest = st[first.len()..].trim();
                let (text_part, anchor) = parse_note_anchor(rest, &mut seq)?;
                if seq.items.len() >= MAX_EDGES {
                    return None;
                }
                seq.items.push(SeqItem::Note {
                    anchor,
                    text: text_part,
                });
            }
            "loop" | "alt" | "opt" | "par" | "critical" | "break" | "else" | "and" | "option" => {
                if matches!(
                    first.to_ascii_lowercase().as_str(),
                    "else" | "and" | "option"
                ) {
                    if blocks.last() != Some(&true) {
                        continue;
                    }
                } else {
                    blocks.push(true);
                }
                if seq.items.len() >= MAX_EDGES {
                    return None;
                }
                seq.items.push(SeqItem::Divider {
                    text: decode_html_entities(st),
                });
            }
            "rect" | "box" => blocks.push(false),
            "end" => {
                if blocks.pop() == Some(true) {
                    if seq.items.len() >= MAX_EDGES {
                        return None;
                    }
                    seq.items.push(SeqItem::Divider {
                        text: "end".to_string(),
                    });
                }
            }
            _ => {
                let (from, to, mut text, dashed, head) = parse_seq_message(st, &mut seq)?;
                if autonumber {
                    msg_count += 1;
                    text = Some(match text {
                        Some(t) => format!("{msg_count}. {t}"),
                        None => format!("{msg_count}."),
                    });
                }
                if seq.items.len() >= MAX_EDGES {
                    return None;
                }
                seq.items.push(SeqItem::Message {
                    from,
                    to,
                    text,
                    dashed,
                    head,
                });
            }
        }
    }

    if seq.labels.is_empty() {
        return None;
    }
    Some(seq)
}

fn parse_note_anchor(rest: &str, seq: &mut Sequence) -> Option<(String, NoteAnchor)> {
    let lower = rest.to_ascii_lowercase();
    let (ids_and_text, kind) = if let Some(r) = lower.strip_prefix("over ") {
        (&rest[rest.len() - r.len()..], 0u8)
    } else if let Some(r) = lower.strip_prefix("left of ") {
        (&rest[rest.len() - r.len()..], 1)
    } else if let Some(r) = lower.strip_prefix("right of ") {
        (&rest[rest.len() - r.len()..], 2)
    } else {
        return None;
    };
    let (ids, text) = ids_and_text.split_once(':')?;
    let text = decode_html_entities(text.trim());
    let mut parts = ids.split(',').map(str::trim).filter(|s| !s.is_empty());
    let a = seq.participant(parts.next()?, None)?;
    let anchor = match kind {
        0 => {
            let b = match parts.next() {
                Some(id) => seq.participant(id, None)?,
                None => a,
            };
            NoteAnchor::Over(a.min(b), a.max(b))
        }
        1 => NoteAnchor::Left(a),
        _ => NoteAnchor::Right(a),
    };
    Some((text, anchor))
}

fn parse_seq_message(
    st: &str,
    seq: &mut Sequence,
) -> Option<(usize, usize, Option<String>, bool, SeqHead)> {
    let mut found: Option<(usize, &str, bool, SeqHead)> = None;
    for (pos, _) in st.char_indices() {
        for &(op, dashed, head) in SEQ_OPS {
            if st[pos..].starts_with(op) {
                found = Some((pos, op, dashed, head));
                break;
            }
        }
        if found.is_some() {
            break;
        }
    }
    let (pos, op, dashed, head) = found?;
    let from_id = st[..pos].trim();
    if from_id.is_empty() {
        return None;
    }
    let rest = st[pos + op.len()..]
        .trim_start()
        .trim_start_matches(['+', '-']);
    let (to_id, text) = match rest.split_once(':') {
        Some((to, text)) => (to.trim(), non_empty(decode_html_entities(text.trim()))),
        None => (rest.trim(), None),
    };
    if to_id.is_empty() {
        return None;
    }
    let from = seq.participant(from_id, None)?;
    let to = seq.participant(to_id, None)?;
    Some((from, to, text, dashed, head))
}

fn note_geometry(xs: &[usize], anchor: &NoteAnchor, text_w: usize) -> (usize, usize) {
    match *anchor {
        NoteAnchor::Over(l, r) => {
            let center = (xs[l] + xs[r]) / 2;
            let w = (xs[r] - xs[l] + 5).max(text_w + 2 * PAD + 2);
            (center.saturating_sub(w / 2), w)
        }
        NoteAnchor::Left(i) => {
            let w = text_w + 2 * PAD + 2;
            (xs[i].saturating_sub(2 + w - 1), w)
        }
        NoteAnchor::Right(i) => (xs[i] + 2, text_w + 2 * PAD + 2),
    }
}

fn layout_sequence(
    seq: &Sequence,
    styles: &MermaidStyles,
    max_width: Option<usize>,
) -> Result<MermaidArt, Oversize> {
    let n = seq.labels.len();
    let labels: Vec<String> = seq
        .labels
        .iter()
        .map(|l| fit_label(l, WRAP_WIDTH))
        .collect();
    let box_w: Vec<usize> = labels
        .iter()
        .map(|l| l.width().max(1) + 2 * PAD + 2)
        .collect();
    let box_h = 3usize;

    let item_text_w = |text: &Option<String>| text.as_deref().map(|t| t.width()).unwrap_or(0);

    let mut gaps: Vec<usize> = (0..n.saturating_sub(1))
        .map(|i| SEQ_GAP.max(box_w[i].div_ceil(2) + box_w[i + 1].div_ceil(2) + 1))
        .collect();

    let mut reqs: Vec<(usize, usize, usize)> = Vec::new();
    for item in &seq.items {
        match item {
            SeqItem::Message { from, to, text, .. } => {
                let tw = item_text_w(text);
                if from != to {
                    let (l, r) = (*from.min(to), *from.max(to));
                    reqs.push((l, r, (tw + 2).max(4)));
                } else if *from + 1 < n {
                    reqs.push((*from, *from + 1, 5 + tw + 2));
                }
            }
            SeqItem::Note { anchor, text } => {
                let tw = text.width();
                match *anchor {
                    NoteAnchor::Over(l, r) if l < r => reqs.push((l, r, tw.saturating_sub(1))),
                    NoteAnchor::Over(i, _) => {
                        let half = (tw + 4).div_ceil(2) + 2;
                        if i > 0 {
                            reqs.push((i - 1, i, half));
                        }
                        if i + 1 < n {
                            reqs.push((i, i + 1, half));
                        }
                    }
                    NoteAnchor::Left(i) if i > 0 => reqs.push((i - 1, i, tw + 7)),
                    NoteAnchor::Right(i) if i + 1 < n => reqs.push((i, i + 1, tw + 7)),
                    _ => {}
                }
            }
            SeqItem::Divider { .. } => {}
        }
    }
    reqs.sort_by_key(|&(l, r, _)| r - l);
    for (l, r, need) in reqs {
        let cur: usize = gaps[l..r].iter().sum();
        if cur < need {
            gaps[r - 1] += need - cur;
        }
    }

    let mut xs = vec![0usize; n];
    xs[0] = box_w[0] / 2;
    for i in 1..n {
        xs[i] = xs[i - 1] + gaps[i - 1];
    }

    let mut canvas_w = xs[n - 1] + box_w[n - 1].div_ceil(2) + 1;
    for item in &seq.items {
        match item {
            SeqItem::Message { from, to, text, .. } if from == to => {
                canvas_w = canvas_w.max(xs[*from] + 5 + item_text_w(text) + 1);
            }
            SeqItem::Note { anchor, text } => {
                let (x, w) = note_geometry(&xs, anchor, text.width());
                canvas_w = canvas_w.max(x + w + 1);
            }
            SeqItem::Divider { text } => {
                canvas_w = canvas_w.max(text.width() + 4);
            }
            _ => {}
        }
    }

    let mut rows: Vec<usize> = Vec::with_capacity(seq.items.len());
    let mut y = box_h + 1;
    for item in &seq.items {
        rows.push(y);
        y += match item {
            SeqItem::Message { from, to, text, .. } => {
                if from == to {
                    4
                } else if text.is_some() {
                    3
                } else {
                    2
                }
            }
            SeqItem::Note { .. } => 4,
            SeqItem::Divider { .. } => 2,
        };
    }
    let bottom_top = y;
    let canvas_h = bottom_top + box_h;

    if let Some(mw) = max_width
        && canvas_w > mw
    {
        return Err(Oversize::Width);
    }
    if canvas_w.saturating_mul(canvas_h) > MAX_CANVAS_CELLS {
        return Err(Oversize::Cells);
    }

    let mut canvas = Canvas::new(canvas_w, canvas_h);
    for i in 0..n {
        for by in [0, bottom_top] {
            let p = Placed {
                x: xs[i].saturating_sub(box_w[i] / 2),
                y: by,
                w: box_w[i],
                h: box_h,
                cx: xs[i],
                cy: by + 1,
                rank: 0,
            };
            draw_box(
                &mut canvas,
                &p,
                std::slice::from_ref(&labels[i]),
                Shape::Rect,
            );
        }
    }
    for (item, &r) in seq.items.iter().zip(&rows) {
        if let SeqItem::Note { anchor, text } = item {
            let (x, w) = note_geometry(&xs, anchor, text.width());
            let p = Placed {
                x,
                y: r,
                w,
                h: 3,
                cx: x + w / 2,
                cy: r + 1,
                rank: 0,
            };
            draw_box(&mut canvas, &p, std::slice::from_ref(text), Shape::Rect);
        }
    }
    for &x in &xs {
        canvas.junction(x, box_h - 1, D);
        canvas.seg_v(x, box_h, bottom_top - 1);
        canvas.junction(x, bottom_top, U);
    }

    for (item, &r) in seq.items.iter().zip(&rows) {
        match item {
            SeqItem::Message {
                from,
                to,
                text,
                dashed,
                head,
            } => {
                let line_ch = if *dashed { '╌' } else { '─' };
                if from == to {
                    let x = xs[*from];
                    canvas.junction(x, r, R);
                    canvas.set(x + 1, r, line_ch, Cls::Edge);
                    canvas.set(x + 2, r, line_ch, Cls::Edge);
                    canvas.set(x + 3, r, '╮', Cls::Edge);
                    canvas.set(x + 3, r + 1, '│', Cls::Edge);
                    canvas.set(
                        x + 1,
                        r + 2,
                        if *head == SeqHead::Cross { '×' } else { '◄' },
                        Cls::Edge,
                    );
                    canvas.set(x + 2, r + 2, line_ch, Cls::Edge);
                    canvas.set(x + 3, r + 2, '╯', Cls::Edge);
                    if let Some(t) = text {
                        draw_seq_text(&mut canvas, t, x + 5, r + 1, Cls::Text);
                    }
                } else {
                    let (x0, x1) = (xs[*from], xs[*to]);
                    let rightward = x1 > x0;
                    let arrow_row = if text.is_some() { r + 1 } else { r };
                    let (lo, hi) = (x0.min(x1), x0.max(x1));
                    canvas.junction(x0, arrow_row, if rightward { R } else { L });
                    for x in (lo + 1)..hi {
                        canvas.set(x, arrow_row, line_ch, Cls::Edge);
                    }
                    let head_ch = match (head, rightward) {
                        (SeqHead::Cross, _) => '×',
                        (SeqHead::Arrow, true) => '▶',
                        (SeqHead::Arrow, false) => '◄',
                    };
                    let head_x = if rightward { x1 - 1 } else { x1 + 1 };
                    canvas.set(head_x, arrow_row, head_ch, Cls::Edge);
                    if let Some(t) = text {
                        let span = hi - lo - 1;
                        let t = fit_label(t, span.max(1));
                        let tx = lo + 1 + span.saturating_sub(t.width()) / 2;
                        draw_seq_text(&mut canvas, &t, tx, r, Cls::Text);
                    }
                }
            }
            SeqItem::Note { .. } => {}
            SeqItem::Divider { text } => {
                for x in 0..canvas_w {
                    canvas.set(x, r, '─', Cls::Edge);
                }
                let t = fit_label(text, canvas_w.saturating_sub(4));
                draw_seq_text(&mut canvas, &format!(" {t} "), 2, r, Cls::EdgeLabel);
            }
        }
    }

    canvas.finalize_mask();
    let (styled_lines, plain_lines) = canvas.to_lines(styles);
    Ok(MermaidArt {
        styled_lines,
        plain_lines,
    })
}

fn draw_seq_text(canvas: &mut Canvas, text: &str, x: usize, y: usize, cls: Cls) {
    let mut cur = x;
    for c in text.chars() {
        let cw = char_width(c).max(1);
        for k in 0..cw {
            if cur + k < canvas.w && y < canvas.h {
                let i = canvas.idx(cur + k, y);
                canvas.mask[i] = 0;
            }
            canvas.set(cur + k, y, if k == 0 { c } else { CONT }, cls);
        }
        cur += cw;
    }
}

const TOO_WIDE_HINT: &str =
    "This diagram is too wide to display here \u{2014} open the image to view it in full.";

fn fallback(
    src: &str,
    styles: &MermaidStyles,
    max_width: Option<usize>,
    too_wide: bool,
) -> MermaidArt {
    let header = first_word(src);
    let title = format!(" mermaid: {header} ");
    let limit = max_width.map(|m| m.saturating_sub(4).max(8));
    let body: Vec<String> = src
        .lines()
        .map(|l| l.trim_end())
        .skip_while(|l| l.is_empty())
        .flat_map(|l| chunk_line(l, limit))
        .collect();
    let content_w = body
        .iter()
        .map(|l| l.width())
        .chain(std::iter::once(title.width()))
        .max()
        .unwrap_or(0);
    let inner = content_w + 2;

    let mut styled = Vec::new();
    let mut plain = Vec::new();

    let mut top = String::from("╭");
    top.push_str(&title);
    for _ in 0..inner.saturating_sub(title.width()) {
        top.push('─');
    }
    top.push('╮');
    styled.push(Line::from(vec![
        Span::styled("╭".to_string(), styles.border),
        Span::styled(title.clone(), styles.title),
        Span::styled(
            format!("{}╮", "─".repeat(inner.saturating_sub(title.width()))),
            styles.border,
        ),
    ]));
    plain.push(top);

    for line in &body {
        let pad = content_w.saturating_sub(line.width());
        styled.push(Line::from(vec![
            Span::styled("│ ".to_string(), styles.border),
            Span::styled(line.clone(), styles.node_text),
            Span::styled(format!("{} │", " ".repeat(pad)), styles.border),
        ]));
        plain.push(format!("│ {}{} │", line, " ".repeat(pad)));
    }

    let bottom = format!("╰{}╯", "─".repeat(inner));
    styled.push(Line::from(Span::styled(bottom.clone(), styles.border)));
    plain.push(bottom);

    if too_wide {
        let hint_style = styles.border.add_modifier(Modifier::ITALIC);
        for chunk in wrap_words(TOO_WIDE_HINT, max_width) {
            styled.push(Line::from(Span::styled(chunk.clone(), hint_style)));
            plain.push(chunk);
        }
    }

    MermaidArt {
        styled_lines: styled,
        plain_lines: plain,
    }
}

fn chunk_line(line: &str, limit: Option<usize>) -> Vec<String> {
    let Some(limit) = limit else {
        return vec![line.to_string()];
    };
    if line.width() <= limit {
        return vec![line.to_string()];
    }
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut cur_w = 0usize;
    for c in line.chars() {
        let cw = char_width(c).max(1);
        if cur_w + cw > limit && !cur.is_empty() {
            out.push(std::mem::take(&mut cur));
            cur_w = 0;
        }
        cur.push(c);
        cur_w += cw;
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

fn wrap_words(text: &str, limit: Option<usize>) -> Vec<String> {
    let Some(limit) = limit else {
        return vec![text.to_string()];
    };
    let mut lines: Vec<String> = Vec::new();
    let mut cur = String::new();
    for word in text.split(' ').filter(|w| !w.is_empty()) {
        if cur.is_empty() {
            cur.push_str(word);
        } else if cur.width() + 1 + word.width() <= limit {
            cur.push(' ');
            cur.push_str(word);
        } else {
            lines.push(std::mem::take(&mut cur));
            cur.push_str(word);
        }
    }
    if !cur.is_empty() {
        lines.push(cur);
    }
    lines
        .into_iter()
        .flat_map(|l| chunk_line(&l, Some(limit)))
        .collect()
}

fn first_word(src: &str) -> String {
    src.split_whitespace()
        .next()
        .unwrap_or("diagram")
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn styles() -> MermaidStyles {
        let s = Style::default();
        MermaidStyles {
            border: s,
            node_text: s,
            edge: s,
            edge_label: s,
            title: s,
        }
    }

    fn plain(src: &str) -> String {
        render(src, &styles(), Some(120))
            .unwrap()
            .plain_lines
            .join("\n")
    }

    #[test]
    fn parses_nodes_edges_and_direction() {
        let g = parse_graph("flowchart LR\n  A[Start] --> B[End]").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.nodes[0].label, "Start");
        assert_eq!(g.nodes[1].label, "End");
        assert!(g.dir == Dir::Right);
    }

    #[test]
    fn non_flowchart_returns_none_from_parse() {
        assert!(parse_graph("sequenceDiagram\n  A->>B: hi").is_none());
    }

    #[test]
    fn html_tags_are_stripped_from_labels() {
        let g = parse_graph("flowchart TD\n  A[\"<b>Bold</b> and <i>italic</i>\"] --> B").unwrap();
        assert_eq!(g.nodes[0].label, "Bold and italic");
    }

    #[test]
    fn br_tag_becomes_a_space() {
        let g = parse_graph("flowchart TD\n  A[\"Line1<br/>Line2<br>Line3\"]").unwrap();
        assert_eq!(g.nodes[0].label, "Line1 Line2 Line3");
    }

    #[test]
    fn markdown_string_strips_bold_italic_and_code() {
        let g = parse_graph(
            "flowchart TD\n  A[\"`**Start** here`\"] --> B[\"`Save to **database**`\"]\n  B --> C[\"`**Done!**`\"]",
        )
        .unwrap();
        assert_eq!(g.nodes[0].label, "Start here");
        assert_eq!(g.nodes[1].label, "Save to database");
        assert_eq!(g.nodes[2].label, "Done!");
    }

    #[test]
    fn markdown_string_preserves_snake_case_and_strips_inline_code() {
        let g = parse_graph("flowchart TD\n  A[\"`_italic_ uses `vocab_size` with __all__`\"]")
            .unwrap();
        assert_eq!(g.nodes[0].label, "italic uses vocab_size with all");
    }

    #[test]
    fn markdown_string_edge_label_is_stripped() {
        let g =
            parse_graph("flowchart TD\n  A -->|\"`**yes**`\"| B\n  A -->|\"`__no__`\"| C").unwrap();
        assert_eq!(g.edges[0].label.as_deref(), Some("yes"));
        assert_eq!(g.edges[1].label.as_deref(), Some("no"));
    }

    #[test]
    fn plain_label_keeps_literal_text_and_underscores() {
        // Not a markdown string (no backtick wrapper): Mermaid renders it
        // literally, so brackets, snake_case, and any `*`/`_` must survive.
        let g = parse_graph("flowchart TD\n  A[\"[ 464, 3797 ] seq_len d_model\"]").unwrap();
        assert_eq!(g.nodes[0].label, "[ 464, 3797 ] seq_len d_model");
    }

    #[test]
    fn code_and_span_tags_are_stripped() {
        let g = parse_graph(
            "flowchart TD\n  A[\"<code>vocab_size</code> <span style=\\\"color:red\\\">x</span>\"]",
        )
        .unwrap();
        assert_eq!(g.nodes[0].label, "vocab_size x");
    }

    #[test]
    fn bare_angle_brackets_are_kept() {
        let g = parse_graph("flowchart TD\n  A[\"a < b and c > d\"]").unwrap();
        assert_eq!(g.nodes[0].label, "a < b and c > d");
    }

    #[test]
    fn generic_types_are_not_stripped_as_html() {
        // `<String>` / `<i32>` / `<id>` look like tags but are not HTML
        // formatting tags, so they must survive (only b/i/code/span/… etc. and
        // <br> are stripped).
        let g = parse_graph(
            "flowchart TD\n  A[\"Returns Vec<String>\"] --> B[\"Option<i32> for <id>\"]",
        )
        .unwrap();
        assert_eq!(g.nodes[0].label, "Returns Vec<String>");
        assert_eq!(g.nodes[1].label, "Option<i32> for <id>");
    }

    #[test]
    fn decode_html_entities_covers_named_numeric_and_double_escape() {
        assert_eq!(
            decode_html_entities("&lt;a&gt; &amp; &quot;x&quot; &apos;y&apos;"),
            "<a> & \"x\" 'y'"
        );
        assert_eq!(decode_html_entities("it&#39;s &#60;ok&#62;"), "it's <ok>");
        assert_eq!(
            decode_html_entities("&#x3c;tag&#X3E; &#x27;q&#x27;"),
            "<tag> 'q'"
        );
        // `&amp;lt;` must yield the literal `&lt;`, never `<`.
        assert_eq!(decode_html_entities("&amp;lt;"), "&lt;");
        assert_eq!(decode_html_entities("a &foo; b & c"), "a &foo; b & c");
        // Control chars (NUL collides with CONT, ESC injects ANSI) never decode.
        assert_eq!(decode_html_entities("a&#27;b&#0;c"), "a&#27;b&#0;c");
        assert_eq!(decode_html_entities("x&#x1b;y"), "x&#x1b;y");
    }

    #[test]
    fn entity_escaped_flowchart_label_decodes_in_box_art() {
        let src = "flowchart LR\n  YAML[\"models-config/&lt;model&gt;/&lt;env&gt;.yaml\\nenterprise_api_config:\"]\n  PY[\"model_config_map.py\\nlanguage_model_dict_to_proto()\"]\n  YAML --> PY";
        let g = parse_graph(src).unwrap();
        assert!(
            g.nodes[0]
                .label
                .contains("models-config/<model>/<env>.yaml"),
            "{}",
            g.nodes[0].label
        );
        let art = plain(src);
        assert!(art.contains("<model>") && art.contains("<env>"), "{art}");
        assert!(!art.contains("&lt;") && !art.contains("&gt;"), "{art}");
    }

    #[test]
    fn direct_push_sinks_decode_entities() {
        // Entities contain `;`, which split_statements treats as a separator, so
        // they reach a sink intact only inside quotes; assert through the real
        // parsers where such quoting works.
        let g = parse_state(
            "stateDiagram-v2\n  state \"work &lt;job&gt;\" as J\n  Idle --> Run: \"on &lt;go&gt;\"\n  Run: \"d &lt;e&gt;\"",
        )
        .unwrap();
        let node = |s: &str| g.nodes.iter().any(|n| n.label.contains(s));
        let edge = |s: &str| {
            g.edges
                .iter()
                .any(|e| e.label.as_deref().is_some_and(|l| l.contains(s)))
        };
        assert!(node("work <job>") && node("d <e>") && edge("on <go>"));
        assert!(!node("&lt;") && !edge("&lt;"));

        let (cg, _) = parse_class("classDiagram\n  A --> B : \"uses &lt;X&gt;\"").unwrap();
        assert!(cg.edges.iter().any(|e| {
            e.label
                .as_deref()
                .is_some_and(|l| l.contains("uses <X>") && !l.contains("&lt;"))
        }));

        let s = parse_sequence(
            "sequenceDiagram\n  A->>B: \"call &lt;svc&gt;\"\n  Note over A,B: \"memo &lt;o&gt;\"\n  alt \"c &lt;x&gt;\"\n    A->>B: ok\n  end",
        )
        .unwrap();
        assert!(s.items.iter().any(|it| matches!(it,
            SeqItem::Message { text: Some(t), .. } if t.contains("call <svc>") && !t.contains("&lt;"))));
        assert!(s.items.iter().any(|it| matches!(it,
            SeqItem::Note { text, .. } if text.contains("memo <o>") && !text.contains("&lt;"))));
        assert!(s.items.iter().any(|it| matches!(it,
            SeqItem::Divider { text } if text.contains("c <x>") && !text.contains("&lt;"))));

        // Class members and ER attributes have no clean quoted form (splitter
        // fragments unquoted `;`; ER drops quoted text as a comment), so exercise
        // those decodes at the finalizer directly.
        let mut member = ClassInfo::default();
        push_member(&mut member, "+run &lt;R&gt;");
        assert_eq!(member.attrs, vec!["+run <R>".to_string()]);
        let mut attr = ClassInfo::default();
        push_er_attribute(&mut attr, "string &lt;pk&gt;");
        assert_eq!(attr.attrs, vec!["string <pk>".to_string()]);
    }

    #[test]
    fn quoted_label_with_inner_brackets_is_one_node() {
        let g = parse_graph(
            "flowchart TD\n  IDs[\"<b>Token IDs</b><br/>[ 464, 3797 ]<br/><i>indices</i>\"]",
        )
        .unwrap();
        assert_eq!(g.nodes.len(), 1, "inner brackets must not split the node");
        assert_eq!(g.edges.len(), 0, "no phantom edges from <br/> + brackets");
        assert_eq!(g.nodes[0].label, "Token IDs [ 464, 3797 ] indices");
    }

    #[test]
    fn unquoted_label_with_embedded_quote_closes_at_bracket() {
        let g = parse_graph("flowchart TD\n  A[5\" pipe] --> B[24\" display]").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.nodes[0].label, "5\" pipe");
        assert_eq!(g.nodes[1].label, "24\" display");
    }

    #[test]
    fn quoted_label_with_inner_parens_is_one_node() {
        let g =
            parse_graph("flowchart TD\n  A[\"Tokenizer (BPE / WordPiece)\"] --> B[Done]").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.nodes[0].label, "Tokenizer (BPE / WordPiece)");
    }

    #[test]
    fn diagram_with_html_labels_renders_without_tag_artifacts() {
        let src = "flowchart TD\n  IDs[\"<b>3. Token IDs</b><br/>[ 464, 3797 ]<br/><i>indices</i>\"] --> Out[\"<b>done</b>\"]";
        let out = plain(src);
        assert!(!out.contains("<b>"), "raw HTML tag leaked:\n{out}");
        assert!(!out.contains("</"), "raw closing tag leaked:\n{out}");
        assert!(!out.contains("br/"), "phantom br artifact leaked:\n{out}");
        assert!(out.contains("Token IDs"), "label text missing:\n{out}");
    }

    #[test]
    fn ranks_ignore_back_edges() {
        let g = parse_graph("graph TD\n A-->B\n B-->C\n C-->A").unwrap();
        let r = compute_ranks(&g);
        let idx = |id: &str| g.index[id];
        assert_eq!(r[idx("A")], 0);
        assert_eq!(r[idx("B")], 1);
        assert_eq!(r[idx("C")], 2);
    }

    #[test]
    fn td_render_has_boxes_labels_and_arrow() {
        let out = plain("graph TD\n A[Start] --> B[End]");
        assert!(out.contains("Start"), "{out}");
        assert!(out.contains("End"), "{out}");
        assert!(out.contains('┌') || out.contains('╭'), "{out}");
        assert!(out.contains('▼'), "{out}");
    }

    #[test]
    fn edge_label_is_rendered() {
        let out = plain("graph TD\n A-->|yes| B");
        assert!(out.contains("yes"), "{out}");
    }

    #[test]
    fn lr_is_shorter_than_td_for_a_chain() {
        let chain = "A --> B --> C --> D";
        let td = render(&format!("graph TD\n {chain}"), &styles(), Some(120))
            .unwrap()
            .plain_lines
            .len();
        let lr = render(&format!("flowchart LR\n {chain}"), &styles(), Some(120))
            .unwrap()
            .plain_lines
            .len();
        assert!(lr < td, "expected LR ({lr}) shorter than TD ({td})");
    }

    #[test]
    fn unsupported_diagram_uses_fallback_box() {
        let out = plain("gantt\n title Plan\n section A\n task :a1, 2024-01-01, 30d");
        assert!(out.contains("mermaid: gantt"), "{out}");
        assert!(out.contains("Plan"), "{out}");
    }

    #[test]
    fn blank_source_returns_none() {
        assert!(render("   \n  ", &styles(), Some(80)).is_none());
    }

    #[test]
    fn inline_label_with_x_or_o_letters() {
        let g = parse_graph("graph TD\n A -- no exit --> B").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.edges[0].label.as_deref(), Some("no exit"));
    }

    #[test]
    fn wide_glyph_box_stays_aligned() {
        let lines = render("graph TD\n A[日本語ab]", &styles(), Some(120))
            .unwrap()
            .plain_lines;
        let widths: Vec<usize> = lines
            .iter()
            .filter(|l| !l.trim().is_empty())
            .map(|l| l.width())
            .collect();
        assert!(
            widths.windows(2).all(|w| w[0] == w[1]),
            "box rows must share one width: {widths:?}\n{lines:?}"
        );
        assert!(!lines.iter().any(|l| l.contains(CONT)), "sentinel leaked");
    }

    #[test]
    fn merge_has_single_arrowhead() {
        let out = plain("graph TD\n A[aaa] --> D[ddddddd]\n B[bb] --> D\n C[ccccc] --> D");
        let arrows = out.chars().filter(|&c| c == '▼').count();
        assert_eq!(arrows, 1, "merge edges share one arrowhead:\n{out}");
        assert!(!out.contains("▼▼"), "must not stack arrowheads:\n{out}");
    }

    #[test]
    fn long_label_wraps_without_truncation() {
        let out =
            plain("graph TD\n A[Check if the user has permission to access resource] --> B[Done]");
        assert!(out.contains("permission"), "{out}");
        assert!(out.contains("resource"), "{out}");
        assert!(!out.contains('…'), "should wrap, not truncate:\n{out}");
    }

    #[test]
    fn very_long_label_truncates_after_max_lines() {
        let long = "alpha ".repeat(40);
        let out = plain(&format!("graph TD\n A[{}] --> B[x]", long.trim()));
        assert!(out.contains('…'), "should truncate past max lines:\n{out}");
    }

    #[test]
    fn wrap_label_breaks_long_identifier_on_boundary() {
        let lines = wrap_label("mark_filter_restore_context", WRAP_WIDTH, MAX_LINES);
        // The first line ends on an identifier boundary, not a mid-segment slice.
        assert!(
            lines[0].ends_with('_'),
            "first line must end on a boundary: {lines:?}"
        );
        // Every break (all but the last line) lands on a boundary char.
        for line in &lines[..lines.len() - 1] {
            assert!(
                line.ends_with(LABEL_BREAK_CHARS),
                "line must break on a boundary: {line:?}"
            );
        }
        // Nothing is lost: the wrapped lines reconstruct the original word.
        assert_eq!(lines.concat(), "mark_filter_restore_context");
    }

    #[test]
    fn wrap_label_token_without_break_char_falls_back_per_char() {
        let token = "a".repeat(40);
        let lines = wrap_label(&token, WRAP_WIDTH, MAX_LINES);
        // No boundary char -> per-char hard break across multiple lines.
        assert!(lines.len() >= 2, "must hard-break: {lines:?}");
        // 40 narrow chars fit in <= MAX_LINES, so nothing is truncated or lost.
        assert_eq!(lines.concat(), token);
    }

    #[test]
    fn flowchart_long_identifier_breaks_on_boundary_not_mid_segment() {
        let out = plain("graph TD\n A[mark_filter_restore_context] --> B[Done]");
        // The boundary-respecting pieces are present in the rendered art; the
        // `wrap_label_breaks_long_identifier_on_boundary` unit test proves there
        // is no mid-segment slice (losslessly), so no offset-coupled guard here.
        assert!(out.contains("mark_filter_restore_"), "{out}");
        assert!(out.contains("context"), "{out}");
    }

    #[test]
    fn wrap_label_mixed_boundary_then_no_boundary_tail() {
        let token = String::from("ab_") + &"c".repeat(40);
        let lines = wrap_label(&token, WRAP_WIDTH, MAX_LINES);
        // The boundary is taken first ...
        assert!(
            lines[0].ends_with('_'),
            "first break on boundary: {lines:?}"
        );
        // ... then the long no-boundary tail falls back to a per-char break.
        assert!(
            lines[1..].iter().any(|l| !l.contains(LABEL_BREAK_CHARS)),
            "a later line must be a per-char break: {lines:?}"
        );
        // 43 cols < MAX_LINES*WRAP_WIDTH, so it must not truncate; fully lossless.
        assert_eq!(lines.concat(), token);
    }

    #[test]
    fn wrap_label_boundary_breaking_still_truncates_at_max_lines() {
        let id = ["segment"; 20].join("_");
        let lines = wrap_label(&id, WRAP_WIDTH, MAX_LINES);
        // The identifier far exceeds MAX_LINES*WRAP_WIDTH, so it truncates ...
        assert_eq!(lines.len(), MAX_LINES);
        // ... with the ellipsis still on the final line.
        assert!(
            lines.last().unwrap().ends_with('…'),
            "truncation must keep the ellipsis: {lines:?}"
        );
    }

    #[test]
    fn bt_flips_orientation() {
        let out = plain("flowchart BT\n A[first] --> B[second] --> C[third]");
        let lines: Vec<&str> = out.lines().collect();
        let row = |needle: &str| lines.iter().position(|l| l.contains(needle)).unwrap();
        assert!(
            row("third") < row("first"),
            "BT: 'third' should sit above 'first':\n{out}"
        );
    }

    #[test]
    fn rl_flips_orientation() {
        let out = plain("flowchart RL\n A[first] --> B[second] --> C[third]");
        let line = out.lines().find(|l| l.contains("first")).unwrap();
        assert!(
            line.find("third") < line.find("first"),
            "RL: 'third' should sit left of 'first':\n{out}"
        );
    }

    #[test]
    fn undirected_piped_label_has_no_arrowhead() {
        let out = plain("graph TD\n A ---|maybe| B");
        assert!(out.contains("maybe"), "{out}");
        assert!(
            !out.contains('▼'),
            "undirected link should not draw an arrow:\n{out}"
        );
    }

    #[test]
    fn chain_edges_are_straight() {
        let out = plain("graph TD\n A[aaaa] --> B[b] --> C[cccccccc]");
        for line in out.lines() {
            assert!(
                !line.contains('└') || !line.contains('┐'),
                "chain should not jog: {line:?}"
            );
        }
    }

    #[test]
    fn adversarial_chain_falls_back() {
        let mut src = String::from("graph TD\n");
        for i in 0..10_000 {
            src.push_str(&format!(" N{i} --> N{}\n", i + 1));
        }
        let out = plain(&src);
        assert!(out.contains("mermaid: graph"), "expected fallback:\n{out}");
    }

    #[test]
    fn single_statement_chain_over_cap_falls_back() {
        let mut src = String::from("graph LR\n ");
        for i in 0..10_000 {
            src.push_str(&format!("N{i}-->"));
        }
        src.push_str("N10000");
        let out = plain(&src);
        assert!(out.contains("mermaid: graph"), "expected fallback");
    }

    #[test]
    fn deep_chain_within_caps_renders() {
        let mut src = String::from("graph TD\n");
        for i in 0..100 {
            src.push_str(&format!(" N{i} --> N{}\n", i + 1));
        }
        let out = render(&src, &styles(), Some(200)).unwrap().plain_lines;
        let joined = out.join("\n");
        assert!(joined.contains("N0"), "{joined}");
        assert!(joined.contains("N100"), "{joined}");
        assert!(joined.contains('▼'), "{joined}");
    }

    #[test]
    fn fallback_styled_and_plain_widths_match() {
        let art = render("gantt\n title Plan\n a\n", &styles(), Some(120)).unwrap();
        assert_eq!(art.styled_lines.len(), art.plain_lines.len());
        let frame_w = art.plain_lines[0].width();
        for (styled, plain) in art.styled_lines.iter().zip(&art.plain_lines) {
            let styled_w: usize = styled
                .spans
                .iter()
                .map(|s| s.content.as_ref().width())
                .sum();
            assert_eq!(styled_w, plain.width(), "styled/plain widths diverge");
            assert_eq!(plain.width(), frame_w, "fallback box must be rectangular");
        }
    }

    #[test]
    fn over_wide_diagram_falls_back() {
        let src = "flowchart LR\n A[aaaaaaaaaaaaaaaaaaaa] --> B[bbbbbbbbbbbbbbbbbbbb] --> C[cccccccccccccccccccc]";
        let out = render(src, &styles(), Some(40)).unwrap().plain_lines;
        let joined = out.join("\n");
        assert!(
            joined.contains("mermaid: flowchart"),
            "expected fallback for over-wide diagram:\n{joined}"
        );
        let max_w = out.iter().map(|l| l.width()).max().unwrap_or(0);
        let fits = render(src, &styles(), Some(120)).unwrap().plain_lines;
        assert!(
            fits.iter().any(|l| l.contains('▶')),
            "same diagram should render when it fits"
        );
        assert!(max_w <= src.len(), "fallback width bounded by source");
    }

    #[test]
    fn too_wide_fallback_appends_hint_below_box() {
        let src = "flowchart LR\n A[aaaaaaaaaaaaaaaaaaaa] --> B[bbbbbbbbbbbbbbbbbbbb] --> C[cccccccccccccccccccc]";
        let out = render(src, &styles(), Some(40)).unwrap().plain_lines;
        let joined = out.join("\n");

        assert!(
            joined.contains("mermaid: flowchart"),
            "plain header:\n{joined}"
        );
        assert!(
            !joined.contains("(too wide)"),
            "header stays plain:\n{joined}"
        );
        assert!(
            joined.contains("flowchart LR"),
            "raw source kept:\n{joined}"
        );

        let bottom = out
            .iter()
            .position(|l| l.contains('╰'))
            .expect("box bottom");
        let note = out
            .iter()
            .position(|l| l.contains("too wide"))
            .expect("note row");
        assert!(note > bottom, "note must be below the box:\n{joined}");
        assert!(
            joined.contains("open the image"),
            "note points at the image:\n{joined}"
        );

        assert!(
            out.iter().all(|l| l.width() <= 40),
            "fits 40 cols:\n{joined}"
        );
    }

    #[test]
    fn unsupported_diagram_fallback_not_flagged_too_wide() {
        let out = plain("gantt\n title Plan\n section A\n task :a1, 2024-01-01, 30d");
        assert!(out.contains("mermaid: gantt"), "{out}");
        assert!(
            !out.contains("too wide"),
            "unsupported type is not a width problem:\n{out}"
        );
    }

    #[test]
    fn fitting_diagram_has_no_width_warning() {
        let out = plain("flowchart LR\n A[Start] --> B[End]");
        assert!(
            !out.contains("too wide"),
            "fitting diagram must not warn:\n{out}"
        );
        assert!(
            !out.contains("mermaid: flowchart"),
            "should draw art, not box:\n{out}"
        );
        assert!(out.contains('▶'), "should draw edges:\n{out}");
    }

    #[test]
    fn bidirectional_link_draws_both_arrowheads() {
        let lr = plain("flowchart LR\n A <--> B");
        assert!(lr.contains('◄') && lr.contains('▶'), "{lr}");
        let td = plain("graph TD\n A <--> B");
        assert!(td.contains('▲') && td.contains('▼'), "{td}");
    }

    #[test]
    fn reversed_arrow_swaps_edge_direction() {
        let g = parse_graph("graph TD\n A <-- B").unwrap();
        let idx = |id: &str| g.index[id];
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.edges[0].from, idx("B"));
        assert_eq!(g.edges[0].to, idx("A"));
        assert_eq!(g.edges[0].head_to, Head::Arrow);
        assert_eq!(g.edges[0].head_from, Head::None);
        let out = plain("graph TD\n A <-- B");
        let lines: Vec<&str> = out.lines().collect();
        let row = |needle: &str| lines.iter().position(|l| l.contains(needle)).unwrap();
        assert!(row("B") < row("A"), "B should rank above A:\n{out}");
    }

    #[test]
    fn semicolon_and_comment_survive_inside_quoted_label() {
        let g = parse_graph("graph TD\n A[\"wait; 50%% done\"] --> B").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.nodes[0].label, "wait; 50%% done");
    }

    #[test]
    fn comment_outside_quotes_is_stripped() {
        let g =
            parse_graph("graph TD %% main flow\n A --> B %% trailing\n %% full line\n").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges.len(), 1);
    }

    #[test]
    fn skip_edge_routes_around_intermediate_boxes() {
        let out = plain("graph TD\n A --> B\n B --> C\n A --> C");
        assert!(!out.contains('┼'), "no border corruption:\n{out}");
        assert!(
            out.contains('◄'),
            "skip edge enters target from lane:\n{out}"
        );
    }

    fn ordered_ranks(src: &str) -> (Graph, Vec<usize>, Vec<Vec<usize>>) {
        let g = parse_graph(src).unwrap();
        let ranks = compute_ranks(&g);
        let max_rank = *ranks.iter().max().unwrap();
        let mut by_rank: Vec<Vec<usize>> = vec![Vec::new(); max_rank + 1];
        for (idx, &r) in ranks.iter().enumerate() {
            by_rank[r].push(idx);
        }
        order_ranks(&mut by_rank, &g.edges, &ranks);
        (g, ranks, by_rank)
    }

    #[test]
    fn order_ranks_removes_avoidable_crossing() {
        let (g, ranks, by_rank) = ordered_ranks("graph TD\n C[ccc]\n D[ddd]\n A --> D\n B --> C");
        let mut pos = vec![0usize; g.nodes.len()];
        for row in &by_rank {
            for (i, &v) in row.iter().enumerate() {
                pos[v] = i;
            }
        }
        assert_eq!(count_crossings(&g.edges, &ranks, &pos), 0);
        let idx = |id: &str| g.index[id];
        assert!(pos[idx("D")] < pos[idx("C")], "D follows parent A leftward");
    }

    #[test]
    fn order_ranks_keeps_crossing_free_order() {
        let (g, ranks, by_rank) = ordered_ranks("graph TD\n A --> C\n B --> D");
        let idx = |id: &str| g.index[id];
        assert_eq!(by_rank[0], vec![idx("A"), idx("B")]);
        assert_eq!(by_rank[1], vec![idx("C"), idx("D")]);
        let mut pos = vec![0usize; g.nodes.len()];
        for row in &by_rank {
            for (i, &v) in row.iter().enumerate() {
                pos[v] = i;
            }
        }
        assert_eq!(count_crossings(&g.edges, &ranks, &pos), 0);
    }

    #[test]
    fn crossing_edges_render_untangled() {
        let out = plain("graph TD\n C[ccc]\n D[ddd]\n A --> D\n B --> C");
        let row = out
            .lines()
            .find(|l| l.contains("ccc") && l.contains("ddd"))
            .unwrap();
        assert!(
            row.find("ddd") < row.find("ccc"),
            "children reorder under their parents:\n{out}"
        );
        assert!(!out.contains('┼'), "{out}");
    }

    #[test]
    fn three_layer_weave_untangles() {
        let (g, ranks, by_rank) = ordered_ranks(
            "graph TD\n X[x]\n Y[y]\n A --> Y\n B --> X\n X --> Q\n Y --> P\n P[p]\n Q[q]",
        );
        let mut pos = vec![0usize; g.nodes.len()];
        for row in &by_rank {
            for (i, &v) in row.iter().enumerate() {
                pos[v] = i;
            }
        }
        assert_eq!(
            count_crossings(&g.edges, &ranks, &pos),
            0,
            "both layers untangle"
        );
    }

    #[test]
    fn unavoidable_crossing_gets_separate_bus_rows() {
        let crossing = plain("graph TD\n A --> D[ddd]\n A --> C[ccc]\n B --> C\n B --> D");
        let parallel = plain("graph TD\n A --> C[ccc]\n B --> D[ddd]");
        assert!(crossing.contains('┼'), "wire crossing renders:\n{crossing}");
        assert_eq!(
            crossing.lines().count(),
            parallel.lines().count() + 1,
            "crossing pair claims one extra bus row:\n{crossing}"
        );
        assert_eq!(
            crossing.chars().filter(|&c| c == '▼').count(),
            2,
            "{crossing}"
        );
    }

    #[test]
    fn fan_out_keeps_single_bus_row() {
        let out = plain("graph TD\n A --> C[ccc]\n A --> D[ddd]");
        let baseline = plain("graph TD\n A --> C[ccc]");
        assert_eq!(
            out.lines().count(),
            baseline.lines().count(),
            "shared-source jogs share one bus row:\n{out}"
        );
        assert!(!out.contains('┼'), "{out}");
    }

    #[test]
    fn shared_target_back_edges_share_one_lane() {
        let two = plain("graph TD\n A --> B\n B --> C\n B --> A\n C --> A");
        let one = plain("graph TD\n A --> B\n B --> C\n C --> A");
        assert_eq!(
            two.lines().map(|l| l.width()).max(),
            one.lines().map(|l| l.width()).max(),
            "shared-target back edges merge into one lane:\n{two}"
        );
        assert_eq!(two.matches('◄').count(), 1, "{two}");
    }

    #[test]
    fn distinct_back_edges_get_separate_lanes() {
        let split = plain("graph TD\n A --> B\n B --> C\n B --> A\n C --> B");
        let single = plain("graph TD\n A --> B\n B --> C\n C --> B");
        assert_eq!(split.matches('◄').count(), 2, "{split}");
        assert!(
            split.lines().map(|l| l.width()).max() > single.lines().map(|l| l.width()).max(),
            "overlapping unrelated back edges claim a second lane:\n{split}"
        );
    }

    #[test]
    fn fallback_wraps_long_lines_to_max_width() {
        let out = render(
            "gantt\n title a very long line that should wrap inside the fallback box nicely",
            &styles(),
            Some(40),
        )
        .unwrap()
        .plain_lines;
        assert!(out.iter().all(|l| l.width() <= 40), "{}", out.join("\n"));
        for line in &out[1..out.len() - 1] {
            assert!(
                line.starts_with('│') && line.ends_with('│'),
                "body rows keep both borders: {line:?}"
            );
        }
        assert!(out.join("\n").contains("nicely"), "{}", out.join("\n"));
    }

    #[test]
    fn class_renders_compartments() {
        let out = plain(
            "classDiagram\n class Animal {\n +int age\n +isMammal() bool\n }\n Animal <|-- Duck",
        );
        assert!(out.contains("Animal"), "{out}");
        assert!(out.contains("+int age"), "{out}");
        assert!(out.contains("+isMammal() bool"), "{out}");
        assert!(
            out.contains('├') && out.contains('┤'),
            "section rules:\n{out}"
        );
        let lines: Vec<&str> = out.lines().collect();
        let name = lines.iter().position(|l| l.contains("Animal")).unwrap();
        let attr = lines.iter().position(|l| l.contains("+int age")).unwrap();
        let method = lines
            .iter()
            .position(|l| l.contains("+isMammal() bool"))
            .unwrap();
        assert!(name < attr && attr < method, "{out}");
    }

    #[test]
    fn class_inheritance_triangle_at_parent() {
        let out = plain("classDiagram\n Animal <|-- Duck\n Animal <|-- Fish");
        assert!(out.contains('△'), "hollow triangle:\n{out}");
        let lines: Vec<&str> = out.lines().collect();
        let animal = lines.iter().position(|l| l.contains("Animal")).unwrap();
        let duck = lines.iter().position(|l| l.contains("Duck")).unwrap();
        assert!(animal < duck, "parent above child:\n{out}");
        let tri = lines.iter().position(|l| l.contains('△')).unwrap();
        assert!(
            tri >= animal && tri < duck,
            "triangle at parent end:\n{out}"
        );
    }

    #[test]
    fn class_realization_is_dotted_triangle() {
        let g = parse_class("classDiagram\n IShape <|.. Circle").unwrap().0;
        assert_eq!(g.edges[0].head_from, Head::Triangle);
        assert!(g.edges[0].line == LineKind::Dotted);
        let out = plain("classDiagram\n IShape <|.. Circle");
        assert!(out.contains('╎') || out.contains('╌'), "{out}");
    }

    #[test]
    fn class_composition_and_aggregation_diamonds() {
        let out = plain("classDiagram\n Car *-- Engine\n Pond o-- Duck");
        assert!(out.contains('◆'), "filled diamond:\n{out}");
        assert!(out.contains('◇'), "open diamond:\n{out}");
    }

    #[test]
    fn class_dependency_dotted_arrow() {
        let g = parse_class("classDiagram\n A ..> B").unwrap().0;
        assert_eq!(g.edges[0].head_to, Head::Arrow);
        assert!(g.edges[0].line == LineKind::Dotted);
    }

    #[test]
    fn class_colon_members_merge_with_block() {
        let out = plain(
            "classDiagram\n class Duck {\n +swim()\n }\n Duck : +String beakColor\n S --> Duck",
        );
        assert!(out.contains("+swim()"), "{out}");
        assert!(out.contains("+String beakColor"), "{out}");
    }

    #[test]
    fn class_annotation_renders_guillemets() {
        let out = plain("classDiagram\n <<interface>> Shape\n Shape <|.. Circle");
        assert!(out.contains("«interface»"), "{out}");
    }

    #[test]
    fn class_generics_display_as_angle_brackets() {
        let out = plain("classDiagram\n Shape~T~ : +area() T\n S --> Shape~T~");
        assert!(out.contains("Shape<T>"), "{out}");
        assert!(!out.contains('~'), "{out}");
    }

    #[test]
    fn class_cardinalities_fold_into_label() {
        let out = plain("classDiagram\n Student \"many\" --> \"1\" School : attends");
        assert!(out.contains("many attends 1"), "{out}");
    }

    #[test]
    fn class_from_end_head_survives_fan_out_jog() {
        let out = plain("classDiagram\n Animal <|-- Duck\n Animal <|-- Fish\n Animal <|-- Cow");
        assert_eq!(
            out.matches('△').count() + out.matches('▽').count(),
            1,
            "merged from-end glyph on the parent border:\n{out}"
        );
    }

    #[test]
    fn class_empty_class_is_plain_titled_box() {
        let out = plain("classDiagram\n class Loner\n A --> Loner");
        assert!(out.contains("Loner"), "{out}");
    }

    #[test]
    fn class_unknown_statement_falls_back() {
        let out = plain("classDiagram\n A --> B\n total garbage here");
        assert!(out.contains("mermaid: classDiagram"), "{out}");
    }

    #[test]
    fn class_member_cap_ellipsis() {
        let mut src = String::from("classDiagram\n class Big {\n");
        for i in 0..12 {
            src.push_str(&format!(" +field{i}\n"));
        }
        src.push_str(" }\n A --> Big");
        let out = plain(&src);
        assert!(out.contains("+field7"), "{out}");
        assert!(!out.contains("+field9"), "{out}");
        assert!(out.contains('…'), "{out}");
    }

    #[test]
    fn class_direction_lr() {
        let out = plain("classDiagram\n direction LR\n A --> B");
        let line = out.lines().find(|l| l.contains('A')).unwrap();
        assert!(line.contains('B'), "{out}");
    }

    #[test]
    fn er_renders_entities_and_relationship_labels() {
        let out = plain(
            "erDiagram\n CUSTOMER ||--o{ ORDER : places\n CUSTOMER {\n string name PK \"full name\"\n int custNumber\n }",
        );
        assert!(out.contains("CUSTOMER"), "{out}");
        assert!(out.contains("ORDER"), "{out}");
        assert!(out.contains("string name PK"), "{out}");
        assert!(
            !out.contains("full name"),
            "attribute comments dropped:\n{out}"
        );
        assert!(out.contains("1 places 0..*"), "{out}");
        assert!(out.contains('├'), "attribute compartment rule:\n{out}");
    }

    #[test]
    fn er_cardinality_map() {
        let cases = [
            ("||--||", "1", "1"),
            ("|o--o|", "0..1", "0..1"),
            ("}o--o{", "0..*", "0..*"),
            ("}|--|{", "1..*", "1..*"),
            ("||--o{", "1", "0..*"),
        ];
        for (op, l, r) in cases {
            let (cl, cr, line) = parse_er_op(op).unwrap();
            assert_eq!((cl, cr), (l, r), "{op}");
            assert!(line == LineKind::Solid);
        }
        assert!(parse_er_op("||..o{").unwrap().2 == LineKind::Dotted);
        assert!(parse_er_op("||==o{").is_none());
        assert!(parse_er_op("garbage").is_none());
    }

    #[test]
    fn er_non_identifying_renders_dotted() {
        let out = plain("erDiagram\n A ||..o{ B : uses");
        assert!(out.contains('╎') || out.contains('╌'), "{out}");
    }

    #[test]
    fn er_relationships_have_no_arrowheads() {
        let out = plain("erDiagram\n A ||--o{ B : has");
        for head in ['▼', '▲', '◄', '▶', '△', '◆', '◇'] {
            assert!(!out.contains(head), "{head} in:\n{out}");
        }
    }

    #[test]
    fn er_entity_alias_label() {
        let out = plain("erDiagram\n p[Person] ||--o{ a[\"Bank Account\"] : owns");
        assert!(out.contains("Person"), "{out}");
        assert!(out.contains("Bank Account"), "{out}");
    }

    #[test]
    fn er_unquoted_label_and_bare_entity_decl() {
        let g = parse_er("erDiagram\n LONER\n A ||--|| B : linked")
            .unwrap()
            .0;
        assert_eq!(g.nodes.len(), 3);
        let out = plain("erDiagram\n LONER\n A ||--|| B : linked");
        assert!(out.contains("LONER"), "{out}");
        assert!(out.contains("1 linked 1"), "{out}");
    }

    #[test]
    fn er_attribute_cap_ellipsis() {
        let mut src = String::from("erDiagram\n BIG {\n");
        for i in 0..12 {
            src.push_str(&format!(" int f{i}\n"));
        }
        src.push_str(" }\n BIG ||--|| OTHER : x");
        let out = plain(&src);
        assert!(out.contains("int f7"), "{out}");
        assert!(!out.contains("int f9"), "{out}");
        assert!(out.contains('…'), "{out}");
    }

    #[test]
    fn er_unknown_statement_falls_back() {
        let out = plain("erDiagram\n A ||--|| B : ok\n utter nonsense statement");
        assert!(out.contains("mermaid: erDiagram"), "{out}");
    }

    #[test]
    fn subgraph_renders_titled_frame() {
        let out = plain(
            "graph TD\n S[Start] --> one\n subgraph one [Group One]\n A --> B\n end\n one --> E[End]",
        );
        assert!(out.contains(" Group One "), "{out}");
        let lines: Vec<&str> = out.lines().collect();
        let title = lines.iter().position(|l| l.contains("Group One")).unwrap();
        let a = lines.iter().position(|l| l.contains("│ A │")).unwrap();
        let b = lines.iter().position(|l| l.contains("│ B │")).unwrap();
        let frame_close = lines
            .iter()
            .rposition(|l| l.trim_start().starts_with('└'))
            .unwrap();
        assert!(title < a && a < b && b <= frame_close, "{out}");
        assert!(out.contains("Start") && out.contains("End"), "{out}");
        assert_eq!(out.matches('▼').count(), 3, "{out}");
    }

    #[test]
    fn subgraph_edge_between_groups() {
        let out = plain(
            "graph TD\n subgraph api [API]\n A1 --> A2\n end\n subgraph db [Storage]\n B1\n end\n api --> db",
        );
        assert!(out.contains(" API "), "{out}");
        assert!(out.contains(" Storage "), "{out}");
        let lines: Vec<&str> = out.lines().collect();
        let api = lines.iter().position(|l| l.contains("API")).unwrap();
        let db = lines.iter().position(|l| l.contains("Storage")).unwrap();
        assert!(api < db, "API frame ranks above Storage:\n{out}");
    }

    #[test]
    fn subgraph_nested_frames() {
        let out = plain(
            "graph TD\n subgraph outer [Outer]\n subgraph inner [Inner]\n X --> Y\n end\n W --> X\n end\n S --> outer",
        );
        assert!(out.contains(" Outer "), "{out}");
        assert!(out.contains(" Inner "), "{out}");
        let lines: Vec<&str> = out.lines().collect();
        let outer = lines.iter().position(|l| l.contains("Outer")).unwrap();
        let inner = lines.iter().position(|l| l.contains("Inner")).unwrap();
        assert!(outer < inner, "{out}");
    }

    #[test]
    fn subgraph_cross_member_edge_attaches_to_frame() {
        let out = plain("graph LR\n S --> A\n subgraph g [Workers]\n A --> B\n end\n B --> T");
        assert!(out.contains(" Workers "), "{out}");
        assert!(out.contains('S') && out.contains('T'), "{out}");
        assert_eq!(out.matches('▶').count(), 3, "{out}");
        let row = out.lines().find(|l| l.contains("│ A ├")).unwrap();
        assert!(
            row.find('S') < row.find('A'),
            "A stays outside the group (first definition wins):\n{out}"
        );
    }

    #[test]
    fn subgraph_id_referenced_before_declaration() {
        let g = parse_graph("graph TD\n X --> two\n subgraph two\n C --> D\n end").unwrap();
        assert_eq!(g.groups.len(), 1);
        let out = plain("graph TD\n X --> two\n subgraph two\n C --> D\n end");
        assert!(out.contains(" two "), "frame titled by id:\n{out}");
        assert!(out.contains("│ C │"), "{out}");
    }

    #[test]
    fn subgraph_quoted_and_plain_titles() {
        let out = plain("graph TD\n subgraph \"My Stuff\"\n A\n end\n S --> A");
        assert!(out.contains(" My Stuff "), "{out}");
        let out2 = plain("graph TD\n subgraph batch jobs\n B\n end\n S --> B");
        assert!(out2.contains(" batch jobs "), "{out2}");
        let out3 = plain("graph TD\n subgraph \"a &lt;b&gt;\"\n C\n end\n S --> C");
        assert!(out3.contains("a <b>") && !out3.contains("&lt;"), "{out3}");
    }

    #[test]
    fn subgraph_empty_is_dropped() {
        let out = plain("graph TD\n subgraph ghost\n end\n A --> B");
        assert!(!out.contains("ghost"), "{out}");
        assert!(out.contains('▼'), "{out}");
    }

    #[test]
    fn subgraph_bt_flips_frame_and_contents() {
        let out = plain("flowchart BT\n S --> one\n subgraph one [Up]\n A --> B\n end");
        assert!(out.contains(" Up "), "{out}");
        let lines: Vec<&str> = out.lines().collect();
        let row = |needle: &str| lines.iter().position(|l| l.contains(needle)).unwrap();
        assert!(row("│ B │") < row("│ A │"), "contents flip with BT:\n{out}");
        assert!(row(" Up ") < row("S"), "frame above source in BT:\n{out}");
        assert!(out.contains('▲'), "{out}");
    }

    #[test]
    fn subgraph_depth_over_cap_falls_back() {
        let mut src = String::from("graph TD\n");
        for i in 0..8 {
            src.push_str(&format!(" subgraph g{i}\n"));
        }
        src.push_str(" A --> B\n");
        for _ in 0..8 {
            src.push_str(" end\n");
        }
        let out = plain(&src);
        assert!(out.contains("mermaid: graph"), "{out}");
    }

    #[test]
    fn subgraph_groupless_path_unchanged() {
        let g = parse_graph("graph TD\n A --> B").unwrap();
        assert!(g.groups.is_empty());
    }

    #[test]
    fn fan_out_creates_cross_product_edges() {
        let g = parse_graph("graph TD\n A & B --> C & D").unwrap();
        assert_eq!(g.nodes.len(), 4);
        assert_eq!(g.edges.len(), 4);
        let idx = |id: &str| g.index[id];
        let has = |f: &str, t: &str| g.edges.iter().any(|e| e.from == idx(f) && e.to == idx(t));
        assert!(has("A", "C") && has("A", "D") && has("B", "C") && has("B", "D"));
        let out = plain("graph TD\n A & B --> C & D");
        assert_eq!(out.chars().filter(|&c| c == '▼').count(), 2, "{out}");
    }

    #[test]
    fn fan_out_in_chain() {
        let g = parse_graph("graph LR\n A & B --> C --> D").unwrap();
        assert_eq!(g.edges.len(), 3);
    }

    #[test]
    fn fan_out_with_reversed_arrow() {
        let g = parse_graph("graph TD\n A & B <-- C").unwrap();
        let idx = |id: &str| g.index[id];
        assert_eq!(g.edges.len(), 2);
        assert!(g.edges.iter().all(|e| e.from == idx("C")));
        assert!(g.edges.iter().all(|e| e.head_to == Head::Arrow));
    }

    #[test]
    fn circle_and_cross_endings_create_no_phantom_nodes() {
        let g = parse_graph("graph TD\n A --o B\n C --x D").unwrap();
        assert_eq!(g.nodes.len(), 4, "no phantom o/x nodes");
        assert!(!g.index.contains_key("o"));
        assert!(!g.index.contains_key("x"));
        assert_eq!(g.edges[0].head_to, Head::Circle);
        assert_eq!(g.edges[1].head_to, Head::Cross);
        let out = plain("graph TD\n A --o B");
        assert!(out.contains('o'), "circle head rendered:\n{out}");
    }

    #[test]
    fn left_endings_decorate_without_reversing() {
        let g = parse_graph("graph TD\n A o-- B\n C x-- D").unwrap();
        let idx = |id: &str| g.index[id];
        assert_eq!(g.edges[0].from, idx("A"));
        assert_eq!(g.edges[0].to, idx("B"));
        assert_eq!(g.edges[0].head_from, Head::Circle);
        assert_eq!(g.edges[1].head_from, Head::Cross);
        assert_eq!(g.edges[0].head_to, Head::None);
    }

    #[test]
    fn reversed_arrow_with_end_marker_swaps_direction() {
        let g = parse_graph("graph TD\n A <--o B\n C <--x D").unwrap();
        let idx = |id: &str| g.index[id];
        assert_eq!(g.edges[0].from, idx("B"));
        assert_eq!(g.edges[0].to, idx("A"));
        assert_eq!(g.edges[0].head_to, Head::Arrow);
        assert_eq!(g.edges[0].head_from, Head::Circle);
        assert_eq!(g.edges[1].from, idx("D"));
        assert_eq!(g.edges[1].to, idx("C"));
        assert_eq!(g.edges[1].head_from, Head::Cross);
        let plain_rev = plain("graph TD\n A <--o B");
        let lines: Vec<&str> = plain_rev.lines().collect();
        let row = |needle: &str| lines.iter().position(|l| l.contains(needle)).unwrap();
        assert!(
            row("B") < row("A"),
            "ranks match plain <-- reversal:\n{plain_rev}"
        );
    }

    #[test]
    fn both_end_markers_parse() {
        let g = parse_graph("graph TD\n A o--o B\n C x--x D").unwrap();
        assert_eq!(g.edges[0].head_from, Head::Circle);
        assert_eq!(g.edges[0].head_to, Head::Circle);
        assert_eq!(g.edges[1].head_from, Head::Cross);
        assert_eq!(g.edges[1].head_to, Head::Cross);
        assert_eq!(g.nodes.len(), 4);
    }

    #[test]
    fn dotted_and_thick_lines_render_distinctly() {
        let dotted = plain("graph TD\n A -.-> B");
        assert!(dotted.contains('╎'), "dotted vertical:\n{dotted}");
        let thick = plain("graph TD\n A ==> B");
        assert!(thick.contains('┃'), "thick vertical:\n{thick}");
        let solid = plain("graph TD\n A --> B");
        assert!(
            !solid.contains('╎') && !solid.contains('┃'),
            "solid unchanged:\n{solid}"
        );
    }

    #[test]
    fn dotted_label_form_renders_dashed() {
        let out = plain("graph LR\n A -. maybe .-> B");
        assert!(out.contains('╌'), "{out}");
        assert!(out.contains("maybe"), "{out}");
    }

    #[test]
    fn thick_jog_uses_thick_corners() {
        let out = plain("graph TD\n A[aaaaaaa] ==> B\n A ==> C[ccccccc]");
        assert!(
            out.contains('┏') || out.contains('┓') || out.contains('┳'),
            "thick corners on jog:\n{out}"
        );
    }

    #[test]
    fn state_diagram_renders_states_and_transitions() {
        let out =
            plain("stateDiagram-v2\n [*] --> Idle\n Idle --> Running: start\n Running --> [*]");
        assert!(out.contains("Idle"), "{out}");
        assert!(out.contains("Running"), "{out}");
        assert!(out.contains("start"), "{out}");
        assert!(out.contains('▼'), "{out}");
        assert_eq!(
            out.matches('●').count(),
            2,
            "distinct start and end markers:\n{out}"
        );
        let lines: Vec<&str> = out.lines().collect();
        let first_dot = lines.iter().position(|l| l.contains('●')).unwrap();
        let last_dot = lines.iter().rposition(|l| l.contains('●')).unwrap();
        let idle = lines.iter().position(|l| l.contains("Idle")).unwrap();
        assert!(first_dot < idle && idle < last_dot, "{out}");
    }

    #[test]
    fn state_v1_header_renders() {
        let out = plain("stateDiagram\n A --> B");
        assert!(out.contains('▼'), "{out}");
    }

    #[test]
    fn state_boxes_are_rounded() {
        let out = plain("stateDiagram-v2\n A --> B");
        assert!(out.contains('╭'), "{out}");
        assert!(!out.contains('┌'), "states render rounded:\n{out}");
    }

    #[test]
    fn state_alias_label_renders() {
        let out = plain("stateDiagram-v2\n state \"Waiting for input\" as W\n W --> Done");
        assert!(out.contains("Waiting for input"), "{out}");
    }

    #[test]
    fn state_choice_parses_as_diamond() {
        let g = parse_state(
            "stateDiagram-v2\n state c <<choice>>\n A --> c\n c --> B: yes\n c --> D: no",
        )
        .unwrap();
        assert!(g.nodes[g.index["c"]].shape == Shape::Diamond);
        assert_eq!(g.edges.len(), 3);
    }

    #[test]
    fn state_description_sets_label() {
        let out = plain("stateDiagram-v2\n s2 : waits patiently\n A --> s2");
        assert!(out.contains("waits patiently"), "{out}");
    }

    #[test]
    fn state_direction_lr() {
        let out = plain("stateDiagram-v2\n direction LR\n A --> B --> C");
        let td = plain("stateDiagram-v2\n A --> B");
        assert!(
            out.lines().count() <= td.lines().count() + 2,
            "LR stays flat:\n{out}"
        );
        let line = out.lines().find(|l| l.contains('A')).unwrap();
        assert!(line.contains('B'), "A and B share a row in LR:\n{out}");
    }

    #[test]
    fn state_composite_contents_render_flat() {
        let out = plain("stateDiagram-v2\n state Active {\n A --> B\n }\n Active --> Done");
        assert!(out.contains("Active"), "{out}");
        assert!(out.contains('A') && out.contains('B'), "{out}");
        assert!(out.contains("Done"), "{out}");
    }

    #[test]
    fn state_notes_are_skipped() {
        let out = plain(
            "stateDiagram-v2\n A --> B\n note right of A: inline note\n note left of B\n block text\n end note",
        );
        assert!(out.contains('▼'), "{out}");
        assert!(!out.contains("note"), "{out}");
        assert!(!out.contains("block text"), "{out}");
    }

    #[test]
    fn state_back_transition_uses_lane() {
        let out = plain("stateDiagram-v2\n A --> B\n B --> C\n C --> B: retry");
        assert!(out.contains('◄'), "{out}");
        assert!(out.contains("retry"), "{out}");
    }

    #[test]
    fn state_unknown_statement_falls_back() {
        let out = plain("stateDiagram-v2\n A --> B\n some garbage line");
        assert!(out.contains("mermaid: stateDiagram-v2"), "{out}");
    }

    #[test]
    fn state_over_cap_falls_back() {
        let mut src = String::from("stateDiagram-v2\n");
        for i in 0..600 {
            src.push_str(&format!(" S{i} --> S{}\n", i + 1));
        }
        let out = plain(&src);
        assert!(out.contains("mermaid: stateDiagram-v2"), "{out}");
    }

    #[test]
    fn state_extra_dash_arrow_tolerated() {
        let g = parse_state("stateDiagram-v2\n A ---> B").unwrap();
        assert_eq!(g.edges.len(), 1);
        assert_eq!(g.nodes.len(), 2);
    }

    #[test]
    fn state_description_preserves_choice_shape() {
        let g = parse_state(
            "stateDiagram-v2\n state c <<choice>>\n c : pick a path\n A --> c\n c --> B",
        )
        .unwrap();
        assert!(g.nodes[g.index["c"]].shape == Shape::Diamond);
        assert_eq!(g.nodes[g.index["c"]].label, "pick a path");
        let g2 =
            parse_state("stateDiagram-v2\n state c <<choice>>\n state \"pick\" as c\n A --> c")
                .unwrap();
        assert!(g2.nodes[g2.index["c"]].shape == Shape::Diamond);
        assert_eq!(g2.nodes[g2.index["c"]].label, "pick");
    }

    #[test]
    fn state_chained_transitions_parse_as_separate_edges() {
        let g = parse_state("stateDiagram-v2\n A --> B --> C").unwrap();
        assert_eq!(g.nodes.len(), 3, "three distinct states");
        assert_eq!(g.edges.len(), 2, "two edges");
        assert!(g.index.contains_key("B"));
        assert!(g.index.contains_key("C"));
        assert!(
            !g.nodes.iter().any(|n| n.label.contains("-->")),
            "no node swallows the arrow"
        );
        let idx = |id: &str| g.index[id];
        assert!(
            g.edges
                .iter()
                .any(|e| e.from == idx("A") && e.to == idx("B"))
        );
        assert!(
            g.edges
                .iter()
                .any(|e| e.from == idx("B") && e.to == idx("C"))
        );
    }

    #[test]
    fn state_chain_with_markers_and_label() {
        let g = parse_state("stateDiagram-v2\n [*] --> A --> B: done").unwrap();
        assert_eq!(g.edges.len(), 2);
        assert!(g.edges.iter().any(|e| e.label.as_deref() == Some("done")));
        let out = plain("stateDiagram-v2\n [*] --> A --> B: done");
        assert!(out.contains('●'), "{out}");
        assert!(out.contains("done"), "{out}");
    }

    #[test]
    fn state_dangling_chain_falls_back() {
        let out = plain("stateDiagram-v2\n A --> B -->");
        assert!(out.contains("mermaid: stateDiagram-v2"), "{out}");
    }

    #[test]
    fn sequence_renders_actors_and_messages() {
        let out = plain("sequenceDiagram\n Alice->>Bob: Hello Bob\n Bob-->>Alice: Hi Alice");
        assert!(out.contains("Alice"), "{out}");
        assert!(out.contains("Bob"), "{out}");
        assert!(out.contains("Hello Bob"), "{out}");
        assert!(out.contains('▶'), "solid call arrow:\n{out}");
        assert!(out.contains('◄'), "reply arrow:\n{out}");
        assert!(out.contains('╌'), "reply line is dashed:\n{out}");
        assert_eq!(
            out.matches("│ Alice │").count(),
            2,
            "actor boxes repeat at bottom:\n{out}"
        );
    }

    #[test]
    fn sequence_participant_as_label() {
        let out = plain(
            "sequenceDiagram\n participant C as Client\n participant S as Server\n C->>S: GET /",
        );
        assert!(out.contains("Client"), "{out}");
        assert!(out.contains("Server"), "{out}");
    }

    #[test]
    fn sequence_declared_order_wins() {
        let out = plain("sequenceDiagram\n participant B\n participant A\n A->>B: hi");
        let line = out.lines().nth(1).unwrap();
        assert!(
            line.find('B') < line.find('A'),
            "B declared first sits left:\n{out}"
        );
    }

    #[test]
    fn sequence_self_message_loops() {
        let out = plain("sequenceDiagram\n A->>A: think");
        assert!(out.contains('╮'), "{out}");
        assert!(out.contains('╯'), "{out}");
        assert!(out.contains("think"), "{out}");
    }

    #[test]
    fn sequence_cross_head() {
        let out = plain("sequenceDiagram\n A-x B: lost");
        assert!(out.contains('×'), "{out}");
    }

    #[test]
    fn sequence_note_over_renders_box() {
        let out = plain("sequenceDiagram\n A->>B: hi\n Note over A,B: happy path");
        assert!(out.contains("happy path"), "{out}");
    }

    #[test]
    fn sequence_autonumber_prefixes_messages() {
        let out = plain("sequenceDiagram\n autonumber\n A->>B: one\n B->>A: two");
        assert!(out.contains("1. one"), "{out}");
        assert!(out.contains("2. two"), "{out}");
    }

    #[test]
    fn sequence_loop_renders_divider_and_end() {
        let out = plain("sequenceDiagram\n A->>B: hi\n loop retry x3\n A->>B: again\n end");
        assert!(out.contains("loop retry x3"), "{out}");
        assert!(out.contains(" end "), "{out}");
    }

    #[test]
    fn sequence_rect_block_is_invisible() {
        let out = plain("sequenceDiagram\n rect rgb(0,0,0)\n A->>B: hi\n end");
        assert!(!out.contains("rect"), "{out}");
        assert!(!out.contains(" end "), "rect end is silent:\n{out}");
    }

    #[test]
    fn sequence_box_end_does_not_close_enclosing_block() {
        let out = plain(
            "sequenceDiagram\n loop l1\n box g\n participant A\n end\n A->>B: hi\n A->>B: bye\n end",
        );
        assert_eq!(
            out.matches(" end ").count(),
            1,
            "box end is silent, loop end renders:\n{out}"
        );
        let lines: Vec<&str> = out.lines().collect();
        let row = |needle: &str| lines.iter().position(|l| l.contains(needle)).unwrap();
        assert!(
            row("loop l1") < row("hi") && row("bye") < row(" end "),
            "messages stay inside the loop:\n{out}"
        );
        assert!(!out.contains("box"), "{out}");
    }

    #[test]
    fn sequence_critical_option_renders_dividers() {
        let out = plain(
            "sequenceDiagram\n critical connect\n A->>B: try\n option timeout\n A->>A: log\n end",
        );
        assert!(
            out.contains("critical connect"),
            "valid critical diagram renders:\n{out}"
        );
        assert!(out.contains("option timeout"), "{out}");
        assert!(out.contains(" end "), "{out}");
    }

    #[test]
    fn sequence_long_label_widens_gap() {
        let out = plain(
            "sequenceDiagram\n A->>B: a very long message label that needs room\n B-->>A: ok",
        );
        assert!(
            out.contains("a very long message label that needs room"),
            "{out}"
        );
    }

    #[test]
    fn mixed_solid_and_dotted_bus_stays_light() {
        let out = plain("graph TD\n A --> C\n B -.-> C");
        assert!(out.contains('╌'), "dotted branch survives:\n{out}");
        assert!(out.contains('─'), "solid branch survives:\n{out}");
        assert!(out.contains('┬'), "shared merge cell stays light:\n{out}");
    }

    #[test]
    fn box_borders_stay_light_next_to_styled_edges() {
        let out = plain("graph TD\n A ==> B");
        assert!(out.contains('┌') && out.contains('└'), "{out}");
        assert!(!out.contains('┏'), "borders not restyled:\n{out}");
    }

    #[test]
    fn self_loop_renders_below_box() {
        let out = plain("graph TD\n A --> A");
        assert!(out.contains('╰') && out.contains('╯'), "{out}");
        assert!(out.contains('▲'), "loop returns into the box:\n{out}");
    }

    #[test]
    fn self_loop_label_renders() {
        let out = plain("graph TD\n A -->|again| A");
        assert!(out.contains("again"), "{out}");
    }

    #[test]
    fn self_loop_coexists_with_forward_edge() {
        let out = plain("graph TD\n A --> A\n A --> B");
        assert!(out.contains('▲'), "{out}");
        assert!(out.contains('▼'), "{out}");
        assert!(out.contains('B'), "{out}");
        assert!(!out.contains('┼'), "{out}");
    }

    #[test]
    fn self_loop_flips_with_bt() {
        let out = plain("flowchart BT\n A --> A\n A --> B");
        assert!(out.contains('▼'), "flipped loop head points down:\n{out}");
        assert!(out.contains('╭') || out.contains('╮'), "{out}");
    }

    #[test]
    fn self_loop_in_lr() {
        let out = plain("flowchart LR\n A --> A\n A --> B");
        assert!(out.contains('▲'), "{out}");
        assert!(out.contains('▶'), "{out}");
    }

    #[test]
    fn inline_o_word_label_still_parses_as_label() {
        let g = parse_graph("graph TD\n A -- or else --> B").unwrap();
        assert_eq!(g.nodes.len(), 2);
        assert_eq!(g.edges[0].label.as_deref(), Some("or else"));
    }

    #[test]
    fn sequence_unparseable_arrow_falls_back() {
        let out = plain("sequenceDiagram\n ->>B: orphan");
        assert!(out.contains("mermaid: sequenceDiagram"), "{out}");
    }

    #[test]
    fn sequence_unknown_statement_falls_back() {
        let out = plain("sequenceDiagram\n A->>B: hi\n garbage statement here");
        assert!(out.contains("mermaid: sequenceDiagram"), "{out}");
    }

    #[test]
    fn sequence_over_wide_falls_back() {
        let out = render(
            "sequenceDiagram\n A->>B: this label is far wider than the available pane width",
            &styles(),
            Some(30),
        )
        .unwrap()
        .plain_lines
        .join("\n");
        assert!(out.contains("mermaid: sequenceDiagram"), "{out}");
    }

    #[test]
    fn sequence_over_cap_falls_back() {
        let mut src = String::from("sequenceDiagram\n");
        for i in 0..600 {
            src.push_str(&format!(" A->>B: msg {i}\n"));
        }
        let out = plain(&src);
        assert!(out.contains("mermaid: sequenceDiagram"), "{out}");
    }

    #[test]
    fn sequence_activation_markers_are_stripped() {
        let out = plain("sequenceDiagram\n A->>+B: call\n B-->>-A: return");
        assert!(out.contains("call"), "{out}");
        assert!(out.contains("return"), "{out}");
        assert!(!out.contains('+'), "{out}");
    }

    #[test]
    fn sequence_rows_are_rectangular_and_sentinel_free() {
        let out = plain("sequenceDiagram\n Alice->>Bob: hi\n Note over Alice: solo note");
        assert!(!out.contains(CONT), "sentinel leaked:\n{out}");
        assert!(out.contains("solo note"), "{out}");
    }
}
