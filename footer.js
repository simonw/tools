(function() {
    // Get the current filename from the URL
    let pathname = window.location.pathname;
    let filename = pathname.split('/').pop() || 'index.html';

    // Add .html if missing
    if (!filename.endsWith('.html')) {
        filename += '.html';
    }

    // Create the footer element
    const footer = document.createElement('footer');
    footer.innerHTML = `
        <hr style="margin: 2rem 0 1rem 0; border: none; border-top: 1px solid #ccc;">
        <nav style="font-family: system-ui, -apple-system, sans-serif; font-size: 14px; color: #666; padding-left: 0.5rem;">
            <a href="/" style="color: #0066cc; text-decoration: none; margin-right: 1.5rem;">Home</a>
            <a href="https://github.com/simonw/tools/blob/main/${filename}" style="color: #0066cc; text-decoration: none; margin-right: 1.5rem;">View source</a>
            <a href="https://github.com/simonw/tools/commits/main/${filename}" style="color: #0066cc; text-decoration: none;">Commit history</a>
        </nav>
    `;

    document.body.appendChild(footer);
})();
