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
from functools import lru_cache

from .emakhuwa import normalizada, traduzir_pergunta

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
# Uma correspondência que passou pela ponte do Emakhuwa (emakhuwa.py) vale
# menos do que uma correspondência directa, e de propósito: o léxico ainda não
# tem uma entrada confirmada por falante nativo. Com estes pesos, duas palavras
# reconhecidas pela ponte chegam ao limiar; uma só nunca chega. Se a ponte se
# enganar, é preciso que a frase a desminta — e basta que nada mais confirme.
PESO_PONTE_CHAVE = 2
PESO_PONTE_PERGUNTA = 1
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
    """
    Fichas comparáveis de um texto, com a grafia já assente.

    Isto mudou na v0.6.0 e é a metade silenciosa da melhoria. Até aqui
    comparavam-se as letras tal como saíram do teclado, e o Emakhuwa não se
    escreve de uma só maneira: «ohawa» e «ohava», «nikhula» e «nikula»,
    «otthuka» e «otuka» são a mesma palavra para quem a diz e eram palavras
    diferentes para o motor. Passando ambos os lados pela normalização do
    dicionário, a variação de grafia deixa de ser um obstáculo — e continua a
    valer peso inteiro, porque não é uma aproximação: é a mesma palavra.

    O português atravessa a mesma função. Perde pouco («chuva» fica «cuva»,
    «barriga» fica «bariga»), e perde dos dois lados ao mesmo tempo, que é o
    que importa para comparar.
    """
    return {normalizada(p) for p in fichar(valor or "")}


@lru_cache(maxsize=256)
def pontes(pergunta):
    """
    Palavras da pergunta que o léxico do dicionário reconhece como Emakhuwa.
    Devolve ((palavra, glosa), …) — a mesma coisa que se mostra a quem perguntou.

    Guardado em cache porque `avaliar` corre uma vez por conteúdo e a pergunta
    é sempre a mesma: sem isto, traduzíamos a frase vinte e três vezes seguidas
    para dar vinte e três vezes o mesmo resultado.
    """
    return tuple(traduzir_pergunta(sorted(fichar(pergunta))))


@lru_cache(maxsize=256)
def _fichas_da_ponte(pergunta):
    """Glosas portuguesas das palavras reconhecidas, em fichas comparáveis."""
    fichas = set()
    for _, glosa in pontes(pergunta):
        fichas |= _conjunto(glosa)
    return frozenset(fichas)


def avaliar(pergunta, item, idioma="pt"):
    """
    `item` é um dicionário com chaves pergunta_pt/vmw e chaves_pt/vmw.
    Devolve (pontos, nº de palavras distintas em comum).
    """
    entrada = _conjunto(pergunta)
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
    comuns = entrada & (chaves | perguntas)

    # A ponte entra depois e por fora: traduz a pergunta, nunca a resposta.
    ponte = _fichas_da_ponte(pergunta) - entrada
    if ponte:
        pontos += len(ponte & chaves) * PESO_PONTE_CHAVE
        pontos += len(ponte & perguntas) * PESO_PONTE_PERGUNTA
        comuns |= ponte & (chaves | perguntas)

    return pontos, len(comuns)


def pontuar(pergunta, item, idioma="pt"):
    return avaliar(pergunta, item, idioma)[0]


def procurar(pergunta, itens, idioma="pt", limite=3):
    """Devolve [(item, pontos)] ordenado, só acima do limiar."""
    # Não se pode exigir duas palavras em comum a quem escreveu só uma.
    exigidas = min(MINIMO_PALAVRAS_COMUNS, len(_conjunto(pergunta))) or 1
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
