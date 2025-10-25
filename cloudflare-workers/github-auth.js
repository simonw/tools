export default {
  async fetch(request, env) {
    const generateHTML = ({ title, content, isError = false, headers = {} }) => {
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
        headers: {
          'Content-Type': 'text/html',
          ...headers
        },
        status: isError ? 400 : 200
      });
    };

    try {
      const url = new URL(request.url);
      const clientId = env.GITHUB_CLIENT_ID;
      const clientSecret = env.GITHUB_CLIENT_SECRET;
      const redirectUri = env.GITHUB_REDIRECT_URI;
      
      if (!url.searchParams.has('code')) {
        // Initial authorization request
        const state = crypto.randomUUID();
        const githubAuthUrl = new URL('https://github.com/login/oauth/authorize');
        githubAuthUrl.searchParams.set('client_id', clientId);
        githubAuthUrl.searchParams.set('redirect_uri', redirectUri);
        githubAuthUrl.searchParams.set('scope', 'gist');
        githubAuthUrl.searchParams.set('state', state);

        // Create headers object with the state cookie
        const headers = new Headers({
          'Location': githubAuthUrl.toString(),
          'Set-Cookie': `github_auth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=3600`
        });

        return new Response(null, {
          status: 302,
          headers
        });
      }

      // Callback handling
      const returnedState = url.searchParams.get('state');
      const cookies = request.headers.get('Cookie') || '';
      const stateCookie = cookies.split(';')
        .map(cookie => cookie.trim())
        .find(cookie => cookie.startsWith('github_auth_state='));
      const savedState = stateCookie ? stateCookie.split('=')[1] : null;

      // Cookie cleanup header
      const clearStateCookie = {
        'Set-Cookie': 'github_auth_state=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0'
      };

      // Validate state parameter
      if (!savedState || savedState !== returnedState) {
        return generateHTML({
          title: 'Invalid State Parameter',
          content: `
            <h3>Security Error</h3>
            <p>Invalid state parameter detected. This could indicate a CSRF attempt.</p>
          `,
          isError: true,
          headers: clearStateCookie
        });
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
          redirect_uri: redirectUri,
          state: returnedState
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
          isError: true,
          headers: clearStateCookie
        });
      }
      
      // Success response with cookie cleanup
      return generateHTML({
        title: 'GitHub OAuth Success',
        content: `
          <h2>Authentication successful!</h2>
          <p>You can close this window.</p>
          <script>
            try {
              localStorage.setItem('GITHUB_TOKEN', '${tokenData.access_token}');
            } catch (err) {
              document.body.innerHTML += '<p style="color: #c62828;">Warning: Unable to store token in localStorage</p>';
            }
          </script>
        `,
        headers: clearStateCookie
      });

    } catch (error) {
      // Error response with cookie cleanup
      return generateHTML({
        title: 'Unexpected Error',
        content: `
          <h3>Unexpected Error</h3>
          <p>An unexpected error occurred during authentication.</p>
          <p>Details: ${error.message}</p>
        `,
        isError: true,
        headers: {
          'Set-Cookie': 'github_auth_state=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0'
        }
      });
    }
  }
};
