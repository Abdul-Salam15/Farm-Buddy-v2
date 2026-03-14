importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.4.1/workbox-sw.js');

if (workbox) {
  console.log('Workbox is loaded');

  // Precache core assets
  workbox.precaching.precacheAndRoute([
    { url: '/chat/', revision: '1' },
    { url: '/static/css/accounts.css', revision: '1' },
    { url: '/static/js/chat.js', revision: '1' },
    { url: '/static/manifest.json', revision: '1' },
    { url: '/static/icons/icon-192.png', revision: '1' },
  ]);

  // Cache CSS/JS with Stale-While-Revalidate
  workbox.routing.registerRoute(
    ({ request }) => request.destination === 'style' || request.destination === 'script',
    new workbox.strategies.StaleWhileRevalidate({
      cacheName: 'static-resources',
    })
  );

  // Cache Images with Cache-First strategy
  workbox.routing.registerRoute(
    ({ request }) => request.destination === 'image',
    new workbox.strategies.CacheFirst({
      cacheName: 'images',
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxEntries: 50,
          maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
        }),
      ],
    })
  );

  // Network-first for chat history updates
  workbox.routing.registerRoute(
    ({ url }) => url.pathname.startsWith('/chat/'),
    new workbox.strategies.NetworkFirst({
      cacheName: 'api-responses',
    })
  );

  // Offline fallback
  workbox.recipes.offlineFallback({ pageFallback: '/chat/' });

} else {
  console.log('Workbox failed to load');
}
