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
  // Espelho de PESO_PONTE_* em busca.py: a ponte do Emakhuwa ajuda a
  // encontrar, nunca decide sozinha.
  var PESO_PONTE_CHAVE = 2;
  var PESO_PONTE_PERGUNTA = 1;
  var LIMIAR = 4;
  var FRACCAO_DO_MELHOR = 0.6;
  var MINIMO_PALAVRAS_COMUNS = 2;

  function normalizar(texto) {
    if (!texto) return "";
    return texto.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  // --- Ponte lexical do Emakhuwa -------------------------------------------
  // Espelho de apps/assistente/emakhuwa.py. A ordem de SUBS_NORM é a do
  // dicionário e tem de ser respeitada: «tth» antes de «th».
  var SUBS_NORM = [["tch","c"],["tx","c"],["ch","c"],["sh","c"],["x","c"],["tth","tt"],
                   ["ph","p"],["th","t"],["kh","k"],["nh","ny"],["w","u"],["y","i"]];
  var SUBS_DIF = [["o","u"],["e","i"],["l","r"]];
  var PREFIXOS = ["oo","uu","wa","we","wi","wo","wu","o","u","w",
                  "mu","mw","m","mi","ni","n","ma","e","i","a","va"];

  function colapsar(texto) { return texto.replace(/(.)\1+/g, "$1"); }

  function vmwExacta(texto) {
    return (texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  }

  function vmwNormalizada(texto) {
    var r = vmwExacta(texto).replace(/['-]/g, "");
    SUBS_NORM.forEach(function (par) { r = r.split(par[0]).join(par[1]); });
    return colapsar(r);
  }

  function vmwDifusa(texto) {
    var r = vmwNormalizada(texto);
    SUBS_DIF.forEach(function (par) { r = r.split(par[0]).join(par[1]); });
    return colapsar(r);
  }

  function vmwRadical(texto) {
    var base = vmwNormalizada(texto);
    var ordenados = PREFIXOS.slice().sort(function (a, b) { return b.length - a.length; });
    for (var i = 0; i < ordenados.length; i += 1) {
      var n = vmwNormalizada(ordenados[i]);
      if (n && base.indexOf(n) === 0 && base.length - n.length >= 2) return base.slice(n.length);
    }
    return base;
  }

  var indiceVmw = null;

  function construirIndice(lexico) {
    var idx = { norma: {}, radical: {}, difusa: {} };
    (lexico || []).forEach(function (e) {
      if (!e.lema || !e.glosa) return;
      var n = vmwNormalizada(e.lema);
      if (n && !(n in idx.norma)) idx.norma[n] = e;
      var r = vmwRadical(e.lema);
      if (r.length >= 3 && !(r in idx.radical)) idx.radical[r] = e;
      var d = vmwDifusa(e.lema);
      if (d.length >= 4 && !(d in idx.difusa)) idx.difusa[d] = e;
    });
    return idx;
  }

  function procurarLema(palavra) {
    if (!indiceVmw || !palavra || palavra.length < 3) return null;
    var achado = indiceVmw.norma[vmwNormalizada(palavra)];
    if (achado) return achado;
    var r = vmwRadical(palavra);
    if (r.length >= 3 && indiceVmw.radical[r]) return indiceVmw.radical[r];
    var d = vmwDifusa(palavra);
    if (d.length >= 4 && indiceVmw.difusa[d]) return indiceVmw.difusa[d];
    return null;
  }

  function pontes(pergunta) {
    var achadas = [];
    var vistos = {};
    Array.from(fichar(pergunta)).sort().forEach(function (palavra) {
      var e = procurarLema(palavra);
      if (!e || vistos[e.lema]) return;
      vistos[e.lema] = true;
      achadas.push({ palavra: palavra, glosa: e.glosa });
    });
    return achadas;
  }

  function fichasDaPonte(pergunta) {
    var fichas = new Set();
    pontes(pergunta).forEach(function (p) {
      conjunto(p.glosa).forEach(function (f) { fichas.add(f); });
    });
    return fichas;
  }

  function fichar(texto) {
    var partes = normalizar(texto).split(/[^a-z0-9]+/);
    var conjunto = new Set();
    partes.forEach(function (p) {
      if (p.length > 2 && !PALAVRAS_VAZIAS.has(p)) conjunto.add(p);
    });
    return conjunto;
  }

  // Espelho de _conjunto() em busca.py: a grafia assenta antes de comparar.
  function conjunto(texto) {
    var r = new Set();
    fichar(texto).forEach(function (p) { r.add(vmwNormalizada(p)); });
    return r;
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
    var entrada = conjunto(pergunta);
    if (entrada.size === 0) return { pontos: 0, comuns: 0 };
    var chaves = conjunto(item.chaves_pt);
    var perguntas = conjunto(item.pergunta_pt);
    if (idioma === "vmw") {
      chaves = uniao(chaves, conjunto(item.chaves_vmw));
      perguntas = uniao(perguntas, conjunto(item.pergunta_vmw));
    } else {
      chaves = uniao(chaves, conjunto(item.chaves_vmw));
    }
    var pontos = interseccao(entrada, chaves) * PESO_CHAVE +
                 interseccao(entrada, perguntas) * PESO_PERGUNTA;
    var comuns = new Set();
    var ambos = uniao(chaves, perguntas);
    entrada.forEach(function (x) { if (ambos.has(x)) comuns.add(x); });

    // A ponte entra depois e por fora, como no servidor.
    var ponte = new Set();
    fichasDaPonte(pergunta).forEach(function (f) { if (!entrada.has(f)) ponte.add(f); });
    if (ponte.size) {
      pontos += interseccao(ponte, chaves) * PESO_PONTE_CHAVE;
      pontos += interseccao(ponte, perguntas) * PESO_PONTE_PERGUNTA;
      ponte.forEach(function (x) { if (ambos.has(x)) comuns.add(x); });
    }
    return { pontos: pontos, comuns: comuns.size };
  }

  function procurar(pergunta, itens, idioma, limite) {
    var exigidas = Math.min(MINIMO_PALAVRAS_COMUNS, conjunto(pergunta).size) || 1;
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

  function linhaDaPonte(pergunta) {
    var achadas = pontes(pergunta);
    if (!achadas.length) return "";
    var rotulo = document.body.dataset.rotuloPonte || "Emakhuwa → português";
    return '<p class="meta ponte-lexical">' + escapar(rotulo) + ": " +
      achadas.map(function (p) {
        return "«" + escapar(p.palavra) + "» = " + escapar(p.glosa);
      }).join(" · ") + "</p>";
  }

  function desenhar(resultados, pergunta) {
    var alvo = document.getElementById("respostas");
    if (!alvo) return;
    var ponte = linhaDaPonte(pergunta);
    if (resultados.length === 0) {
      alvo.innerHTML = ponte + '<div class="resposta resposta-atencao"><p>' +
        escapar(document.body.dataset.semResposta || "") + "</p></div>";
      return;
    }
    alvo.innerHTML = ponte + resultados.map(function (r) {
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
    if (!indiceVmw) indiceVmw = construirIndice(cache.lexico);
    desenhar(procurar(pergunta, cache.itens, idioma, 3), pergunta);
    var aviso = document.getElementById("aviso-sem-rede");
    if (aviso) aviso.hidden = false;
    return true;
  }

  // Descarrega a base validada para o telemóvel assim que há rede.
  if (navigator.onLine !== false) {
    fetch("/assistente/conhecimento.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (dados) {
        if (!dados) return;
        guardar(dados);
        indiceVmw = construirIndice(dados.lexico);
      })
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
