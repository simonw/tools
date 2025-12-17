(function() {
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

    // Create the footer element
    const footer = document.createElement('footer');
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
})();
