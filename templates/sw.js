{% load static %}/* Service worker do MãeSegura — cache de aplicação e conteúdo validado. */
/* Subir este número sempre que o CSS ou o JS mudarem: os ficheiros estáticos
   são servidos da cache primeiro, e sem isto quem tem a aplicação instalada
   continuaria a ver a versão antiga. */
const CACHE = "maesegura-v4";
const ESSENCIAIS = [
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

  /*
    Páginas: rede primeiro, cache como rede de segurança.

    Tem de ser assim. Uma página guardada traz consigo o token CSRF e o carimbo
    da protecção anti-robô, e ambos envelhecem: servida de cache ao fim de dias,
    o envio seguinte seria recusado e a mulher não perceberia porquê. Indo à
    rede primeiro, quem tem ligação envia sempre com valores frescos; quem não
    tem recebe a página guardada e, no assistente, a resposta sai do conteúdo
    que o telemóvel já guardou.
  */
  if (pedido.mode === "navigate") {
    evento.respondWith(
      fetch(pedido)
        .then((resposta) => {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(pedido, copia));
          return resposta;
        })
        .catch(() => caches.match(pedido).then((g) => g || caches.match("/offline/")))
    );
    return;
  }

  // Conteúdo clínico: rede primeiro, para apanhar validações novas.
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

  // Ficheiros estáticos: cache primeiro, que é onde ela compensa.
  evento.respondWith(
    caches.match(pedido).then((guardada) =>
      guardada || fetch(pedido).catch(() => caches.match("/offline/"))
    )
  );
});
