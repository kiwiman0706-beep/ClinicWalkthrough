// Service worker for the clinic walkthrough PWA.
// The app is a single self-contained HTML file with no external requests, so a
// small precache is enough to make it work fully offline once installed.
// Bump CACHE_VERSION whenever index.html or the icons change.
const CACHE_VERSION = 'clinic-walkthrough-v29';
const PRECACHE = [
  './',
  './index.html',
  './hq.js',
  './vendor/three.min.js',
  './textures/DEC8296.jpg',
  './textures/ECP-315_VSR1N.jpg',
  './textures/ECP-315_VSR2N.jpg',
  './textures/ECP-315_VSR3N.jpg',
  './textures/FS4274.jpg',
  './textures/FS4276.jpg',
  './textures/JC-12031K.jpg',
  './textures/LJ-10234KN74.jpg',
  './textures/PWT4290.jpg',
  './textures/Panasonic_RV.jpg',
  './textures/TH6019.jpg',
  './textures/TH60415.jpg',
  './textures/TJ-2062K.jpg',
  './textures/WVP8041.jpg',
  './textures/WVP8069.jpg',
  './textures/WVP8255.jpg',
  './textures/WVP8256.jpg',
  './textures/WVP8257.jpg',
  './textures/WVP8473.jpg',
  './textures/WVP8492.jpg',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/maskable-192.png',
  './icons/maskable-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      // Bypass the HTTP cache: GitHub Pages tells the browser to keep index.html
      // for ten minutes, which would otherwise precache the version we just replaced.
      .then(cache => cache.addAll(PRECACHE.map(url => new Request(url, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_VERSION).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  // Navigations: network first so a redeploy is picked up, cache as the offline fallback.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(new Request(request.url, { cache: 'reload', credentials: 'same-origin' }))
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then(cache => cache.put('./index.html', copy));
          return response;
        })
        .catch(() => caches.match('./index.html', { ignoreSearch: true }).then(hit => hit ?? caches.match('./')))
    );
    return;
  }

  // Everything else: cache first, refreshing the entry in the background.
  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then(hit => {
      const network = fetch(request)
        .then(response => {
          if (response.ok && response.type === 'basic') {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then(cache => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => hit);
      return hit ?? network;
    })
  );
});
