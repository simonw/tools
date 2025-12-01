<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Notes to Markdown</title>
  <style>
* {
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: #f5f5f7;
  color: #1d1d1f;
  line-height: 1.6;
}

h1 {
  color: #1d1d1f;
  margin-bottom: 10px;
  font-weight: 600;
}

.instructions {
  background: #fff;
  border-left: 4px solid #ffcc00;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.paste-area {
  width: 100%;
  min-height: 120px;
  padding: 15px;
  border: 2px dashed #86868b;
  border-radius: 8px;
  background: #fff;
  color: #1d1d1f;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 16px;
  margin-bottom: 20px;
  outline: none;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.paste-area:focus {
  border-color: #ffcc00;
  border-style: solid;
  box-shadow: 0 0 0 3px rgba(255, 204, 0, 0.3);
}

.paste-area::placeholder {
  color: #86868b;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.section h2 {
  margin-top: 0;
  color: #1d1d1f;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.code-output {
  width: 100%;
  min-height: 200px;
  padding: 15px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fafafa;
  color: #1d1d1f;
  font-family: 'SF Mono', Monaco, 'Courier New', Courier, monospace;
  font-size: 14px;
  resize: vertical;
  overflow-x: auto;
  white-space: pre-wrap;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

button {
  padding: 10px 20px;
  background: #ffcc00;
  color: #1d1d1f;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-weight: 600;
  transition: all 0.2s;
}

button:hover {
  background: #e6b800;
}

button:active {
  background: #cca300;
}

button.copied {
  background: #007aff;
  color: #fff;
}

.preview-container {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 15px;
  overflow-x: auto;
}

.preview-container a {
  color: #007aff;
  text-decoration: none;
}

.preview-container a:hover {
  text-decoration: underline;
}

.empty-state {
  text-align: center;
  color: #86868b;
  padding: 40px;
  font-size: 18px;
}

.error {
  background: #fff;
  border-left: 4px solid #ff3b30;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  color: #ff3b30;
}

details {
  margin-top: 10px;
}

summary {
  cursor: pointer;
  color: #86868b;
  font-size: 14px;
  padding: 8px 0;
  user-select: none;
}

summary:hover {
  color: #1d1d1f;
}

.rtf-debug {
  width: 100%;
  min-height: 150px;
  max-height: 400px;
  padding: 15px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #f0f0f0;
  color: #666;
  font-family: 'SF Mono', Monaco, 'Courier New', Courier, monospace;
  font-size: 12px;
  resize: vertical;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin-top: 10px;
}

@media (max-width: 768px) {
  body {
    padding: 10px;
  }

  h1 {
    font-size: 24px;
  }

  .button-group {
    flex-direction: column;
  }

  button {
    width: 100%;
  }
}
  </style>
</head>
<body>
  <h1>Notes to Markdown</h1>

  <div class="instructions">
    <strong>Instructions:</strong> Paste content from Apple Notes below. The RTF data will be converted to Markdown and HTML with hyperlinks preserved.
  </div>

  <textarea class="paste-area" placeholder="Click here and paste your Apple Notes content (Cmd+V)..."></textarea>

  <div class="results" id="results">
    <div class="empty-state">Paste Apple Notes content to see the conversion</div>
  </div>

<script>
const pasteArea = document.querySelector('.paste-area');
const resultsDiv = document.getElementById('results');

function parseRTFHyperlinks(rtf) {
  const results = [];
  let i = 0;

  while (i < rtf.length) {
    // Look for hyperlink field pattern
    const fieldStart = rtf.indexOf('{\\field{\\*\\fldinst{HYPERLINK', i);
    if (fieldStart === -1) break;

    // Find the URL
    const urlStart = rtf.indexOf('"', fieldStart);
    if (urlStart === -1) break;
    const urlEnd = rtf.indexOf('"', urlStart + 1);
    if (urlEnd === -1) break;
    const url = rtf.substring(urlStart + 1, urlEnd);

    // Find the link text in fldrslt
    const fldrsltStart = rtf.indexOf('{\\fldrslt', fieldStart);
    if (fldrsltStart === -1) break;

    // Extract the text, handling nested braces
    let braceCount = 0;
    let textStart = -1;
    let textEnd = -1;

    for (let j = fldrsltStart; j < rtf.length; j++) {
      if (rtf[j] === '{') {
        braceCount++;
      } else if (rtf[j] === '}') {
        braceCount--;
        if (braceCount === 0) {
          textEnd = j;
          break;
        }
      }
    }

    if (textEnd === -1) break;

    // Extract text content from fldrslt, removing RTF control codes
    let fldrsltContent = rtf.substring(fldrsltStart + 9, textEnd);
    let linkText = extractTextFromRTF(fldrsltContent);

    results.push({
      start: fieldStart,
      end: textEnd + 1,
      url: url,
      text: linkText.trim()
    });

    i = textEnd + 1;
  }

  return results;
}

function extractTextFromRTF(rtf) {
  let text = '';
  let i = 0;

  while (i < rtf.length) {
    const char = rtf[i];

    if (char === '\\') {
      // Handle control sequence
      let j = i + 1;

      // Check for escaped characters
      if (j < rtf.length) {
        const nextChar = rtf[j];
        if (nextChar === '\\' || nextChar === '{' || nextChar === '}') {
          text += nextChar;
          i = j + 1;
          continue;
        }
        if (nextChar === '\n' || nextChar === '\r') {
          text += '\n';
          i = j + 1;
          continue;
        }
        // Handle hex characters \'xx
        if (nextChar === "'") {
          j++;
          let hexCode = '';
          while (j < rtf.length && /[0-9a-fA-F]/.test(rtf[j]) && hexCode.length < 2) {
            hexCode += rtf[j];
            j++;
          }
          if (hexCode.length === 2) {
            text += String.fromCharCode(parseInt(hexCode, 16));
          }
          i = j;
          continue;
        }
      }

      // Read control word
      let controlWord = '';
      while (j < rtf.length && /[a-z]/i.test(rtf[j])) {
        controlWord += rtf[j];
        j++;
      }

      // Read numeric parameter
      let numParam = '';
      while (j < rtf.length && /[-0-9]/.test(rtf[j])) {
        numParam += rtf[j];
        j++;
      }

      // Skip optional space after control word
      if (j < rtf.length && rtf[j] === ' ') {
        j++;
      }

      // Handle Unicode
      if (controlWord === 'u') {
        const codePoint = parseInt(numParam);
        if (!isNaN(codePoint)) {
          if (codePoint < 0) {
            text += String.fromCharCode(65536 + codePoint);
          } else {
            text += String.fromCharCode(codePoint);
          }
        }
        // Skip replacement character
        if (j < rtf.length && rtf[j] === '?') {
          j++;
        }
      }

      i = j;
    } else if (char === '{' || char === '}') {
      i++;
    } else if (char === '\n' || char === '\r') {
      i++;
    } else {
      text += char;
      i++;
    }
  }

  return text;
}

function stripRTFHeader(rtf) {
  // Remove the RTF header including fonttbl, colortbl, expandedcolortbl, and other preamble
  // Find the end of the header section (after all the table definitions)

  // Remove font table
  rtf = rtf.replace(/\{\\fonttbl[^}]*(\{[^}]*\})*[^}]*\}/g, '');

  // Remove color table
  rtf = rtf.replace(/\{\\colortbl[^}]*\}/g, '');

  // Remove expanded color table
  rtf = rtf.replace(/\{\\\*\\expandedcolortbl[^}]*\}/g, '');

  // Remove RTF header declaration
  rtf = rtf.replace(/^\{\\rtf1\\ansi[^\\]*/, '{');
  rtf = rtf.replace(/\\cocoartf\d+/g, '');
  rtf = rtf.replace(/\\cocoatextscaling\d+/g, '');
  rtf = rtf.replace(/\\cocoaplatform\d+/g, '');
  rtf = rtf.replace(/\\deftab\d+/g, '');

  return rtf;
}

function rtfToMarkdownAndHtml(rtf) {
  // Strip the RTF header/preamble before processing
  rtf = stripRTFHeader(rtf);

  const hyperlinks = parseRTFHyperlinks(rtf);

  // Build output by processing the RTF and inserting markdown links
  let markdown = '';
  let html = '';
  let lastEnd = 0;

  // Get all plain text between hyperlinks
  function getPlainTextBetween(start, end) {
    let segment = rtf.substring(start, end);

    // Remove paragraph formatting
    segment = segment.replace(/\\pard[^\\}]*/g, '');
    segment = segment.replace(/\\pardeftab\d+/g, '');
    segment = segment.replace(/\\slleading\d+/g, '');
    segment = segment.replace(/\\partightenfactor\d+/g, '');
    segment = segment.replace(/\\pardirnatural/g, '');

    // Handle line breaks
    segment = segment.replace(/\\\\/g, '\n');

    // Extract text
    return extractTextFromRTF(segment);
  }

  for (const link of hyperlinks) {
    // Add text before this link
    const textBefore = getPlainTextBetween(lastEnd, link.start);
    markdown += textBefore;
    html += escapeHtml(textBefore);

    // Add the link
    if (link.text) {
      markdown += `[${link.text}](${link.url})`;
      html += `<a href="${escapeHtml(link.url)}">${escapeHtml(link.text)}</a>`;
    } else {
      markdown += link.url;
      html += `<a href="${escapeHtml(link.url)}">${escapeHtml(link.url)}</a>`;
    }

    lastEnd = link.end;
  }

  // Add remaining text
  const textAfter = getPlainTextBetween(lastEnd, rtf.length);
  markdown += textAfter;
  html += escapeHtml(textAfter);

  // Clean up the output
  markdown = cleanupText(markdown);
  html = cleanupText(html);

  // Convert newlines to <br> for HTML
  html = html.replace(/\n/g, '<br>\n');

  return { markdown, html };
}

function cleanupText(text) {
  // Remove any remaining control sequences that slipped through
  text = text.replace(/\\cf\d+/g, '');
  text = text.replace(/\\f\d+/g, '');
  text = text.replace(/\\fs\d+/g, '');
  text = text.replace(/\\b\d*/g, '');
  text = text.replace(/\\i\d*/g, '');
  text = text.replace(/\\[a-z]+\d*/g, '');

  // Clean up extra whitespace but preserve intentional line breaks
  text = text.replace(/[ \t]+/g, ' ');
  text = text.replace(/\n +/g, '\n');
  text = text.replace(/ +\n/g, '\n');
  text = text.replace(/\n{3,}/g, '\n\n');

  return text.trim();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

pasteArea.addEventListener('paste', async (e) => {
  e.preventDefault();

  const clipboardData = e.clipboardData;
  resultsDiv.innerHTML = '';

  if (!clipboardData) {
    resultsDiv.innerHTML = '<div class="empty-state">No clipboard data detected</div>';
    return;
  }

  // Try RTF first (Apple Notes uses RTF)
  const rtfData = clipboardData.getData('text/rtf');

  let markdown = '';
  let html = '';

  if (rtfData) {
    try {
      const result = rtfToMarkdownAndHtml(rtfData);
      markdown = result.markdown;
      html = result.html;
    } catch (error) {
      resultsDiv.innerHTML = `<div class="error">Error parsing RTF: ${error.message}</div>`;
      return;
    }
  } else {
    // Fall back to plain text
    const plainText = clipboardData.getData('text/plain');

    if (plainText) {
      markdown = plainText;
      html = escapeHtml(plainText).replace(/\n/g, '<br>\n');
    } else {
      resultsDiv.innerHTML = '<div class="error">No supported format detected in clipboard.</div>';
      return;
    }
  }

  // Create Markdown section
  const markdownSection = document.createElement('div');
  markdownSection.className = 'section';
  markdownSection.innerHTML = `
    <h2>Markdown</h2>
    <div class="button-group">
      <button id="copyMarkdownBtn">Copy Markdown</button>
    </div>
    <textarea class="code-output" id="markdownOutput" readonly>${escapeHtml(markdown)}</textarea>
  `;
  resultsDiv.appendChild(markdownSection);

  // Create HTML section
  const htmlSection = document.createElement('div');
  htmlSection.className = 'section';
  htmlSection.innerHTML = `
    <h2>HTML</h2>
    <div class="button-group">
      <button id="copyHtmlBtn">Copy HTML</button>
    </div>
    <textarea class="code-output" id="htmlOutput" readonly>${escapeHtml(html)}</textarea>
  `;
  resultsDiv.appendChild(htmlSection);

  // Create preview section
  const previewSection = document.createElement('div');
  previewSection.className = 'section';
  previewSection.innerHTML = `
    <h2>Preview</h2>
    <div class="preview-container" id="preview"></div>
  `;
  resultsDiv.appendChild(previewSection);

  document.getElementById('preview').innerHTML = html;

  // Create debug section (collapsed by default)
  if (rtfData) {
    const debugSection = document.createElement('div');
    debugSection.className = 'section';
    debugSection.innerHTML = `
      <details>
        <summary>Show raw RTF (debug)</summary>
        <pre class="rtf-debug">${escapeHtml(rtfData)}</pre>
      </details>
    `;
    resultsDiv.appendChild(debugSection);
  }

  // Set up copy buttons
  const copyMarkdownBtn = document.getElementById('copyMarkdownBtn');
  const copyHtmlBtn = document.getElementById('copyHtmlBtn');
  const markdownOutput = document.getElementById('markdownOutput');
  const htmlOutput = document.getElementById('htmlOutput');

  copyMarkdownBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(markdownOutput.value);
      copyMarkdownBtn.textContent = 'Copied!';
      copyMarkdownBtn.classList.add('copied');
      setTimeout(() => {
        copyMarkdownBtn.textContent = 'Copy Markdown';
        copyMarkdownBtn.classList.remove('copied');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  });

  copyHtmlBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(htmlOutput.value);
      copyHtmlBtn.textContent = 'Copied!';
      copyHtmlBtn.classList.add('copied');
      setTimeout(() => {
        copyHtmlBtn.textContent = 'Copy HTML';
        copyHtmlBtn.classList.remove('copied');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  });
});

// Clear the textarea on paste
pasteArea.addEventListener('paste', () => {
  setTimeout(() => {
    pasteArea.value = '';
  }, 0);
});
</script>
</body>
</html>
