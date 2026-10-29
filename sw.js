// Создаётся при сборке (vite.config.ts). Не редактировать вручную.
const CACHE = 'olympiads-e2856bc2b141';
const FILES = ["./","assets/golos-text-cyrillic-600-normal-C24T-5ZM.woff2","assets/golos-text-cyrillic-400-normal-Du08II1m.woff2","assets/golos-text-latin-400-normal-BRtgm2Ku.woff2","assets/golos-text-cyrillic-700-normal-BMNsYb1I.woff2","assets/unbounded-cyrillic-600-normal-DW6uzIMB.woff2","assets/unbounded-cyrillic-700-normal-DMBAjPn6.woff2","assets/unbounded-latin-700-normal-CRkNGKoV.woff2","assets/golos-text-cyrillic-400-normal-Ceu9bpXK.woff","assets/golos-text-cyrillic-600-normal-Dw66BQxA.woff","assets/golos-text-latin-400-normal-DzzaOOeY.woff","assets/golos-text-cyrillic-700-normal-Di-oX6KR.woff","assets/unbounded-cyrillic-600-normal-iltWiMfk.woff","assets/unbounded-cyrillic-700-normal-BVvDsduZ.woff","assets/unbounded-latin-700-normal-By2CwDai.woff","assets/index-HjSGGXWU.css","assets/index-Cw0p7Lgk.js","assets/web-9SCe7dvY.js","assets/web-CcobYJCL.js","assets/web-DIN5EGtO.js","icons/apple-touch-icon.png","icons/favicon-32.png","icons/icon-192.png","icons/icon-512.png","manifest.webmanifest","Olimpiady-iPhone.mobileconfig"];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('olympiads-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  if (new URL(req.url).pathname.includes('/data/')) return; // данные — забота приложения
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(() => caches.match('./', { ignoreSearch: true })));
    return;
  }
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
