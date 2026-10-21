{% load static %}/* Service worker do MãeSegura — cache de aplicação e conteúdo validado. */
const CACHE = "maesegura-v1";
const ESSENCIAIS = [
  "/",
  "/assistente/",
  "/offline/",
  "{% static 'css/app.css' %}",
  "{% static 'js/app.js' %}",
  "{% static 'manifest.json' %}",
  "{% static 'icones/icone.svg' %}",
  "/assistente/conhecimento.json"
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ESSENCIAIS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(chaves.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET") return;

  // Conteúdo clínico: rede primeiro, para apanhar validações novas; cache como rede de segurança.
  if (pedido.url.includes("/conhecimento.json")) {
    evento.respondWith(
      fetch(pedido)
        .then((resposta) => {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(pedido, copia));
          return resposta;
        })
        .catch(() => caches.match(pedido))
    );
    return;
  }

  evento.respondWith(
    caches.match(pedido).then((guardada) =>
      guardada || fetch(pedido).catch(() => caches.match("/offline/"))
    )
  );
});
