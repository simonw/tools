export default {
  /**
   * Main request handler
   */
  async fetch(request, env) {
    /**
     * Small helper to build HTML responses (success + error)
     */
    const html = (
      { title, body, isError = false, extraHeaders = {} },
    ) =>
      new Response(
        `<!DOCTYPE html>
         <html lang="en">
           <head>
             <meta charset="utf-8">
             <title>${title}</title>
             <style>
               body{font-family:-apple-system,system-ui,sans-serif;
                    max-width:680px;margin:3rem auto;padding:0 1rem;text-align:center;}
               .card{border:1px solid ${isError ? "#ffcdd2" : "#c8e6c9"};
                     background:${isError ? "#ffebee" : "#e8f5e9"};
                     padding:1rem;border-radius:6px;}
               img{border-radius:50%;vertical-align:middle;margin-right:.5rem}
               ul{list-style:none;padding:0}
             </style>
           </head>
           <body>
             <div class="card">${body}</div>
             ${isError
          ? "<p>Please close this window and try again.</p>"
          : ""}
           </body>
         </html>`,
        {
          status: isError ? 400 : 200,
          headers: { "Content-Type": "text/html", ...extraHeaders },
        },
      );

    try {
      const url = new URL(request.url);

      // =============== 1. First visit → kick off OAuth flow ===============
      if (!url.searchParams.has("code")) {
        // Anti-CSRF state value
        const state = crypto.randomUUID();

        const authURL = new URL("https://accounts.google.com/o/oauth2/v2/auth");
        authURL.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
        authURL.searchParams.set("redirect_uri", env.GOOGLE_REDIRECT_URI);
        authURL.searchParams.set("response_type", "code");
        authURL.searchParams.set(
          "scope",
          "https://www.googleapis.com/auth/youtube.readonly",
        );
        authURL.searchParams.set("state", state);
        authURL.searchParams.set("access_type", "offline"); // ask for refresh_token

        return new Response(null, {
          status: 302,
          headers: {
            Location: authURL.toString(),
            "Set-Cookie":
              `yt_state=${state}; HttpOnly; Secure; SameSite=Lax; Max-Age=3600; Path=/`,
          },
        });
      }

      // =============== 2. Callback request ===============
      const { code, state: returnedState } = Object.fromEntries(
        url.searchParams,
      );

      // 2a. Validate state cookie to mitigate CSRF
      const cookieHeader = request.headers.get("Cookie") || "";
      const savedState = cookieHeader
        .split(";")
        .map((c) => c.trim())
        .find((c) => c.startsWith("yt_state="))
        ?.split("=")[1];

      const clearStateCookie =
        "yt_state=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/";

      if (!savedState || savedState !== returnedState) {
        return html({
          title: "Security error",
          body:
            "<h2>Invalid state parameter.</h2><p>Potential CSRF detected.</p>",
          isError: true,
          extraHeaders: { "Set-Cookie": clearStateCookie },
        });
      }

      // 2b. Exchange code for access_token
      const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          code,
          client_id: env.GOOGLE_CLIENT_ID,
          client_secret: env.GOOGLE_CLIENT_SECRET,
          redirect_uri: env.GOOGLE_REDIRECT_URI,
          grant_type: "authorization_code",
        }),
      });

      const tokenJson = await tokenRes.json();
      if (tokenJson.error) {
        return html({
          title: "OAuth error",
          body: `<h2>${tokenJson.error}</h2><p>${tokenJson.error_description ??
            ""}</p>`,
          isError: true,
          extraHeaders: { "Set-Cookie": clearStateCookie },
        });
      }

      const accessToken = tokenJson.access_token;

      // 2c. Call YouTube Data API to fetch subscriptions
      const ytRes = await fetch(
        "https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=50",
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );

      if (!ytRes.ok) {
        return html({
          title: "YouTube API error",
          body:
            `<h2>Unable to fetch subscriptions.</h2><p>Status: ${ytRes.status}</p>`,
          isError: true,
          extraHeaders: { "Set-Cookie": clearStateCookie },
        });
      }

      const ytJson = await ytRes.json();

      const listItems = ytJson.items
        .map(
          (sub) =>
            `<li><img src="${sub.snippet.thumbnails.default.url}" width="40" height="40" alt="">
             ${sub.snippet.title}</li>`,
        )
        .join("");

      return html({
        title: "Your YouTube Subscriptions",
        body:
          `<h2>Subscriptions (${ytJson.items.length})</h2><ul>${listItems}</ul>
           <p>You can close this window now.</p>`,
        extraHeaders: { "Set-Cookie": clearStateCookie },
      });
    } catch (err) {
      return html({
        title: "Unexpected error",
        body: `<h2>Unexpected error</h2><p>${err.message}</p>`,
        isError: true,
      });
    }
  },
};
