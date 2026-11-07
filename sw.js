/* Mandados do dia: guarda o aplicativo no aparelho para abrir sem sinal.
   Troque o número da versão abaixo a cada atualização para o iPhone pegar a nova. */
const VERSAO = 'mandados-pwa-v37';
const CASCA = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable-512.png', './apple-touch-icon.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSAO && k.startsWith('mandados-')).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') { return; }
  const url = new URL(req.url);
  const mesmo = url.origin === self.location.origin;
  const biblioteca = url.hostname === 'cdnjs.cloudflare.com';
  if (mesmo && url.pathname.indexOf('/ruas/') !== -1) { return; }   /* pacotes de ruas: o próprio app guarda no aparelho; não duplicar no cache */
  if (!mesmo && !biblioteca) { return; }               /* IA, WhatsApp, Maps: sempre direto da internet */
  if (biblioteca) {                                    /* bibliotecas com versão fixa: guarda e reaproveita */
    e.respondWith(caches.match(req).then((c) => c || fetch(req).then((r) => { if (r && r.ok) { const copia = r.clone(); caches.open(VERSAO).then((k) => k.put(req, copia)); } return r; })));
    return;
  }
  e.respondWith(                                       /* a própria página: tenta a internet (para pegar atualização) e cai no que está guardado */
    fetch(req).then((r) => { if (r && r.ok) { const copia = r.clone(); caches.open(VERSAO).then((k) => k.put(req, copia)); } return r; })
      .catch(() => caches.match(req).then((c) => c || caches.match('./index.html')))
  );
});
