const CACHE_NAME = 'food-reader-v1';
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

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(async () => (await caches.match(request)) || caches.match('/offline.html')),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        }),
    ),
  );
});
