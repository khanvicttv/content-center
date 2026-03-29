const CACHE = 'kcc-v3';
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
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // For the main HTML — always try network first, fall back to cache
  // This ensures updates are picked up immediately
  if (e.request.url.includes('index.html') || e.request.url.endsWith('/content-center/')) {
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
  // For everything else — cache first, network fallback
  e.respondWith(
    caches.match(e.request).then(cached => {
      return cached || fetch(e.request).catch(() => caches.match('/content-center/index.html'));
    })
  );
});
