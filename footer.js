(function() {
    // Get the current filename from the URL
    let pathname = window.location.pathname;
    let filename = pathname.split('/').pop() || 'index.html';

    // Add .html if missing
    if (!filename.endsWith('.html')) {
        filename += '.html';
    }

    // Find the most common text color on the page
    function getMostCommonTextColor() {
        const colorCounts = {};
        const elements = document.body.querySelectorAll('*');

        elements.forEach(el => {
            // Skip script, style, and hidden elements
            if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'NOSCRIPT') {
                return;
            }

            // Only count elements that have direct text content
            const hasDirectText = Array.from(el.childNodes).some(
                node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
            );

            if (hasDirectText) {
                const style = window.getComputedStyle(el);
                const color = style.color;

                // Skip fully transparent colors
                const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
                if (match) {
                    const a = match[4] !== undefined ? parseFloat(match[4]) : 1;
                    if (a < 0.1) return;
                }

                colorCounts[color] = (colorCounts[color] || 0) + 1;
            }
        });

        // Find the most common color
        let mostCommon = null;
        let maxCount = 0;

        for (const [color, count] of Object.entries(colorCounts)) {
            if (count > maxCount) {
                maxCount = count;
                mostCommon = color;
            }
        }

        // Default fallback if no text color found
        return mostCommon || 'rgb(0, 0, 0)';
    }

    const textColor = getMostCommonTextColor();

    // Create the footer element
    const footer = document.createElement('footer');
    footer.innerHTML = `
        <hr style="margin: 2rem 0 1rem 0; border: none; border-top: 1px solid ${textColor};">
        <nav style="font-family: system-ui, -apple-system, sans-serif; font-size: 12px; padding-left: 0.5rem;">
            <a href="/" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">Home</a>
            <a href="https://github.com/simonw/tools/blob/main/${filename}" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">View source</a>
            <a href="https://github.com/simonw/tools/commits/main/${filename}" style="color: ${textColor}; text-decoration: underline;">Commit history</a>
        </nav>
    `;

    document.body.appendChild(footer);
})();
