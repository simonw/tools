# Tools Repository Structure Guide for Building sloccount.html

## Repository Overview

**Location**: `/home/user/tools/`  
**Type**: Static HTML/JavaScript web tools (200+ tools)  
**Hosting**: GitHub Pages (tools.simonwillison.net)  
**Build**: Python scripts generate docs and indices  
**Testing**: Playwright + pytest for automated testing  

---

## 1. Repository Structure

```
/home/user/tools/
├── *.html                    # Individual tool files
├── *.docs.md                 # Documentation/descriptions for each tool
├── tests/
│   ├── test_*.py            # Pytest test files
│   ├── ocr-test-text.png    # Test fixtures
│   └── three_page_pdf.pdf
├── .github/workflows/
│   ├── test.yml             # Runs pytest/playwright
│   ├── pages.yml            # Deploys to GitHub Pages
│   └── claude.yml
├── build_index.py           # Generates index.html from README.md
├── build_colophon.py        # Generates colophon page with commit info
├── gather_links.py          # Collects tool metadata
├── README.md                # Main listing of all tools
├── build.sh                 # Build script
├── pyproject.toml           # Python project config and dependencies
└── .gitignore
```

---

## 2. Tool File Naming Convention

- **HTML file**: `{tool-name}.html` (e.g., `query-string-stripper.html`)
- **Docs file**: `{tool-name}.docs.md` (e.g., `query-string-stripper.docs.md`)
- **Docs format**: Brief description + auto-generated commit comment

### Example docs.md:
```markdown
This utility removes the query string portion from URLs (everything after the question mark). 
Enter a URL into the input field and the tool instantly displays the cleaned version without 
query parameters. You can copy the stripped URL to your clipboard with the dedicated button 
for easy use elsewhere.

<!-- Generated from commit: f7010753d1508f56a225c6cddf84e9cc78936ff4 -->
```

---

## 3. Common HTML Structure Patterns

### Basic Minimal Tool (query-string-stripper.html - 144 lines)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Query String Stripper</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        /* Mobile-friendly media query */
        @media (max-width: 600px) {
            body { padding: 10px; }
            h1 { font-size: 24px; }
        }
    </style>
</head>
<body>
    <h1>Query String Stripper</h1>
    <p>Paste a URL to remove the query string (everything from ? onwards)</p>
    
    <label for="url-input">URL:</label>
    <input type="text" id="url-input" placeholder="...">
    
    <div id="output-container">
        <label for="stripped-url">Stripped URL:</label>
        <input type="text" id="stripped-url" readonly>
        <button id="copy-button">Copy to clipboard</button>
    </div>

    <script>
        // Event listeners and processing logic
        const urlInput = document.getElementById('url-input');
        urlInput.addEventListener('input', function() {
            // Real-time processing
        });
    </script>
</body>
</html>
```

**Key characteristics:**
- Responsive `<meta name="viewport">`
- Box-sizing border-box universally
- Centered max-width layout (800px is common)
- Real-time event listeners (`input`, `change`)
- Show/hide sections with `.visible` class
- Mobile media query at ~600px breakpoint

---

## 4. Common Mobile-Friendly UI Patterns

### Responsive Patterns Used:
1. **Max-width centered containers** (600-1200px)
2. **Flexbox layouts** for responsive grids
3. **Media queries** for breakpoints (600px, 768px, 920px)
4. **Padding adjustments** for mobile
5. **Font size scaling** with `clamp()`

### Example from mask-visualizer.html:
```css
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
}

@media (min-width: 920px) {
    .row {
        grid-template-columns: 360px 1fr;
    }
}
```

### Example from pyodide-bar-chart.html (modern approach):
```css
h1 {
    font-size: clamp(22px, 3.2vw, 34px);
    letter-spacing: 0.2px;
}

.wrap {
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 16px 60px;
}
```

---

## 5. Tool Architecture Patterns

### Pattern 1: Simple Stateless Tools
**Examples**: `query-string-stripper.html`, `escape-entities.html`
- Input → Process → Output
- Real-time event listeners
- No external API calls
- Minimal state management

### Pattern 2: Tools with External Resources/APIs
**Examples**: `jina-reader.html`, `ocr.html`

```javascript
// Load external library via CDN
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.0.2/marked.min.js"></script>

// Or ES module imports
<script type="module">
    import pdfjsDist from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/+esm';
</script>

// Fetch API calls
fetch(`https://api.github.com/gists/${gistId}`)
    .then(response => response.json())
    .then(data => {
        // Process data
    })
    .catch(err => showError(err.message));
```

### Pattern 3: Tools with WebAssembly
**Examples**: `sqlite-wasm.html`, `micropython.html`, `ocr.html`

#### sqlite-wasm.html pattern:
```html
<script src="https://cdn.jsdelivr.net/npm/@sqlite.org/sqlite-wasm@3.46.1-build4/sqlite-wasm/jswasm/sqlite3.mjs" 
        type="module"></script>

<script type="module">
    import sqlite3InitModule from 'https://cdn.jsdelivr.net/npm/@sqlite.org/sqlite-wasm@3.46.1-build4/sqlite-wasm/jswasm/sqlite3.mjs';
    
    const initializeSQLite = async () => {
        const sqlite3 = await sqlite3InitModule({
            print: console.log,
            printErr: console.error,
        });
        window.db = new sqlite3.oo1.DB();
        // Initialize with CREATE TABLE and data
    };
    
    window.executeQuery = () => {
        const query = document.getElementById('query').value;
        const results = window.db.selectObjects(query);
        displayResults(results);
    };
</script>
```

#### micropython.html pattern:
```html
<script type="module">
    import * as mpjs from 'https://cdn.jsdelivr.net/npm/@micropython/micropython-webassembly-pyscript@1.26.0/micropython.mjs';
    
    let mp;
    let activeCapture = null;
    
    const mp = await mpjs.loadMicroPython({
        linebuffer: true,
        stdout: (text) => pushOutput('stdout', text),
        stderr: (text) => pushOutput('stderr', text),
    });
    
    async function runWithCapture(src) {
        activeCapture = { stdout: '', stderr: '' };
        await mp.runPythonAsync(src.endsWith('\n') ? src : `${src}\n`);
        return activeCapture;
    }
</script>
```

---

## 6. Data Loading Patterns

### Pattern 1: Load from URL Hash
Used in `json-string-extractor.html`:
```javascript
// Load Gist from URL hash
async function loadGistFromHash() {
    const hash = window.location.hash;
    const gistMatch = hash.match(/gist=([a-fA-F0-9]+)/i);
    
    if (gistMatch) {
        const gistId = gistMatch[1];
        const jsonContent = await loadGistJSON(gistId);
        jsonInput.value = jsonContent;
        processJSON();
    }
}

loadGistFromHash();

// Listen for hash changes
window.addEventListener('hashchange', () => {
    loadGistFromHash();
});
```

### Pattern 2: File Input + Drag & Drop
Used in `ocr.html`, `svg-render.html`:
```javascript
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');

dropzone.addEventListener('click', () => fileInput.click());

dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});
```

### Pattern 3: Clipboard Interaction
Used in `clipboard-viewer.html`:
```javascript
// Read from clipboard
navigator.clipboard.read().then((items) => {
    items.forEach((item) => {
        // Process clipboard types
    });
});

// Write to clipboard
navigator.clipboard.writeText(text).then(() => {
    button.textContent = 'Copied!';
    setTimeout(() => {
        button.textContent = 'Copy to clipboard';
    }, 2000);
});
```

---

## 7. UI Component Patterns

### Copy to Clipboard Button
Standardized across most tools:
```javascript
const copyButton = document.getElementById('copy-button');
const textToCopy = document.getElementById('text-field');

copyButton.addEventListener('click', () => {
    navigator.clipboard.writeText(textToCopy.value).then(() => {
        const originalText = copyButton.textContent;
        copyButton.textContent = 'Copied!';
        copyButton.classList.add('copied');
        
        setTimeout(() => {
            copyButton.textContent = originalText;
            copyButton.classList.remove('copied');
        }, 2000);
    }).catch(() => {
        // Fallback for older browsers
        textToCopy.select();
        document.execCommand('copy');
    });
});
```

### Loading States
```javascript
// Show loading indicator
button.disabled = true;
button.textContent = 'Loading...';

try {
    const result = await fetchData();
    displayResult(result);
} finally {
    button.disabled = false;
    button.textContent = 'Original text';
}
```

### Error Messages
Pattern used in `json-string-extractor.html`:
```html
<div id="error" class="error"></div>

<style>
.error {
    color: #e74c3c;
    padding: 12px;
    background: #fef5f5;
    border-radius: 4px;
    margin-top: 10px;
    display: none;
}
</style>

<script>
function showError(message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    errorDiv.style.display = 'none';
}
</script>
```

---

## 8. Test Structure

### Setup (tests/test_ocr.py)
```python
from http.client import HTTPConnection
import pathlib
from playwright.sync_api import Page, expect
import pytest
from subprocess import Popen, PIPE
import time

test_dir = pathlib.Path(__file__).parent.absolute()
root = test_dir.parent.absolute()

@pytest.fixture(scope="module")
def static_server():
    """Start a local HTTP server for testing"""
    process = Popen(
        ["python", "-m", "http.server", "8123", "--directory", root], 
        stdout=PIPE
    )
    retries = 5
    while retries > 0:
        conn = HTTPConnection("127.0.0.1:8123")
        try:
            conn.request("HEAD", "/")
            response = conn.getresponse()
            if response is not None:
                yield process
                break
        except ConnectionRefusedError:
            time.sleep(1)
            retries -= 1
    
    if not retries:
        raise RuntimeError("Failed to start http server")
    else:
        process.terminate()
        process.wait()
```

### Test Examples
```python
def test_initial_state(page: Page, static_server):
    page.goto("http://127.0.0.1:8123/ocr.html")
    expect(page.locator("h1")).to_have_text(
        "OCR PDFs and images directly in your browser"
    )
    expect(page.locator("#dropzone")).to_have_text(
        "Drag and drop a PDF, JPG, PNG, or GIF file here or click to select a file"
    )

def test_open_image(page: Page, static_server):
    page.goto("http://127.0.0.1:8123/ocr.html")
    file_input = page.locator("#fileInput")
    file_input.set_input_files(str(test_dir / "ocr-test-text.png"))
    expect(page.locator(".image-container img")).to_be_visible()
    expect(page.locator(".textarea-alt")).to_have_value("OCR test text")
```

### Running Tests
```bash
# Install dependencies
pip install -e .
playwright install

# Run all tests
pytest

# Run specific test
pytest tests/test_ocr.py::test_initial_state

# Run with verbose output
pytest -v
```

---

## 9. External Library/CDN Loading Patterns

### Popular CDNs Used:
```html
<!-- Marked (Markdown parser) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.0.2/marked.min.js"></script>

<!-- PDF.js (PDF rendering) -->
<script type="module">
    import pdfjsDist from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/+esm';
</script>

<!-- Tesseract.js (OCR) -->
<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>

<!-- CropperJS (Image cropping) -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"></script>

<!-- Pyodide (Python in browser) -->
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js"></script>

<!-- SQLite WASM -->
<script src="https://cdn.jsdelivr.net/npm/@sqlite.org/sqlite-wasm@3.46.1-build4/sqlite-wasm/jswasm/sqlite3.mjs" type="module"></script>

<!-- MicroPython WASM -->
<script type="module">
    import * as mpjs from 'https://cdn.jsdelivr.net/npm/@micropython/micropython-webassembly-pyscript@1.26.0/micropython.mjs';
</script>
```

---

## 10. Build and Deployment

### GitHub Workflows (.github/workflows/test.yml)
```yaml
name: Test
on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
        cache: 'pip'
        cache-dependency-path: 'pyproject.toml'
    - name: Cache Playwright browsers
      uses: actions/cache@v4
      with:
        path: ~/.cache/ms-playwright/
        key: ${{ runner.os }}-browsers
    - name: Install dependencies
      run: |
        pip install -e .
        playwright install
    - name: Run test
      run: pytest
```

### Build Process (build.sh)
```bash
#!/bin/bash
set -e

# Ensure full git history for finding commit dates
git fetch --unshallow

# Install Python dependencies
pip install --quiet markdown

# Run Python build scripts
python gather_links.py      # Collect tool metadata
python build_colophon.py    # Generate colophon page
python build_index.py       # Convert README.md to index.html
```

---

## 11. Template for sloccount.html

Based on patterns above, here's a template structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sloccount - Lines of Code Counter</title>
    <style>
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                         Helvetica, Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }
        
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            margin-top: 0;
            font-size: 28px;
            color: #333;
        }
        
        textarea {
            width: 100%;
            min-height: 150px;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
        }
        
        textarea:focus {
            outline: none;
            border-color: #4a90e2;
        }
        
        button {
            background-color: #4a90e2;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        
        button:hover {
            background-color: #357abd;
        }
        
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        
        .results {
            margin-top: 30px;
            display: none;
        }
        
        .results.visible {
            display: block;
        }
        
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-item {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #4a90e2;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        
        .error {
            color: #e74c3c;
            padding: 12px;
            background: #fef5f5;
            border-radius: 4px;
            display: none;
            margin-top: 10px;
        }
        
        .error.visible {
            display: block;
        }
        
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            
            .container {
                padding: 15px;
            }
            
            .stats {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Sloccount</h1>
        <p>Count lines of code in multiple files or paste source code</p>
        
        <textarea id="codeInput" placeholder="Paste your source code here or drag & drop files..."></textarea>
        
        <button id="processButton">Count Lines</button>
        
        <div id="error" class="error"></div>
        
        <div id="results" class="results">
            <h2>Results</h2>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-label">Total Lines</div>
                    <div class="stat-value" id="totalLines">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Code Lines</div>
                    <div class="stat-value" id="codeLines">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Comment Lines</div>
                    <div class="stat-value" id="commentLines">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Blank Lines</div>
                    <div class="stat-value" id="blankLines">0</div>
                </div>
            </div>
            
            <h3>Breakdown by File</h3>
            <div id="fileStats"></div>
            
            <button id="copyButton">Copy Results</button>
        </div>
    </div>
    
    <script>
        const codeInput = document.getElementById('codeInput');
        const processButton = document.getElementById('processButton');
        const resultsDiv = document.getElementById('results');
        const errorDiv = document.getElementById('error');
        
        function countLines(code) {
            const lines = code.split('\n');
            let totalLines = 0;
            let codeLines = 0;
            let commentLines = 0;
            let blankLines = 0;
            
            for (const line of lines) {
                const trimmed = line.trim();
                totalLines++;
                
                if (!trimmed) {
                    blankLines++;
                } else if (trimmed.startsWith('//') || 
                           trimmed.startsWith('#') || 
                           trimmed.startsWith('*')) {
                    commentLines++;
                } else {
                    codeLines++;
                }
            }
            
            return { totalLines, codeLines, commentLines, blankLines };
        }
        
        function displayResults(stats) {
            document.getElementById('totalLines').textContent = stats.totalLines;
            document.getElementById('codeLines').textContent = stats.codeLines;
            document.getElementById('commentLines').textContent = stats.commentLines;
            document.getElementById('blankLines').textContent = stats.blankLines;
            
            resultsDiv.classList.add('visible');
            errorDiv.classList.remove('visible');
        }
        
        processButton.addEventListener('click', () => {
            const code = codeInput.value.trim();
            
            if (!code) {
                errorDiv.textContent = 'Please paste some code';
                errorDiv.classList.add('visible');
                resultsDiv.classList.remove('visible');
                return;
            }
            
            try {
                const stats = countLines(code);
                displayResults(stats);
            } catch (error) {
                errorDiv.textContent = `Error: ${error.message}`;
                errorDiv.classList.add('visible');
            }
        });
        
        // Real-time processing
        codeInput.addEventListener('input', () => {
            if (codeInput.value.trim()) {
                processButton.disabled = false;
            } else {
                processButton.disabled = true;
            }
        });
    </script>
</body>
</html>
```

---

## 12. Key Files to Reference

| File | Purpose |
|------|---------|
| `/home/user/tools/query-string-stripper.html` | Simple pattern (144 lines) |
| `/home/user/tools/json-string-extractor.html` | Complex with external APIs (420 lines) |
| `/home/user/tools/sqlite-wasm.html` | WebAssembly pattern |
| `/home/user/tools/micropython.html` | Python in browser |
| `/home/user/tools/ocr.html` | Tesseract.js + PDF.js pattern |
| `/home/user/tools/mask-visualizer.html` | Canvas visualization |
| `/home/user/tools/escape-entities.html` | Minimal simple tool |
| `/home/user/tools/tests/test_ocr.py` | Test pattern |

---

## 13. Development Checklist for sloccount.html

- [ ] Create `sloccount.html` following basic tool template
- [ ] Create `sloccount.docs.md` with brief description
- [ ] Implement core functionality (line counting logic)
- [ ] Add mobile-friendly responsive design
- [ ] Add copy to clipboard functionality
- [ ] Test with various code samples
- [ ] Create `tests/test_sloccount.py` with Playwright tests
- [ ] Verify responsive behavior on mobile devices
- [ ] Test edge cases (empty input, special characters, etc.)
- [ ] Add any external library CDN links if needed
- [ ] Test in CI/CD pipeline (GitHub Actions)

---

## 14. Useful Commands

```bash
# Start local development server
python -m http.server 8000

# Test specific tool
pytest tests/test_sloccount.py -v

# Run all tests
pytest

# Install playwright browsers
playwright install
```

---

## Summary

The tools repository follows a **lightweight, stateless HTML5 pattern** where:
1. Each tool is a **single, self-contained HTML file**
2. Tools are **mobile-responsive** with minimal CSS frameworks
3. **Real-time processing** via JavaScript event listeners
4. **External resources** loaded from CDNs (jsdelivr, cdnjs, etc.)
5. **No build step** required for individual tools
6. **Tests** use Playwright + pytest for automation
7. **Documentation** auto-generated from git commits

For sloccount.html, follow the **query-string-stripper** or **escape-entities** pattern as a starting point for a simple, focused tool.
