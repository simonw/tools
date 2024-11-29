export default {
  async fetch(request, env) {
    const generateHTML = ({ title, content, isError = false }) => {
      return new Response(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${title}</title>
            <style>
              body {
                font-family: -apple-system, system-ui, sans-serif;
                padding: 2rem;
                max-width: 600px;
                margin: 0 auto;
                text-align: center;
              }
              .message {
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 4px;
                background-color: ${isError ? '#ffebee' : '#e8f5e9'};
                border: 1px solid ${isError ? '#ffcdd2' : '#c8e6c9'};
                color: ${isError ? '#b71c1c' : '#2e7d32'};
              }
            </style>
          </head>
          <body>
            <div class="message">
              ${content}
            </div>
            ${isError ? '<p>Please close this window and try again. If the problem persists, contact support.</p>' : ''}
          </body>
        </html>
      `, {
        headers: { 'Content-Type': 'text/html' },
        status: isError ? 400 : 200
      });
    };

    try {
      const url = new URL(request.url);
      const clientId = env.GITHUB_CLIENT_ID;
      const clientSecret = env.GITHUB_CLIENT_SECRET;
      const redirectUri = env.GITHUB_REDIRECT_URI;
      
      if (!url.searchParams.has('code')) {
        const githubAuthUrl = new URL('https://github.com/login/oauth/authorize');
        githubAuthUrl.searchParams.set('client_id', clientId);
        githubAuthUrl.searchParams.set('redirect_uri', redirectUri);
        githubAuthUrl.searchParams.set('scope', 'gist');
        githubAuthUrl.searchParams.set('state', crypto.randomUUID());
        return Response.redirect(githubAuthUrl.toString(), 302);
      }

      const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          code: url.searchParams.get('code'),
          redirect_uri: redirectUri
        })
      });
      
      const tokenData = await tokenResponse.json();
      
      if (tokenData.error) {
        return generateHTML({
          title: 'GitHub OAuth Error',
          content: `
            <h3>Authentication Error</h3>
            <p>Error: ${tokenData.error}</p>
            ${tokenData.error_description ? `<p>Description: ${tokenData.error_description}</p>` : ''}
          `,
          isError: true
        });
      }
      
      return generateHTML({
        title: 'GitHub OAuth Success',
        content: `
          <h2>Authentication successful!</h2>
          <p>You can close this window.</p>
          <script>
            try {
              localStorage.setItem('github_token', '${tokenData.access_token}');
            } catch (err) {
              document.body.innerHTML += '<p style="color: #c62828;">Warning: Unable to store token in localStorage</p>';
            }
          </script>
        `
      });

    } catch (error) {
      return generateHTML({
        title: 'Unexpected Error',
        content: `
          <h3>Unexpected Error</h3>
          <p>An unexpected error occurred during authentication.</p>
          <p>Details: ${error.message}</p>
        `,
        isError: true
      });
    }
  }
};
