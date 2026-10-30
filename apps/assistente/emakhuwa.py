"""
Ponte lexical do Emakhuwa para o motor de busca.

Base normativa
--------------
Variante de referência: **Emakhuwa Central (vmw)**, a de Nampula. Ortografia
segundo Ngunga & Faquir (2014), *Padronização da Ortografia de Línguas
Moçambicanas*, CELM/UEM; gramática de Kröger (2009) e vocabulário do SIL.
O léxico está em dados/lexico_vmw.json, cada entrada com a variante e o
documento de onde veio.

O que a normalização apaga, e porquê se aceita
----------------------------------------------
A norma marca a duração vocálica por duplicação, e ela é distintiva: *omala*
(acabar) e *omaala* (calar-se) são palavras diferentes. A aspiração também:
*ephula* (nariz) e *epula* (chuva). A normalização desta casa funde as duas
coisas — colapsa vogais dobradas e reduz `ph th kh` a `p t k`.

É uma perda consciente. Quem escreve aqui é uma mulher grávida num telemóvel,
sem ter aprendido a norma de 2014, e a grafia que lhe sai não é uma escolha.
Entre não encontrar um sinal de perigo e encontrar um conteúdo a mais, a
segunda falha é a que se corrige a olhar para o ecrã. O limiar de duas
palavras impede que uma fusão sozinha decida alguma coisa, e os pares que a
norma distingue e nós fundimos estão fixados em testes.py — onde falham alto
no dia em que algum deles entrar no conteúdo clínico.

Porquê existe
-------------
Até à v0.5.2, uma pergunta escrita em Emakhuwa só encontrava resposta se
calhasse de usar exactamente as palavras-chave que o clínico escreveu. Duas
coisas o impediam.

A primeira é a ortografia. O Emakhuwa escreve-se de maneiras diferentes na
mesma rua: «ohawa» e «ohava», «nikhula» e «nikula», «otthuka» e «otuka». Para
quem escreve num telemóvel, com teclado português, a diferença não é uma
escolha — é o que saiu. Comparar as letras uma a uma transforma variação
normal da língua em pergunta sem resposta.

A segunda é que o acervo clínico está quase todo em português. Uma mulher que
escreve «muru onniwereya» tem a resposta sobre dores de cabeça à frente dela,
validada e assinada, e não lhe chega — porque ninguém escreveu «muru» na lista
de palavras-chave.

Este módulo resolve as duas com o léxico do «Tradutor e Dicionário Emakhuwa»
(acervo v0.2, dados/lexico_vmw.json): normaliza a grafia como o dicionário a
normaliza, e traduz as palavras da PERGUNTA para as glosas portuguesas, que
depois entram na busca normal.

O que este módulo nunca faz
---------------------------
Não escreve, não traduz e não altera uma única resposta. O acervo do dicionário
não tem ainda uma só entrada confirmada por falante nativo; deixá-lo tocar no
texto que uma grávida lê seria pôr palavra por validar na boca de um clínico
que assinou outra coisa. A ponte trabalha de um lado só: ajuda a ENCONTRAR o
que já foi assinado.

E ajuda com desconto. Uma correspondência vinda da ponte vale menos do que uma
correspondência directa (ver PESO_* em busca.py), de modo que uma só palavra
reconhecida nunca chega para devolver conteúdo clínico. Se a ponte se enganar
numa palavra — e vai enganar-se, com um acervo por validar —, o limiar
continua a exigir que algo mais na frase confirme o assunto.
"""
import json
import pathlib
import unicodedata

# A mesma lista do dicionário, pela mesma ordem. A ordem importa: «tth» tem de
# ser reduzido antes de «th», senão «otthuka» passa por «th» e perde-se.
SUBS_NORM = [
    ("tch", "c"), ("tx", "c"), ("ch", "c"), ("sh", "c"), ("x", "c"),
    ("tth", "tt"), ("ph", "p"), ("th", "t"), ("kh", "k"), ("nh", "ny"),
    ("w", "u"), ("y", "i"),
]
# Confusões que atravessam variantes e ouvidos: o~u, e~i, l~r.
SUBS_DIF = [("o", "u"), ("e", "i"), ("l", "r")]
# Prefixos de classe e o «o-» do infinitivo. Cortá-los aproxima «ohawa» de
# «hawa» e deixa a raiz comparável.
PREFIXOS = [
    "oo", "uu", "wa", "we", "wi", "wo", "wu", "o", "u", "w",
    "mu", "mw", "m", "mi", "ni", "n", "ma", "e", "i", "a", "va",
]

CAMINHO_LEXICO = pathlib.Path(__file__).resolve().parent / "dados" / "lexico_vmw.json"


def _sem_acentos(texto):
    decomposto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _colapsar(texto):
    """Vogal longa e vogal breve são a mesma palavra: «maasi» e «masi»."""
    saida = []
    for letra in texto:
        if not saida or saida[-1] != letra:
            saida.append(letra)
    return "".join(saida)


def exacta(texto):
    return _sem_acentos((texto or "").lower().strip())


def normalizada(texto):
    r = exacta(texto).replace("'", "").replace("-", "")
    for a, b in SUBS_NORM:
        r = r.replace(a, b)
    return _colapsar(r)


def difusa(texto):
    r = normalizada(texto)
    for a, b in SUBS_DIF:
        r = r.replace(a, b)
    return _colapsar(r)


def radical(texto):
    """Corta o prefixo mais longo que deixe pelo menos duas letras de raiz."""
    base = normalizada(texto)
    for prefixo in sorted(PREFIXOS, key=len, reverse=True):
        n = normalizada(prefixo)
        if n and base.startswith(n) and len(base) - len(n) >= 2:
            return base[len(n):]
    return base


def _carregar():
    try:
        bruto = json.loads(CAMINHO_LEXICO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Sem léxico o assistente continua a funcionar exactamente como antes.
        # Nunca se deixa cair o motor de busca por causa de um ficheiro de apoio.
        return []
    return bruto.get("entradas", [])


ENTRADAS = _carregar()


def _indexar():
    """
    Três índices, do mais exigente para o menos: grafia normalizada, raiz sem
    prefixo e grafia difusa. Procura-se por esta ordem e pára-se no primeiro,
    para que uma correspondência frouxa nunca passe à frente de uma firme.
    """
    por_norma, por_radical, por_difusa = {}, {}, {}
    for entrada in ENTRADAS:
        lema = entrada.get("lema", "")
        glosa = entrada.get("glosa", "")
        if not lema or not glosa:
            continue
        por_norma.setdefault(normalizada(lema), entrada)
        raiz = radical(lema)
        if len(raiz) >= 3:
            por_radical.setdefault(raiz, entrada)
        difuso = difusa(lema)
        if len(difuso) >= 4:
            por_difusa.setdefault(difuso, entrada)
    return por_norma, por_radical, por_difusa


POR_NORMA, POR_RADICAL, POR_DIFUSA = _indexar()


def procurar_lema(palavra):
    """Devolve a entrada do léxico que corresponde à palavra, ou None."""
    if not palavra or len(palavra) < 3:
        return None
    achado = POR_NORMA.get(normalizada(palavra))
    if achado:
        return achado
    raiz = radical(palavra)
    if len(raiz) >= 3:
        achado = POR_RADICAL.get(raiz)
        if achado:
            return achado
    difuso = difusa(palavra)
    if len(difuso) >= 4:
        return POR_DIFUSA.get(difuso)
    return None


def traduzir_pergunta(palavras):
    """
    Recebe as palavras da pergunta e devolve
    [(palavra, glosa)] para aquelas que o léxico reconhece.

    A glosa vem como o dicionário a escreve («dar à luz, parir; gerar»); quem
    a fichar que a reparta. Devolvê-la inteira permite também mostrá-la a quem
    perguntou — dizer «entendi "muru" como "cabeça"» é a diferença entre ajudar
    e adivinhar em silêncio.
    """
    pontes = []
    vistos = set()
    for palavra in palavras:
        entrada = procurar_lema(palavra)
        if not entrada:
            continue
        chave = entrada["lema"]
        if chave in vistos:
            continue
        vistos.add(chave)
        pontes.append((palavra, entrada["glosa"]))
    return pontes
