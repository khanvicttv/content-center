const CACHE = 'kcc-v31';
const ASSETS = [
  '/content-center/',
  '/content-center/index.html',
  '/content-center/manifest.json',
  '/content-center/icon-192.png',
  '/content-center/icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => {
      // Tell all open tabs a new version is active
      self.clients.matchAll({ includeUncontrolled: true }).then(clients => {
        clients.forEach(client => client.postMessage({ type: 'UPDATE_AVAILABLE' }));
      });
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Always network-first for HTML — catches updates immediately
  if (e.request.mode === 'navigate' ||
      e.request.url.includes('index.html') ||
      e.request.url.endsWith('/content-center/')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(cache => cache.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }
  // Cache-first for everything else (icons, manifest)
  e.respondWith(
    caches.match(e.request).then(cached =>
      cached || fetch(e.request).catch(() => caches.match('/content-center/index.html'))
    )
  );
});

