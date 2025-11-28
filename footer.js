(function() {
    // Get the current filename from the URL
    let pathname = window.location.pathname;
    let filename = pathname.split('/').pop() || 'index.html';

    // Add .html if missing
    if (!filename.endsWith('.html')) {
        filename += '.html';
    }

    // Detect if background is dark
    function isDarkBackground() {
        const bgColor = window.getComputedStyle(document.body).backgroundColor;
        const match = bgColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
        if (match) {
            const r = parseInt(match[1]);
            const g = parseInt(match[2]);
            const b = parseInt(match[3]);
            const a = match[4] !== undefined ? parseFloat(match[4]) : 1;
            // If transparent, assume light background (browser default is white)
            if (a < 0.1) {
                return false;
            }
            // Calculate relative luminance
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            return luminance < 0.5;
        }
        return false;
    }

    const isDark = isDarkBackground();
    const linkColor = isDark ? '#ffffff' : '#0066cc';
    const hrColor = isDark ? '#666' : '#ccc';
    const textColor = isDark ? '#ccc' : '#666';

    // Create the footer element
    const footer = document.createElement('footer');
    footer.innerHTML = `
        <hr style="margin: 2rem 0 1rem 0; border: none; border-top: 1px solid ${hrColor};">
        <nav style="font-family: system-ui, -apple-system, sans-serif; font-size: 12px; color: ${textColor}; padding-left: 0.5rem;">
            <a href="/" style="color: ${linkColor}; text-decoration: none; margin-right: 1.5rem;">Home</a>
            <a href="https://github.com/simonw/tools/blob/main/${filename}" style="color: ${linkColor}; text-decoration: none; margin-right: 1.5rem;">View source</a>
            <a href="https://github.com/simonw/tools/commits/main/${filename}" style="color: ${linkColor}; text-decoration: none;">Commit history</a>
        </nav>
    `;

    document.body.appendChild(footer);
})();
