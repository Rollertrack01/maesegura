/*
  Camada offline do assistente.

  O algoritmo de pontuação aqui é o espelho exacto de apps/assistente/busca.py.
  Quem alterar um dos dois tem de alterar o outro — ver nota nesse ficheiro.
*/
(function () {
  "use strict";

  var PALAVRAS_VAZIAS = new Set([
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "em", "no", "na",
    "para", "por", "que", "e", "ou", "com", "sem", "meu", "minha", "me", "eu", "se",
    "muito", "muita", "estou", "este", "tenho", "ao", "aos",
    "ni", "wa", "ya", "mu", "ti", "sa",
    "onde", "quando", "como", "qual", "quais", "quanto", "quanta", "quantos",
    "quantas", "porque", "posso", "devo", "deve", "fazer", "faco",
    "preciso", "quero", "vou", "ser", "sao", "nao", "sim",
    "esta", "estao", "isso", "isto", "mim", "nos", "ja",
    "depois", "antes", "entao", "agora", "aqui"
  ]);
  var PESO_CHAVE = 3;
  var PESO_PERGUNTA = 2;
  var LIMIAR = 4;
  var FRACCAO_DO_MELHOR = 0.6;
  var MINIMO_PALAVRAS_COMUNS = 2;

  function normalizar(texto) {
    if (!texto) return "";
    return texto.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function fichar(texto) {
    var partes = normalizar(texto).split(/[^a-z0-9]+/);
    var conjunto = new Set();
    partes.forEach(function (p) {
      if (p.length > 2 && !PALAVRAS_VAZIAS.has(p)) conjunto.add(p);
    });
    return conjunto;
  }

  function interseccao(a, b) {
    var total = 0;
    a.forEach(function (x) { if (b.has(x)) total += 1; });
    return total;
  }

  function uniao(a, b) {
    var r = new Set(a);
    b.forEach(function (x) { r.add(x); });
    return r;
  }

  function avaliar(pergunta, item, idioma) {
    var entrada = fichar(pergunta);
    if (entrada.size === 0) return { pontos: 0, comuns: 0 };
    var chaves = fichar(item.chaves_pt);
    var perguntas = fichar(item.pergunta_pt);
    if (idioma === "vmw") {
      chaves = uniao(chaves, fichar(item.chaves_vmw));
      perguntas = uniao(perguntas, fichar(item.pergunta_vmw));
    } else {
      chaves = uniao(chaves, fichar(item.chaves_vmw));
    }
    return {
      pontos: interseccao(entrada, chaves) * PESO_CHAVE +
              interseccao(entrada, perguntas) * PESO_PERGUNTA,
      comuns: interseccao(entrada, uniao(chaves, perguntas))
    };
  }

  function procurar(pergunta, itens, idioma, limite) {
    var exigidas = Math.min(MINIMO_PALAVRAS_COMUNS, fichar(pergunta).size) || 1;
    var pontuados = itens
      .map(function (item) {
        var a = avaliar(pergunta, item, idioma);
        return { item: item, pontos: a.pontos, comuns: a.comuns };
      })
      .filter(function (r) { return r.pontos >= LIMIAR && r.comuns >= exigidas; })
      .sort(function (a, b) { return b.pontos - a.pontos || a.item.id - b.item.id; });
    if (pontuados.length === 0) return [];
    var corte = Math.max(LIMIAR, pontuados[0].pontos * FRACCAO_DO_MELHOR);
    return pontuados.filter(function (r) { return r.pontos >= corte; }).slice(0, limite || 3);
  }

  // --- Integração com a página ---------------------------------------------
  var CHAVE_CACHE = "maesegura.conhecimento";
  var idioma = document.documentElement.lang || "pt";

  function guardar(dados) {
    try {
      localStorage.setItem(CHAVE_CACHE, JSON.stringify(dados));
    } catch (e) { /* armazenamento indisponível: seguimos sem cache local */ }
  }

  function ler() {
    try {
      var bruto = localStorage.getItem(CHAVE_CACHE);
      return bruto ? JSON.parse(bruto) : null;
    } catch (e) { return null; }
  }

  function escapar(texto) {
    var div = document.createElement("div");
    div.textContent = texto == null ? "" : texto;
    return div.innerHTML;
  }

  function desenhar(resultados) {
    var alvo = document.getElementById("respostas");
    if (!alvo) return;
    if (resultados.length === 0) {
      alvo.innerHTML = '<div class="resposta resposta-atencao"><p>' +
        escapar(document.body.dataset.semResposta || "") + "</p></div>";
      return;
    }
    alvo.innerHTML = resultados.map(function (r) {
      var c = r.item;
      var classe = c.gravidade === "urgente" ? "resposta-urgente"
                 : c.gravidade === "atencao" ? "resposta-atencao" : "";
      var titulo = (idioma === "vmw" && c.pergunta_vmw) ? c.pergunta_vmw : c.pergunta_pt;
      var corpo = c.resposta_pt;
      var extra = (idioma === "vmw" && c.resposta_vmw) ? "<p>" + escapar(c.resposta_vmw) + "</p>" : "";
      return '<div class="resposta ' + classe + '"><h3>' + escapar(titulo) + "</h3><p>" +
        escapar(corpo) + "</p>" + extra +
        '<p class="meta">' + escapar(c.fonte) + "</p></div>";
    }).join("");
  }

  function responderOffline(pergunta) {
    var cache = ler();
    if (!cache || !cache.itens) return false;
    desenhar(procurar(pergunta, cache.itens, idioma, 3));
    var aviso = document.getElementById("aviso-sem-rede");
    if (aviso) aviso.hidden = false;
    return true;
  }

  // Descarrega a base validada para o telemóvel assim que há rede.
  if (navigator.onLine !== false) {
    fetch("/assistente/conhecimento.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (dados) { if (dados) guardar(dados); })
      .catch(function () { /* sem rede: usamos o que já está guardado */ });
  }

  var formulario = document.getElementById("formulario-pergunta");
  if (formulario) {
    formulario.addEventListener("submit", function (evento) {
      if (navigator.onLine === false) {
        var campo = document.getElementById("pergunta");
        if (campo && responderOffline(campo.value)) evento.preventDefault();
      }
    });
  }

  document.querySelectorAll("[data-sugestao]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.getElementById("pergunta");
      if (!campo) return;
      campo.value = botao.dataset.sugestao;
      campo.focus();
      if (formulario) formulario.requestSubmit();
    });
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
})();
