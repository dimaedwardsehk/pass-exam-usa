/* CDL Master Prep PWA service worker */
const BASE = '/pass-exam-usa/cdl';
const CACHE = 'cdl-master-prep-v7-4';
const PRECACHE = [
  BASE + '/',
  BASE + '/index.html',
  BASE + '/manifest.webmanifest',
  BASE + '/favicon.ico',
  BASE + '/pwa/icon-192.png',
  BASE + '/pwa/icon-512.png',
  BASE + '/pwa/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Only handle requests within our PWA scope
  if (!url.pathname.startsWith(BASE)) return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req);
      const fetchPromise = fetch(req)
        .then((response) => {
          if (response && response.status === 200 && response.type === 'basic') {
            cache.put(req, response.clone());
          }
          return response;
        })
        .catch(() => cached || cache.match(BASE + '/index.html'));
      return cached || fetchPromise;
    })
  );
});
