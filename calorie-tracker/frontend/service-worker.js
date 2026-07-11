const CACHE_NAME = 'food-reader-v16';
const ASSET_VERSION = '20260711-1';
const withVersion = (path) => `${path}?v=${ASSET_VERSION}`;
const APP_SHELL = [
  '/', '/coach.html', '/index.html', '/login.html', '/history.html', '/metrics.html', '/profile.html', '/offline.html',
  withVersion('/styles.css'), withVersion('/coach.css'), withVersion('/common.js'), withVersion('/coach.js'),
  withVersion('/home.js'), withVersion('/login.js'), withVersion('/history.js'), withVersion('/metrics.js'), withVersion('/profile.js'), withVersion('/charts.js'), withVersion('/manifest.webmanifest'),
  '/assets/favicon/apple-touch-icon.png', '/assets/favicon/icon-192.png', '/assets/favicon/icon-512.png', '/assets/favicon/favicon-32x32.png', '/assets/favicon/favicon-16x16.png', '/assets/favicon/favicon.svg', '/assets/images/text-meal-placeholder.svg',
];
const API_PREFIXES = ['/auth', '/users', '/me', '/profile', '/withings', '/coach', '/uploads'];
const NETWORK_FIRST_EXTENSIONS = /\.(?:html|css|js|webmanifest)$/;

function shouldUseNetworkFirst(request, url) { return request.mode === 'navigate' || NETWORK_FIRST_EXTENSIONS.test(url.pathname); }
async function updateCache(cacheName, request, response) { if (!response || !response.ok) return; const cache = await caches.open(cacheName); await cache.put(request, response.clone()); }

self.addEventListener('install', (event) => { event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))); self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))); self.clients.claim(); });
self.addEventListener('fetch', (event) => {
  const { request } = event; if (request.method !== 'GET') return;
  const url = new URL(request.url); if (url.origin !== self.location.origin || API_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) return;
  if (shouldUseNetworkFirst(request, url)) {
    event.respondWith(fetch(request).then(async (response) => { await updateCache(CACHE_NAME, request, response); return response; }).catch(async () => (await caches.match(request)) || (request.mode === 'navigate' ? caches.match('/offline.html') : Response.error())));
    return;
  }
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => { void updateCache(CACHE_NAME, request, response); return response; })));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/coach.html';
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
    const existing = windows.find((client) => new URL(client.url).pathname === url);
    return existing ? existing.focus() : clients.openWindow(url);
  }));
});
