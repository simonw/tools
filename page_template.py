"""Shared HTML chrome for generated pages (homepage, category pages).

Centralises the base + navigation + directory CSS so the homepage and the
category pages stay visually consistent without duplicating styles.
"""

from __future__ import annotations

STYLE = """
        body {
            font-family: "Helvetica Neue", helvetica, sans-serif;
            line-height: 1.4;
            margin: 0;
            padding: 0;
        }
        h1 {
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.4em;
        }
        h2 {
            margin-top: 1.5em;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        code {
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
            padding: 0.2em 0.4em;
        }
        nav {
            text-align: left;
            background: linear-gradient(to bottom, rgb(154, 103, 175) 0%, rgb(96, 72, 129) 49%, rgb(100, 67, 130) 100%);
            color: white;
        }
        nav p {
            display: flex;
            justify-content: space-between;
            margin: 0;
            padding: 4px 2em;
        }
        nav a:link,
        nav a:visited,
        nav a:hover,
        nav a:focus,
        nav a:active {
            color: white;
            text-decoration: none;
        }
        section.body {
            padding: 0.5em 2em;
            max-width: 800px;
        }
        @media (max-width: 600px) {
            section.body {
                padding: 0em 1em;
            }
            nav p {
                padding: 4px 1em;
            }
        }
        html {
            scroll-behavior: smooth;
        }
        .breadcrumb {
            font-size: 0.9em;
            color: #777;
            margin: 0.5em 0 1em;
        }
        .directory {
            margin-top: 1em;
        }
        .dir-intro {
            color: #444;
            font-size: 0.95em;
            max-width: 48em;
            margin: 0.5em 0 1em;
        }
        .dir-heading {
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.35em;
            color: #4a2f63;
            border-bottom: 2px solid #9a67af;
            padding-bottom: 2px;
            margin: 1.4em 0 0.8em;
        }
        .dir-toplevel {
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.1em;
            color: #fff;
            background: linear-gradient(to bottom, rgb(154, 103, 175) 0%, rgb(100, 67, 130) 100%);
            padding: 4px 10px;
            margin: 1.5em 0 0.9em;
            border-radius: 2px;
            scroll-margin-top: 8px;
        }
        .dir-toplevel a { color: #fff; }
        .yh-index {
            column-width: 330px;
            column-gap: 44px;
            margin: 0.5em 0 1em;
        }
        .yh-cat {
            break-inside: avoid;
            -webkit-column-break-inside: avoid;
            display: inline-block;
            width: 100%;
            margin: 0 0 1.1em;
            vertical-align: top;
        }
        .yh-cat h3 {
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.1em;
            margin: 0 0 0.15em;
        }
        .yh-cat h3 a {
            color: #4a2f63;
            font-weight: bold;
        }
        .yh-xtra {
            color: #cc0000;
            font-size: 0.7em;
            font-weight: normal;
            vertical-align: super;
        }
        .yh-cat p {
            margin: 0;
            font-size: 0.9em;
            line-height: 1.45;
            color: #555;
        }
        .browse-all-link {
            margin: 0.5em 0 0;
            font-size: 0.95em;
        }
        .dir-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 0 0 1.5em;
        }
        .dir-chip {
            font-size: 0.82em;
            background: #f0ebf5;
            border: 1px solid #d3c4e0;
            border-radius: 3px;
            padding: 2px 8px;
            color: #5a3d73 !important;
            white-space: nowrap;
        }
        .dir-chip:hover {
            background: #5a3d73;
            color: #fff !important;
            text-decoration: none;
        }
        .dir-grid {
            column-width: 280px;
            column-gap: 30px;
        }
        .dir-cat {
            break-inside: avoid;
            -webkit-column-break-inside: avoid;
            display: inline-block;
            width: 100%;
            margin: 0 0 1.4em;
            vertical-align: top;
        }
        .dir-cat h3 {
            font-family: Georgia, 'Times New Roman', Times, serif;
            font-size: 1.05em;
            font-weight: bold;
            margin: 0 0 0.3em;
            padding-bottom: 2px;
            border-bottom: 1px solid #c9b8d6;
            color: #5a3d73;
            scroll-margin-top: 8px;
        }
        .dir-cat ul {
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .dir-cat li {
            font-size: 0.9em;
            line-height: 1.5;
            padding-left: 0.9em;
            text-indent: -0.9em;
        }
        .dir-cat li::before {
            content: "\\203A";
            color: #b8a3c9;
            margin-right: 0.4em;
        }
        .dir-count {
            color: #999;
            font-weight: normal;
            font-size: 0.85em;
        }
        .tool-list {
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .tool-list li {
            margin: 0 0 1em;
        }
        .tool-list a {
            font-weight: bold;
        }
        .tool-list .tool-desc {
            color: #444;
            font-size: 0.92em;
            margin: 0.15em 0 0;
        }
        :target > h3 {
            background: #fdf6a8;
        }
"""

NAV = (
    '<nav>\n    <p><a href="/">Simon Willison\'s Tools</a> '
    '<a href="https://simonwillison.net/">My blog</a></p>\n</nav>'
)


def render_page(title, body_html, extra_css="", body_extra=""):
    """Render a complete HTML document with the shared chrome.

    ``extra_css`` is inserted after the shared style block; ``body_extra`` is
    placed after the main section (e.g. for page-specific scripts).
    """
    import html as _html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_html.escape(title)}</title>
    <style>{STYLE}{extra_css}
    </style>
</head>
<body>
{NAV}
<section class="body">
{body_html}
</section>
{body_extra}
</body>
</html>
"""
