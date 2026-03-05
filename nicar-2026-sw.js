// IMPORTANT: Bump this version number whenever nicar-2026.html or this file changes
const CACHE_NAME = 'nicar-2026-v4';
const SCHEDULE_URL = 'https://ire-nicar-conference-schedules.s3.us-east-2.amazonaws.com/nicar-2026/nicar-2026-schedule.json';
const ASSETS_TO_CACHE = [
    'nicar-2026.html',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    if (event.request.url === SCHEDULE_URL) {
        // Stale-while-revalidate for the schedule JSON
        event.respondWith(
            caches.open(CACHE_NAME).then(async cache => {
                const cachedResponse = await cache.match(event.request);

                const fetchPromise = fetch(event.request).then(networkResponse => {
                    if (networkResponse.ok) {
                        const cloned = networkResponse.clone();
                        // Compare with cached version to detect updates
                        cloned.text().then(async newText => {
                            const oldResponse = await cache.match(event.request);
                            let changed = true;
                            if (oldResponse) {
                                const oldText = await oldResponse.text();
                                changed = oldText !== newText;
                            }
                            // Store the fresh response in cache
                            await cache.put(event.request, new Response(newText, {
                                headers: networkResponse.headers,
                                status: networkResponse.status,
                            }));
                            if (changed && oldResponse) {
                                // Notify all clients that the schedule was updated
                                const clients = await self.clients.matchAll();
                                clients.forEach(client => {
                                    client.postMessage({ type: 'SCHEDULE_UPDATED' });
                                });
                            }
                        });
                    }
                    return networkResponse;
                }).catch(() => {
                    // Network failed - cached response will be used
                });

                // Return cached response immediately if available, otherwise wait for network
                if (cachedResponse) {
                    // Trigger background fetch but return cached version now
                    fetchPromise;
                    return cachedResponse;
                }
                return fetchPromise || new Response('{"sessions":[],"speakers":[]}', {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Cache-first for same-origin assets (the HTML page itself)
    // GitHub Pages serves pretty URLs: /nicar-2026 returns nicar-2026.html
    // so we need to try both the exact URL and the .html variant as cache keys
    if (url.origin === self.location.origin) {
        event.respondWith(
            (async () => {
                const cached = await caches.match(event.request)
                    || await caches.match(event.request.url + '.html');
                if (cached) {
                    // Background update
                    fetch(event.request).then(response => {
                        if (response.ok) {
                            caches.open(CACHE_NAME).then(cache => cache.put(event.request, response));
                        }
                    }).catch(() => {});
                    return cached;
                }
                const response = await fetch(event.request);
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            })()
        );
        return;
    }

    // Network-first for everything else
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
