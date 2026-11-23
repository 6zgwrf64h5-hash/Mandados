/* Meu Treino: sempre busca a versão nova quando tem internet; sem internet, abre a última guardada.
   Fica na pasta /treino, então manda só no app de treino (o sw.js do Mandados não interfere aqui). */
const VERSAO = 'treino-v1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith('treino-') && k !== VERSAO).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') { return; }
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.indexOf('/treino/') === -1) { return; }
  e.respondWith(
    fetch(req, { cache: 'no-store' }).then((r) => { if (r && r.ok) { const c = r.clone(); caches.open(VERSAO).then((k) => k.put(req, c)); } return r; })
      .catch(() => caches.match(req, { ignoreSearch: true }).then((c) => c || caches.match('./index.html') || caches.match('./')))
  );
});
