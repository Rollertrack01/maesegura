from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.acompanhamento.models import EventoUso, Gestante
from apps.acompanhamento.views import CHAVE_SESSAO_GESTANTE
from apps.core.antirobo import verificar

from .busca import pontes, procurar
from .emakhuwa import ENTRADAS as ENTRADAS_LEXICO
from .models import Conhecimento


def _base_de_conhecimento():
    return list(
        Conhecimento.objects.publicaveis().select_related("topico")
    )


def _gestante(request):
    codigo = request.session.get(CHAVE_SESSAO_GESTANTE)
    if not codigo:
        return None
    return Gestante.objects.filter(codigo=codigo, activa=True).first()


@require_http_methods(["GET", "POST"])
def assistente(request):
    idioma = request.idioma
    gestante = _gestante(request)
    pergunta = ""
    resultados = []
    respondeu = None
    pontes_usadas = ()

    aviso_antirobo = ""
    processar = request.method == "POST"
    if processar:
        veredicto = verificar(request, "assistente")
        if not veredicto.ok:
            if veredicto.silencioso:
                return redirect("assistente:assistente")
            # Recusado: devolvemos o ecrã com a pergunta escrita e um aviso
            # calmo, sem a processar.
            aviso_antirobo = veredicto.mensagem
            pergunta = (request.POST.get("pergunta") or "").strip()[:300]
            processar = False

    if processar:
        pergunta = (request.POST.get("pergunta") or "").strip()[:300]
        conhecimentos = _base_de_conhecimento()
        itens = [(c, c.para_json()) for c in conhecimentos]
        encontrados = procurar(pergunta, [j for _, j in itens], idioma=idioma)
        mapa = {j["id"]: c for c, j in itens}
        resultados = [(mapa[item["id"]], pontos) for item, pontos in encontrados]
        respondeu = bool(resultados)
        # Mostrar como a pergunta foi entendida. Vale sobretudo quando não há
        # resposta: quem escreveu «oyara» fica a saber que a palavra foi lida
        # como «dar à luz» e que o vazio não é da escrita dela.
        pontes_usadas = pontes(pergunta)

        distrito = gestante.distrito if gestante else ""
        if respondeu:
            EventoUso.registar(EventoUso.PERGUNTA, idioma=idioma, distrito=distrito)
            if any(c.gravidade == Conhecimento.URGENTE for c, _ in resultados):
                EventoUso.registar(EventoUso.ALERTA_URGENTE, idioma=idioma, distrito=distrito)
        else:
            EventoUso.registar(EventoUso.PERGUNTA_SEM_RESPOSTA, idioma=idioma, distrito=distrito)

    destaques = [c for c in _base_de_conhecimento() if c.destaque][:6]
    unidade = gestante.unidade_sanitaria if gestante else None
    return render(
        request,
        "assistente/assistente.html",
        {
            "pergunta": pergunta,
            "resultados": resultados,
            "respondeu": respondeu,
            "pontes": pontes_usadas,
            "destaques": destaques,
            "unidade": unidade,
            "aviso_antirobo": aviso_antirobo,
            "carimbo_verificado": bool(aviso_antirobo),
            "URGENTE": Conhecimento.URGENTE,
            "ATENCAO": Conhecimento.ATENCAO,
        },
    )


@require_GET
def conhecimento_json(request):
    """
    Base de conhecimento validada, aberta. É isto que o service worker guarda
    para o assistente funcionar sem rede, e é também um dado público do projecto.
    """
    itens = [c.para_json() for c in _base_de_conhecimento()]
    # O léxico viaja no mesmo ficheiro de propósito: é o único que o service
    # worker guarda, e uma mulher sem rede tem de poder escrever em Emakhuwa
    # tal como escreveria com rede. São cerca de 7 KB — pesados uma vez,
    # guardados no telemóvel, e nunca tocam no texto das respostas.
    lexico = [
        {"lema": e["lema"], "glosa": e["glosa"]}
        for e in ENTRADAS_LEXICO
    ]
    resposta = JsonResponse(
        {"total": len(itens), "itens": itens, "lexico": lexico},
        json_dumps_params={"ensure_ascii": False},
    )
    resposta["Cache-Control"] = "public, max-age=300"
    return resposta
