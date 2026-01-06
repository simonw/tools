// Record analytics visit
(function recordAnalytics() {
    const STORAGE_KEY = 'tools_analytics';
    const slug = window.location.pathname; // path only, no fragment or query string
    const timestamp = Date.now();

    try {
        const analytics = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        analytics.push({ slug, timestamp });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(analytics));
    } catch (e) {
        // Silently fail if localStorage is unavailable
    }
})();

// Get the current filename from the URL
let pathname = window.location.pathname;
let filename = pathname.split('/').pop() || 'index.html';

// Add .html if missing
if (!filename.endsWith('.html')) {
    filename += '.html';
}

// Get the page name for the "About" link (from pathname, without .html)
const pageName = filename.replace('.html', '');

// Parse an RGB/RGBA color string and return {r, g, b, a}
function parseColor(colorStr) {
    const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
    if (match) {
        return {
            r: parseInt(match[1]),
            g: parseInt(match[2]),
            b: parseInt(match[3]),
            a: match[4] !== undefined ? parseFloat(match[4]) : 1
        };
    }
    return null;
}

// Calculate relative luminance (0 = black, 1 = white)
function getLuminance(r, g, b) {
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

// Get the effective background color, checking body and html
function getEffectiveBackgroundColor() {
    // Check body first
    const bodyBg = window.getComputedStyle(document.body).backgroundColor;
    const bodyColor = parseColor(bodyBg);
    if (bodyColor && bodyColor.a > 0.1) {
        return bodyColor;
    }

    // Check html element
    const htmlBg = window.getComputedStyle(document.documentElement).backgroundColor;
    const htmlColor = parseColor(htmlBg);
    if (htmlColor && htmlColor.a > 0.1) {
        return htmlColor;
    }

    // Default to white (browser default)
    return { r: 255, g: 255, b: 255, a: 1 };
}

// Check if a color has good contrast against the background
function hasGoodContrast(textColor, bgColor) {
    const textLum = getLuminance(textColor.r, textColor.g, textColor.b);
    const bgLum = getLuminance(bgColor.r, bgColor.g, bgColor.b);
    const contrast = Math.abs(textLum - bgLum);
    return contrast > 0.3; // Minimum contrast threshold
}

// Find the most common text color that has good contrast with the background
function getBestTextColor(bgColor) {
    const colorCounts = {};
    const elements = document.body.querySelectorAll('*');

    elements.forEach(el => {
        if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'NOSCRIPT') {
            return;
        }

        const hasDirectText = Array.from(el.childNodes).some(
            node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
        );

        if (hasDirectText) {
            const style = window.getComputedStyle(el);
            const color = style.color;
            const parsed = parseColor(color);

            if (parsed && parsed.a > 0.1 && hasGoodContrast(parsed, bgColor)) {
                colorCounts[color] = (colorCounts[color] || 0) + 1;
            }
        }
    });

    // Find the most common color with good contrast
    let mostCommon = null;
    let maxCount = 0;

    for (const [color, count] of Object.entries(colorCounts)) {
        if (count > maxCount) {
            maxCount = count;
            mostCommon = color;
        }
    }

    return mostCommon;
}

const bgColor = getEffectiveBackgroundColor();
const bgLuminance = getLuminance(bgColor.r, bgColor.g, bgColor.b);
const isDark = bgLuminance < 0.5;

// Try to find a good text color from the page
let textColor = getBestTextColor(bgColor);

// If no suitable color found, use sensible defaults based on background
if (!textColor) {
    textColor = isDark ? 'rgb(255, 255, 255)' : 'rgb(0, 0, 0)';
}

// Check if body uses flex or grid layout that could break footer positioning
const bodyStyle = window.getComputedStyle(document.body);
const bodyDisplay = bodyStyle.display;
const needsLayoutFix = (bodyDisplay === 'flex' || bodyDisplay === 'grid');

if (needsLayoutFix) {
    // Wrap existing body content to preserve the original layout behavior
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
        display: ${bodyDisplay};
        flex: 1 1 auto;
        flex-direction: ${bodyStyle.flexDirection};
        align-items: ${bodyStyle.alignItems};
        justify-content: ${bodyStyle.justifyContent};
        flex-wrap: ${bodyStyle.flexWrap};
        gap: ${bodyStyle.gap};
        width: 100%;
        min-height: inherit;
    `;

    // Move all existing children (except scripts at the end) into the wrapper
    while (document.body.firstChild) {
        wrapper.appendChild(document.body.firstChild);
    }

    // Reset body to a vertical flex column
    document.body.style.display = 'flex';
    document.body.style.flexDirection = 'column';
    document.body.style.alignItems = 'stretch';
    document.body.style.justifyContent = 'flex-start';

    document.body.appendChild(wrapper);
}

// Create the footer element
const footer = document.createElement('footer');
footer.style.cssText = 'flex-shrink: 0; width: 100%; box-sizing: border-box;';
footer.innerHTML = `
    <hr style="margin: 2rem 0 1rem 0; border: none; border-top: 1px solid ${textColor};">
    <nav style="font-family: system-ui, -apple-system, sans-serif; font-size: 12px; text-align: center; font-style: normal; padding-bottom: 1rem;">
        <a href="/" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">Home</a>
        <a href="/colophon#${filename}" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">About ${pageName}</a>
        <a href="https://github.com/simonw/tools/blob/main/${filename}" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">View source</a>
        <a href="https://github.com/simonw/tools/commits/main/${filename}" style="color: ${textColor}; text-decoration: underline;" id="footer-changes-link">Changes</a>
    </nav>
`;

document.body.appendChild(footer);

// Fetch dates.json and update the Changes link with the last updated date
fetch('/dates.json')
    .then(response => response.json())
    .then(dates => {
        const date = dates[filename];
        if (date) {
            const link = document.getElementById('footer-changes-link');
            if (link) {
                link.textContent = `Updated ${date}`;
            }
        }
    })
    .catch(() => {
        // Silently fail - keep "Changes" as fallback
    });

    class PageWeightMonitor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.collectData();
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  getResourceData() {
    const resources = performance.getEntriesByType('resource');
    const navigation = performance.getEntriesByType('navigation')[0];

    const byType = {};
    let totalTransfer = 0;
    let totalDecoded = 0;
    let measuredCount = 0;
    let unmeasuredCount = 0;
    const unmeasuredUrls = [];

    resources.forEach(r => {
      const type = r.initiatorType || 'other';
      if (!byType[type]) {
        byType[type] = { count: 0, transferSize: 0, decodedSize: 0, items: [] };
      }

      byType[type].count++;
      byType[type].items.push({
        name: r.name,
        transferSize: r.transferSize,
        decodedSize: r.decodedBodySize,
        duration: r.duration
      });

      if (r.transferSize > 0) {
        byType[type].transferSize += r.transferSize;
        byType[type].decodedSize += r.decodedBodySize;
        totalTransfer += r.transferSize;
        totalDecoded += r.decodedBodySize;
        measuredCount++;
      } else {
        unmeasuredCount++;
        unmeasuredUrls.push(r.name);
      }
    });

    if (navigation && navigation.transferSize > 0) {
      totalTransfer += navigation.transferSize;
      totalDecoded += navigation.decodedBodySize;
      byType['document'] = {
        count: 1,
        transferSize: navigation.transferSize,
        decodedSize: navigation.decodedBodySize,
        items: [{
          name: navigation.name,
          transferSize: navigation.transferSize,
          decodedSize: navigation.decodedBodySize,
          duration: navigation.duration
        }]
      };
    }

    return {
      totalTransfer,
      totalDecoded,
      measuredCount,
      unmeasuredCount,
      unmeasuredUrls,
      resourceCount: resources.length + 1,
      byType,
      loadTime: navigation ? navigation.loadEventEnd - navigation.startTime : 0
    };
  }

  collectData() {
    const update = () => {
      const data = this.getResourceData();
      this.updateBadge(data);
      this.updateModalIfOpen(data);
    };
    update();
    setInterval(update, 500);
  }

  updateBadge(data) {
    const sizeEl = this.shadowRoot.getElementById('size');
    const countEl = this.shadowRoot.getElementById('count');
    sizeEl.textContent = this.formatBytes(data.totalTransfer);
    countEl.textContent = `${data.resourceCount} requests`;
    this.currentData = data;
  }

  updateModalIfOpen(data) {
    const dialog = this.shadowRoot.getElementById('dialog');
    if (dialog && dialog.open) {
      this.renderModalContent(data);
    }
  }

  renderModalContent(data) {
    const content = this.shadowRoot.getElementById('details');

    if (!data) return;

    // Save the open state of details elements before updating
    const openDetails = new Set();
    content.querySelectorAll('details[open]').forEach(details => {
      const identifier = details.dataset.type;
      if (identifier) {
        openDetails.add(identifier);
      }
    });

    let html = `
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-value">${this.formatBytes(data.totalTransfer)}</div>
          <div class="summary-label">Transferred</div>
        </div>
        <div class="summary-card">
          <div class="summary-value">${this.formatBytes(data.totalDecoded)}</div>
          <div class="summary-label">Uncompressed</div>
        </div>
        <div class="summary-card">
          <div class="summary-value">${data.resourceCount}</div>
          <div class="summary-label">Requests</div>
        </div>
        <div class="summary-card">
          <div class="summary-value">${Math.round(data.loadTime)}ms</div>
          <div class="summary-label">Load Time</div>
        </div>
      </div>
    `;

    if (data.unmeasuredCount > 0) {
      html += `
        <details class="warning-details" data-type="warning">
          <summary class="warning">⚠️ ${data.unmeasuredCount} cross-origin resource${data.unmeasuredCount !== 1 ? 's' : ''} couldn't be measured (missing Timing-Allow-Origin header)</summary>
          <ul class="unmeasured-list">
            ${data.unmeasuredUrls.map(url => `<li title="${url}">${this.truncateUrl(url)}</li>`).join('')}
          </ul>
        </details>
      `;
    }

    html += `<h3>By Resource Type</h3>`;

    const typeLabels = {
      document: '📄 Document',
      script: '📜 Scripts',
      link: '🎨 Stylesheets',
      img: '🖼️ Images',
      fetch: '🔄 Fetch/XHR',
      xmlhttprequest: '🔄 XHR',
      css: '🎨 CSS',
      font: '🔤 Fonts',
      other: '📦 Other'
    };

    for (const [type, info] of Object.entries(data.byType).sort((a, b) => b[1].transferSize - a[1].transferSize)) {
      const label = typeLabels[type] || `📦 ${type}`;
      html += `
        <details class="type-group" data-type="${type}">
          <summary>
            <span class="type-label">${label}</span>
            <span class="type-stats">${info.count} file${info.count !== 1 ? 's' : ''} · ${this.formatBytes(info.transferSize)}</span>
          </summary>
          <ul class="resource-list">
            ${info.items.map(item => `
              <li>
                <span class="resource-name" title="${item.name}">${this.truncateUrl(item.name)}</span>
                <span class="resource-size">${item.transferSize > 0 ? this.formatBytes(item.transferSize) : '(hidden)'}</span>
              </li>
            `).join('')}
          </ul>
        </details>
      `;
    }

    content.innerHTML = html;

    // Restore the open state of details elements after updating
    content.querySelectorAll('details').forEach(details => {
      const identifier = details.dataset.type;
      if (identifier && openDetails.has(identifier)) {
        details.open = true;
      }
    });
  }

  showModal() {
    const dialog = this.shadowRoot.getElementById('dialog');
    const data = this.currentData;

    if (!data) return;

    this.renderModalContent(data);
    dialog.showModal();
  }

  truncateUrl(url, maxLength = 60) {
    try {
      const u = new URL(url);
      const path = u.pathname + u.search;
      const full = u.host + path;
      if (full.length > maxLength) {
        const available = maxLength - u.host.length - 4;
        if (available > 10) {
          return u.host + '/...' + path.slice(-(available));
        }
        return full.slice(0, maxLength - 3) + '...';
      }
      return full;
    } catch {
      return url.length > maxLength ? url.slice(0, maxLength - 3) + '...' : url;
    }
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --pwm-bg: #1a1a2e;
          --pwm-bg-light: #252542;
          --pwm-accent: #4ade80;
          --pwm-text: #e2e8f0;
          --pwm-text-muted: #94a3b8;
          --pwm-border: #334155;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        #badge {
          position: fixed;
          bottom: 12px;
          right: 12px;
          background: var(--pwm-bg);
          color: var(--pwm-text);
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          z-index: 99999;
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
          border: 1px solid var(--pwm-border);
          transition: transform 0.15s, box-shadow 0.15s;
        }

        #badge:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }

        .icon {
          font-size: 16px;
        }

        #size {
          font-weight: 600;
          color: var(--pwm-accent);
        }

        #count {
          color: var(--pwm-text-muted);
          font-size: 11px;
        }

        dialog {
          background: var(--pwm-bg);
          color: var(--pwm-text);
          border: 1px solid var(--pwm-border);
          border-radius: 12px;
          padding: 0;
          max-width: 600px;
          width: 90vw;
          max-height: 80vh;
          box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        }

        dialog::backdrop {
          background: rgba(0,0,0,0.6);
          backdrop-filter: blur(4px);
        }

        .dialog-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid var(--pwm-border);
          position: sticky;
          top: 0;
          background: var(--pwm-bg);
        }

        .dialog-header h2 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }

        .close-btn {
          background: none;
          border: none;
          color: var(--pwm-text-muted);
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          line-height: 1;
        }

        .close-btn:hover {
          color: var(--pwm-text);
        }

        .dialog-body {
          padding: 20px;
          overflow-y: auto;
          max-height: calc(80vh - 60px);
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }

        .summary-card {
          background: var(--pwm-bg-light);
          padding: 14px;
          border-radius: 8px;
          text-align: center;
        }

        .summary-value {
          font-size: 18px;
          font-weight: 700;
          color: var(--pwm-accent);
        }

        .summary-label {
          font-size: 11px;
          color: var(--pwm-text-muted);
          margin-top: 4px;
        }

        .warning-details {
          margin-bottom: 16px;
        }

        .warning {
          background: #422006;
          color: #fbbf24;
          padding: 10px 14px;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
          list-style: none;
        }

        .warning::-webkit-details-marker {
          display: none;
        }

        .warning::before {
          content: '▶ ';
          font-size: 10px;
        }

        .warning-details[open] .warning::before {
          content: '▼ ';
        }

        .unmeasured-list {
          list-style: none;
          margin: 8px 0 0 0;
          padding: 10px 14px;
          background: #351c05;
          border-radius: 0 0 6px 6px;
          font-size: 11px;
        }

        .unmeasured-list li {
          padding: 4px 0;
          color: #fcd34d;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        h3 {
          font-size: 13px;
          color: var(--pwm-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin: 0 0 12px 0;
        }

        .type-group {
          margin-bottom: 8px;
          background: var(--pwm-bg-light);
          border-radius: 8px;
        }

        .type-group summary {
          padding: 12px 14px;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          list-style: none;
        }

        .type-group summary::-webkit-details-marker {
          display: none;
        }

        .type-group summary::before {
          content: '▶';
          font-size: 10px;
          margin-right: 10px;
          transition: transform 0.2s;
        }

        .type-group[open] summary::before {
          transform: rotate(90deg);
        }

        .type-label {
          font-weight: 500;
        }

        .type-stats {
          color: var(--pwm-text-muted);
          font-size: 12px;
        }

        .resource-list {
          list-style: none;
          margin: 0;
          padding: 0 14px 12px 32px;
        }

        .resource-list li {
          display: flex;
          justify-content: space-between;
          padding: 6px 0;
          font-size: 12px;
          border-top: 1px solid var(--pwm-border);
        }

        .resource-name {
          color: var(--pwm-text-muted);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 70%;
        }

        .resource-size {
          color: var(--pwm-text);
          font-family: monospace;
        }

        @media (max-width: 500px) {
          .summary-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      </style>

      <div id="badge" title="Click for details">
        <span class="icon">📊</span>
        <div>
          <div id="size">measuring...</div>
          <div id="count">—</div>
        </div>
      </div>

      <dialog id="dialog">
        <div class="dialog-header">
          <h2>📊 Page Weight Details</h2>
          <button class="close-btn" id="close">&times;</button>
        </div>
        <div class="dialog-body" id="details"></div>
      </dialog>
    `;

    this.shadowRoot.getElementById('badge').addEventListener('click', () => this.showModal());
    this.shadowRoot.getElementById('close').addEventListener('click', () => {
      this.shadowRoot.getElementById('dialog').close();
    });
    this.shadowRoot.getElementById('dialog').addEventListener('click', (e) => {
      if (e.target.tagName === 'DIALOG') {
        e.target.close();
      }
    });
  }
}

customElements.define('page-weight-monitor', PageWeightMonitor);

// Auto-insert the component when this module is imported, if PAGE_WEIGHT is set in localStorage
if (localStorage.getItem('PAGE_WEIGHT') !== null) {
    document.body.appendChild(document.createElement('page-weight-monitor'));
}