/* 틀린그림찾기 서비스 워커 — 첫 방문 뒤에는 오프라인에서도 실행됩니다. */
const CACHE = 'spotdiff-v1';

const PRECACHE = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './stages.js',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/icon-rounded-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png',
  './images/stage_01_a.webp',
  './images/stage_01_b.webp',
  './images/stage_02_a.webp',
  './images/stage_02_b.webp',
  './images/stage_03_a.webp',
  './images/stage_03_b.webp',
  './images/stage_04_a.webp',
  './images/stage_04_b.webp',
  './images/stage_05_a.webp',
  './images/stage_05_b.webp',
  './images/thumbs/stage_01_a.jpg',
  './images/thumbs/stage_02_a.jpg',
  './images/thumbs/stage_03_a.jpg',
  './images/thumbs/stage_04_a.jpg',
  './images/thumbs/stage_05_a.jpg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') { return; }

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) { return; }

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match('./index.html')))
    );
    return;
  }

  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) { return hit; }
      return fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => hit);
    })
  );
});
