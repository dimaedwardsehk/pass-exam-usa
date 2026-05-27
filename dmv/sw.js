const CACHE_NAME = 'dmv-prep-v1';
const ASSETS = [
  '/pass-exam-usa/dmv/',
  '/pass-exam-usa/dmv/index.html',
  '/pass-exam-usa/dmv/styles.css',
  '/pass-exam-usa/dmv/app.js',
  '/pass-exam-usa/dmv/data/questions.json',
  '/pass-exam-usa/dmv/manifest.webmanifest'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
