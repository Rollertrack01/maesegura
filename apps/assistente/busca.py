"""
Motor de recuperação do assistente.

Porquê recuperação e não geração: o UNICEF exige código aberto de ponta a ponta
e segurança desde a concepção. Um modelo generativo externo quebraria as duas
coisas — introduzia um backend proprietário na cadeia e abria a porta a respostas
inventadas sobre gravidez. Aqui o assistente escolhe entre respostas que um
profissional de saúde escreveu e assinou, ou admite que não sabe.

O algoritmo é propositadamente simples e determinístico, em Python puro, para que
o mesmo cálculo possa correr no service worker (static/js/app.js) quando não há
rede. Qualquer alteração aqui tem de ser espelhada lá.
"""
import re
import unicodedata

PALAVRAS_VAZIAS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "em", "no", "na",
    "para", "por", "que", "e", "ou", "com", "sem", "meu", "minha", "me", "eu", "se",
    "muito", "muita", "estou", "este", "tenho", "ao", "aos",
    "ni", "wa", "ya", "o", "mu", "ti", "sa",
    # interrogativas e auxiliares: estruturam a frase, não dizem o assunto
    "onde", "quando", "como", "qual", "quais", "quanto", "quanta", "quantos",
    "quantas", "porque", "porquê", "posso", "devo", "deve", "fazer", "faco",
    "faço", "preciso", "quero", "vou", "ser", "sao", "são", "nao", "não", "sim",
    "esta", "está", "estao", "isso", "isto", "mim", "nos", "nós", "ja", "já",
    "depois", "antes", "entao", "então", "agora", "aqui",
}
PESO_PALAVRA_CHAVE = 3
PESO_PERGUNTA = 2
# Uma só palavra em comum (um "onde", um "perder") nunca chega para devolver
# conteúdo clínico: exigimos duas correspondências, ou uma forte reforçada.
LIMIAR = 4
# Uma palavra em comum nunca basta, por mais alto que pontue: "o bebé" sozinho
# não distingue "onde ter o bebé" de "o bebé não mexe".
MINIMO_PALAVRAS_COMUNS = 2
# Só mostramos resultados próximos do melhor. Sem isto, uma palavra comum
# ("perder") arrasta conteúdos sem relação, e três sinais de perigo
# simultâneos no ecrã são ruído perigoso para quem procura uma resposta.
FRACCAO_DO_MELHOR = 0.6


def normalizar(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def fichar(texto):
    """Divide em palavras úteis, sem acentos e sem palavras vazias."""
    bruto = re.split(r"[^a-z0-9]+", normalizar(texto))
    return {p for p in bruto if len(p) > 2 and p not in PALAVRAS_VAZIAS}


def _conjunto(valor):
    return fichar(valor or "")


def avaliar(pergunta, item, idioma="pt"):
    """
    `item` é um dicionário com chaves pergunta_pt/vmw e chaves_pt/vmw.
    Devolve (pontos, nº de palavras distintas em comum).
    """
    entrada = fichar(pergunta)
    if not entrada:
        return 0, 0

    chaves = _conjunto(item.get("chaves_pt"))
    perguntas = _conjunto(item.get("pergunta_pt"))
    if idioma == "vmw":
        chaves |= _conjunto(item.get("chaves_vmw"))
        perguntas |= _conjunto(item.get("pergunta_vmw"))
    else:
        # uma mulher pode escrever em Emakhuwa com a interface em português
        chaves |= _conjunto(item.get("chaves_vmw"))

    pontos = len(entrada & chaves) * PESO_PALAVRA_CHAVE
    pontos += len(entrada & perguntas) * PESO_PERGUNTA
    return pontos, len(entrada & (chaves | perguntas))


def pontuar(pergunta, item, idioma="pt"):
    return avaliar(pergunta, item, idioma)[0]


def procurar(pergunta, itens, idioma="pt", limite=3):
    """Devolve [(item, pontos)] ordenado, só acima do limiar."""
    # Não se pode exigir duas palavras em comum a quem escreveu só uma.
    exigidas = min(MINIMO_PALAVRAS_COMUNS, len(fichar(pergunta))) or 1
    pontuados = []
    for item in itens:
        pontos, comuns = avaliar(pergunta, item, idioma)
        if pontos >= LIMIAR and comuns >= exigidas:
            pontuados.append((item, pontos))
    if not pontuados:
        return []
    pontuados.sort(key=lambda par: (-par[1], par[0].get("id", 0)))
    melhor = pontuados[0][1]
    corte = max(LIMIAR, melhor * FRACCAO_DO_MELHOR)
    return [par for par in pontuados if par[1] >= corte][:limite]
