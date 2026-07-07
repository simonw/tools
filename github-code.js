const template = document.createElement("template");

template.innerHTML = `
  <style>
    :host {
      --github-code-bg: #ffffff;
      --github-code-border: #d0d7de;
      --github-code-header-bg: #f6f8fa;
      --github-code-text: #24292f;
      --github-code-muted: #57606a;
      --github-code-line-number: #6e7781;
      --github-code-line-border: #d8dee4;
      --github-code-error: #cf222e;
      --github-code-focus: #0969da;

      display: block;
      color: var(--github-code-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .frame {
      overflow: hidden;
      border: 1px solid var(--github-code-border);
      border-radius: 8px;
      background: var(--github-code-bg);
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      min-height: 0;
      padding: 0.3rem 0.6rem;
      border-bottom: 1px solid var(--github-code-border);
      background: var(--github-code-header-bg);
      font-size: 0.75rem;
      line-height: 1.25;
    }

    .source {
      display: flex;
      align-items: center;
      gap: 0.2rem;
      min-width: 0;
      overflow: hidden;
      color: var(--github-code-text);
      font-weight: 600;
      white-space: nowrap;
    }

    .source a {
      overflow: hidden;
      color: inherit;
      text-decoration: none;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .source a:hover {
      text-decoration: underline;
    }

    .source a:focus-visible {
      border-radius: 4px;
      outline: 2px solid var(--github-code-focus);
      outline-offset: 2px;
    }

    .repo {
      flex: 0 1 auto;
    }

    .source-separator,
    .source-message {
      color: var(--github-code-muted);
    }

    .path {
      flex: 1 1 auto;
      min-width: 0;
    }

    .meta {
      flex: 0 0 auto;
      color: var(--github-code-muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .code {
      overflow: auto;
      margin: 0;
      background: var(--github-code-bg);
      font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.8125rem;
      line-height: 1.55;
      tab-size: 4;
    }

    .rows {
      --github-code-gutter-width: calc(var(--github-code-line-number-width, 2ch) + 1.7rem);

      display: grid;
      position: relative;
      min-width: max-content;
      padding: 0.55rem 0;
    }

    .rows::before {
      content: "";
      position: absolute;
      top: 0;
      bottom: 0;
      left: var(--github-code-gutter-width);
      border-right: 1px solid var(--github-code-line-border);
      pointer-events: none;
    }

    .row {
      display: grid;
      grid-template-columns: var(--github-code-gutter-width) 1fr;
      min-height: 1.25rem;
    }

    .number {
      display: block;
      padding: 0 0.85rem;
      color: var(--github-code-line-number);
      cursor: pointer;
      font-variant-numeric: tabular-nums;
      text-align: right;
      text-decoration: none;
      user-select: none;
    }

    .number:hover {
      text-decoration: underline;
    }

    .number:visited {
      color: var(--github-code-line-number);
    }

    .number:focus-visible {
      border-radius: 4px;
      outline: 2px solid var(--github-code-focus);
      outline-offset: -1px;
    }

    .text {
      padding: 0 1rem;
      white-space: pre;
    }

    .message {
      padding: 1rem;
      color: var(--github-code-muted);
      font-size: 0.925rem;
    }

    .message.error {
      color: var(--github-code-error);
    }
  </style>

  <div class="frame">
    <div class="header">
      <span class="source">
        <a class="repo" target="_blank" rel="noopener noreferrer" hidden></a>
        <span class="source-separator" hidden>/</span>
        <a class="path" target="_blank" rel="noopener noreferrer" hidden></a>
        <span class="source-message" hidden></span>
      </span>
      <span class="meta"></span>
    </div>
    <pre class="code"><code class="rows"></code></pre>
  </div>
`;

class GitHubCode extends HTMLElement {
  static observedAttributes = ["href"];

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.append(template.content.cloneNode(true));
    this._abortController = null;
  }

  connectedCallback() {
    this.load();
  }

  disconnectedCallback() {
    this.cancelPendingFetch();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "href" && oldValue !== newValue && this.isConnected) {
      this.load();
    }
  }

  async load() {
    this.cancelPendingFetch();

    let source;
    try {
      source = parseSourceUrl(this.getAttribute("href"));
    } catch (error) {
      this.renderMessage("Invalid GitHub URL", error.message, true);
      return;
    }

    this.renderMessage(source.label, "Loading...");

    const abortController = new AbortController();
    this._abortController = abortController;

    try {
      const result = await fetchFirstAvailable(source.candidates, abortController.signal);
      const text = await result.response.text();
      const lines = getRequestedLines(text, source.range);

      this.renderCode({
        fileHref: withRangeHash(result.pageUrl, lines),
        fileLabel: result.fileLabel,
        pageUrl: result.pageUrl,
        repoHref: result.repoUrl,
        repoLabel: result.repoLabel,
        rangeLabel: formatRangeLabel(lines),
        lines,
      });
    } catch (error) {
      if (error.name === "AbortError") return;
      this.renderMessage(source.label, error.message, true);
    } finally {
      if (this._abortController === abortController) {
        this._abortController = null;
      }
    }
  }

  cancelPendingFetch() {
    if (this._abortController) {
      this._abortController.abort();
      this._abortController = null;
    }
  }

  renderCode({ fileHref, fileLabel, pageUrl, repoHref, repoLabel, rangeLabel, lines }) {
    const repoLink = this.shadowRoot.querySelector(".repo");
    const pathLink = this.shadowRoot.querySelector(".path");
    const separator = this.shadowRoot.querySelector(".source-separator");
    const sourceMessage = this.shadowRoot.querySelector(".source-message");
    const meta = this.shadowRoot.querySelector(".meta");
    const rows = this.shadowRoot.querySelector(".rows");

    repoLink.hidden = false;
    repoLink.href = repoHref;
    repoLink.textContent = repoLabel;
    separator.hidden = false;
    pathLink.hidden = false;
    pathLink.href = fileHref;
    pathLink.textContent = fileLabel;
    sourceMessage.hidden = true;
    sourceMessage.textContent = "";
    meta.textContent = rangeLabel;
    rows.style.setProperty("--github-code-line-number-width", `${getLineNumberDigitCount(lines)}ch`);
    rows.replaceChildren(...lines.map((line) => createLineNode(line, pageUrl)));
  }

  renderMessage(label, message, isError = false) {
    const repoLink = this.shadowRoot.querySelector(".repo");
    const pathLink = this.shadowRoot.querySelector(".path");
    const separator = this.shadowRoot.querySelector(".source-separator");
    const sourceMessage = this.shadowRoot.querySelector(".source-message");
    const meta = this.shadowRoot.querySelector(".meta");
    const rows = this.shadowRoot.querySelector(".rows");
    const messageNode = document.createElement("span");

    repoLink.hidden = true;
    repoLink.removeAttribute("href");
    repoLink.textContent = "";
    separator.hidden = true;
    pathLink.hidden = true;
    pathLink.removeAttribute("href");
    pathLink.textContent = "";
    sourceMessage.hidden = false;
    sourceMessage.textContent = label;
    meta.textContent = "";
    rows.style.removeProperty("--github-code-line-number-width");
    messageNode.className = isError ? "message error" : "message";
    messageNode.textContent = message;
    rows.replaceChildren(messageNode);
  }
}

function parseSourceUrl(href) {
  if (!href) {
    throw new Error("The href attribute is required.");
  }

  const url = new URL(href, window.location.href);
  const range = parseLineRange(url.hash);
  const parts = url.pathname.split("/").filter(Boolean);

  if (url.hostname === "github.com") {
    return parseGithubPageUrl(url, parts, range);
  }

  if (url.hostname === "raw.githubusercontent.com") {
    return parseRawGithubUrl(url, parts, range);
  }

  throw new Error("Use a github.com blob URL or a raw.githubusercontent.com URL.");
}

function parseGithubPageUrl(url, parts, range) {
  if (parts.length < 5 || (parts[2] !== "blob" && parts[2] !== "raw")) {
    throw new Error("Expected a GitHub file URL containing /blob/ or /raw/.");
  }

  const [owner, repo] = parts;
  const sourceParts = parts.slice(3);
  const candidates = [];
  const repoLabel = `${decodePath(owner)}/${decodePath(repo)}`;
  const repoUrl = buildGithubRepoUrl(owner, repo);

  for (let refLength = 1; refLength < sourceParts.length; refLength += 1) {
    const refParts = sourceParts.slice(0, refLength);
    const fileParts = sourceParts.slice(refLength);
    const rawUrl = buildRawUrl(owner, repo, refParts, fileParts);
    const pageUrl = buildGithubBlobUrl(owner, repo, refParts, fileParts);
    const fileLabel = decodePath(fileParts.join("/"));

    candidates.push({
      rawUrl,
      pageUrl,
      repoLabel,
      repoUrl,
      fileLabel,
      label: `${repoLabel}/${fileLabel}`,
    });
  }

  if (candidates.length === 0) {
    throw new Error("Expected a file path after the GitHub ref.");
  }

  return {
    href: url.href,
    label: candidates[0].label,
    range,
    candidates,
  };
}

function parseRawGithubUrl(url, parts, range) {
  if (parts.length < 4) {
    throw new Error("Expected a raw GitHub URL with owner, repo, ref, and path.");
  }

  const [owner, repo, ...rest] = parts;
  const repoLabel = `${decodePath(owner)}/${decodePath(repo)}`;
  const repoUrl = buildGithubRepoUrl(owner, repo);
  const fileLabel = decodePath(rest.slice(1).join("/"));
  const label = `${repoLabel}/${fileLabel}`;
  const pageUrl = buildGithubBlobUrl(owner, repo, rest.slice(0, 1), rest.slice(1));
  url.hash = "";

  return {
    href: url.href,
    label,
    range,
    candidates: [{ rawUrl: url.href, pageUrl, repoLabel, repoUrl, fileLabel, label }],
  };
}

function parseLineRange(hash) {
  if (!hash) return null;

  const match = hash.match(/^#L(\d+)(?:-L?(\d+))?$/i);
  if (!match) {
    throw new Error("Line ranges should look like #L9 or #L9-L18.");
  }

  const start = Number(match[1]);
  const end = Number(match[2] || match[1]);

  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < 1) {
    throw new Error("Line numbers must be positive integers.");
  }

  if (end < start) {
    throw new Error("The ending line must be greater than or equal to the starting line.");
  }

  return { start, end };
}

async function fetchFirstAvailable(candidates, signal) {
  let lastError = null;

  for (const candidate of candidates) {
    const response = await fetch(candidate.rawUrl, { signal });

    if (response.ok) {
      return {
        response,
        label: candidate.label,
        pageUrl: candidate.pageUrl,
        repoLabel: candidate.repoLabel,
        repoUrl: candidate.repoUrl,
        fileLabel: candidate.fileLabel,
      };
    }

    lastError = new Error(`GitHub returned ${response.status} for ${candidate.rawUrl}`);

    if (response.status !== 404) {
      break;
    }
  }

  throw lastError || new Error("Unable to fetch the requested GitHub file.");
}

function getRequestedLines(text, range) {
  const allLines = text.replace(/\r\n?/g, "\n").split("\n");

  if (allLines.length > 1 && allLines.at(-1) === "") {
    allLines.pop();
  }

  if (range && range.start > allLines.length) {
    return [];
  }

  const start = range ? range.start : 1;
  const end = range ? Math.min(range.end, allLines.length) : allLines.length;

  return allLines.slice(start - 1, end).map((text, index) => ({
    number: start + index,
    text,
  }));
}

function createLineNode(line, pageUrl) {
  const row = document.createElement("span");
  const number = document.createElement("a");
  const text = document.createElement("span");

  row.className = "row";
  number.className = "number";
  number.href = withLineHash(pageUrl, line.number);
  number.target = "_blank";
  number.rel = "noopener noreferrer";
  number.textContent = line.number;
  text.className = "text";
  text.textContent = line.text || " ";

  row.append(number, text);
  return row;
}

function formatRangeLabel(lines) {
  if (lines.length === 0) return "No lines";
  const first = lines[0].number;
  const last = lines.at(-1).number;
  return first === last ? `L${first}` : `L${first}-L${last}`;
}

function getLineNumberDigitCount(lines) {
  return Math.max(1, ...lines.map((line) => String(line.number).length));
}

function buildRawUrl(owner, repo, refParts, fileParts) {
  return `https://raw.githubusercontent.com/${owner}/${repo}/${refParts.join("/")}/${fileParts.join("/")}`;
}

function buildGithubRepoUrl(owner, repo) {
  return `https://github.com/${owner}/${repo}`;
}

function buildGithubBlobUrl(owner, repo, refParts, fileParts) {
  return `https://github.com/${owner}/${repo}/blob/${refParts.join("/")}/${fileParts.join("/")}`;
}

function withRangeHash(pageUrl, lines) {
  if (lines.length === 0) return pageUrl;

  const url = new URL(pageUrl);
  const first = lines[0].number;
  const last = lines.at(-1).number;
  url.hash = first === last ? `L${first}` : `L${first}-L${last}`;
  return url.href;
}

function withLineHash(pageUrl, lineNumber) {
  const url = new URL(pageUrl);
  url.hash = `L${lineNumber}`;
  return url.href;
}

function decodePath(path) {
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}

customElements.define("github-code", GitHubCode);
