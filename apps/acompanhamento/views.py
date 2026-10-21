from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.i18n import CODIGOS, traduzir

from .models import Contacto, EventoUso, Gestante, UnidadeSanitaria
from .servicos import registar_gestante

CHAVE_SESSAO_GESTANTE = "codigo_gestante"


def _unidades():
    return UnidadeSanitaria.objects.filter(confirmado_em__isnull=False)


@require_http_methods(["GET", "POST"])
def registo(request):
    idioma = request.idioma
    erros = {}
    if request.method == "POST":
        semana_bruta = (request.POST.get("semana") or "").strip()
        consentimento = request.POST.get("consentimento") == "sim"
        try:
            semana = int(semana_bruta)
            if not 4 <= semana <= 42:
                raise ValueError
        except ValueError:
            semana = None
            erros["semana"] = traduzir("registo.erro.semana", idioma)
        if not consentimento:
            erros["consentimento"] = traduzir("registo.erro.consentimento", idioma)

        if not erros:
            unidade = None
            unidade_id = request.POST.get("unidade")
            if unidade_id:
                unidade = _unidades().filter(pk=unidade_id).first()
            idioma_escolhido = request.POST.get("idioma")
            if idioma_escolhido not in CODIGOS:
                idioma_escolhido = idioma
            gestante = registar_gestante(
                semana=semana,
                distrito=(request.POST.get("distrito") or "").strip()[:80],
                unidade=unidade,
                telefone=(request.POST.get("telefone") or "").strip()[:30],
                idioma=idioma_escolhido,
            )
            request.session[CHAVE_SESSAO_GESTANTE] = gestante.codigo
            request.session["idioma"] = idioma_escolhido
            return redirect("acompanhamento:inicio")

    return render(
        request,
        "acompanhamento/registo.html",
        {"erros": erros, "unidades": _unidades(), "valores": request.POST},
    )


def _gestante_da_sessao(request):
    codigo = request.session.get(CHAVE_SESSAO_GESTANTE)
    if not codigo:
        return None
    return Gestante.objects.filter(codigo=codigo, activa=True).first()


@require_http_methods(["GET", "POST"])
def entrar(request):
    erro = None
    if request.method == "POST":
        codigo = (request.POST.get("codigo") or "").strip().upper()
        gestante = Gestante.objects.filter(codigo=codigo, activa=True).first()
        if gestante:
            request.session[CHAVE_SESSAO_GESTANTE] = gestante.codigo
            request.session["idioma"] = gestante.idioma
            return redirect("acompanhamento:inicio")
        erro = traduzir("entrar.erro", request.idioma)
    return render(request, "acompanhamento/entrar.html", {"erro": erro})


def inicio(request):
    gestante = _gestante_da_sessao(request)
    if gestante is None:
        return redirect("acompanhamento:registo")

    hoje = timezone.localdate()
    contactos = list(gestante.contactos.all())
    for contacto in contactos:
        contacto.atrasado = contacto.em_atraso(hoje)
    EventoUso.registar(
        EventoUso.CONSULTA_VISTA, idioma=gestante.idioma, distrito=gestante.distrito
    )
    return render(
        request,
        "acompanhamento/inicio.html",
        {
            "gestante": gestante,
            "semana_actual": gestante.semana_actual(hoje),
            "contactos": contactos,
            "proximo": gestante.proximo_contacto(hoje),
        },
    )


def sair(request):
    request.session.pop(CHAVE_SESSAO_GESTANTE, None)
    return redirect("acompanhamento:registo")
