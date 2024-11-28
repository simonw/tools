export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const clientId = env.GITHUB_CLIENT_ID;
    const clientSecret = env.GITHUB_CLIENT_SECRET;
    const redirectUri = env.GITHUB_REDIRECT_URI;
    
    // If we have a code, exchange it for an access token
    if (url.searchParams.has('code')) {
      const code = url.searchParams.get('code');
      
      // Exchange the code for an access token
      const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          code: code,
          redirect_uri: redirectUri
        })
      });
      
      const tokenData = await tokenResponse.json();
      
      // Return HTML that stores the token and closes the window
      return new Response(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>GitHub OAuth Success</title>
          </head>
          <body>
            <script>
              localStorage.setItem('github_token', '${tokenData.access_token}');
              document.body.innerHTML = 'Authentication successful! You can close this window.';
            </script>
          </body>
        </html>
      `, {
        headers: {
          'Content-Type': 'text/html'
        }
      });
    }
    
    // If no code, redirect to GitHub OAuth
    const githubAuthUrl = new URL('https://github.com/login/oauth/authorize');
    githubAuthUrl.searchParams.set('client_id', clientId);
    githubAuthUrl.searchParams.set('redirect_uri', redirectUri);
    githubAuthUrl.searchParams.set('scope', 'gist');
    githubAuthUrl.searchParams.set('state', crypto.randomUUID());
    
    return Response.redirect(githubAuthUrl.toString(), 302);
  }
};
