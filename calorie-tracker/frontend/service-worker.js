const CACHE_NAME = 'food-reader-v2';
const APP_SHELL = [
  '/',
  '/index.html',
  '/login.html',
  '/history.html',
  '/metrics.html',
  '/profile.html',
  '/offline.html',
  '/styles.css',
  '/common.js',
  '/home.js',
  '/login.js',
  '/history.js',
  '/metrics.js',
  '/profile.js',
  '/charts.js',
  '/manifest.webmanifest',
  '/assets/favicon/apple-touch-icon.png',
  '/assets/favicon/favicon-32x32.png',
  '/assets/favicon/favicon-16x16.png',
  '/assets/favicon/favicon.svg',
  '/assets/images/text-meal-placeholder.svg',
];

const API_PREFIXES = ['/auth', '/users', '/me', '/profile', '/uploads'];
const NETWORK_FIRST_EXTENSIONS = /\.(?:html|css|js|webmanifest)$/;

function shouldUseNetworkFirst(request, url) {
  return request.mode === 'navigate' || NETWORK_FIRST_EXTENSIONS.test(url.pathname);
}

async function updateCache(cacheName, request, response) {
  const cache = await caches.open(cacheName);
  await cache.put(request, response.clone());
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (API_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) {
    return;
  }

  if (shouldUseNetworkFirst(request, url)) {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          await updateCache(CACHE_NAME, request, response);
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) {
            return cached;
          }
          return request.mode === 'navigate' ? caches.match('/offline.html') : Response.error();
        }),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          updateCache(CACHE_NAME, request, response);
          return response;
        }),
    ),
  );
});
