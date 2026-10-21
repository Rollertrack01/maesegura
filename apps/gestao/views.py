from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.acompanhamento.models import Contacto, EventoUso, Gestante, UnidadeSanitaria
from apps.assistente.models import Conhecimento

from .forms import ConteudoForm, UnidadeForm, UtilizadorForm
from .perfis import CLINICO, GESTOR, exige_perfil, perfis_de, pode_validar_conteudo


# --- Autenticação ------------------------------------------------------------

def entrar(request):
    if request.user.is_authenticated:
        return redirect("gestao:painel")
    erro = None
    if request.method == "POST":
        utilizador = authenticate(
            request,
            username=(request.POST.get("username") or "").strip(),
            password=request.POST.get("password") or "",
        )
        if utilizador is None:
            erro = "Nome de utilizador ou senha incorrectos."
        elif not (utilizador.is_superuser or perfis_de(utilizador)):
            erro = "A sua conta ainda não tem perfil atribuído. Fale com a coordenação."
        else:
            login(request, utilizador)
            return redirect(request.GET.get("proximo") or "gestao:painel")
    return render(request, "gestao/entrar.html", {"erro": erro})


def sair(request):
    logout(request)
    return redirect("gestao:entrar")


# --- Painel ------------------------------------------------------------------

@exige_perfil()
def painel(request):
    hoje = timezone.localdate()
    conteudos = Conhecimento.objects.aggregate(
        total=Count("id"),
        validados=Count("id", filter=Q(validado_em__isnull=False) & ~Q(validado_por="")),
        com_emakhuwa=Count("id", filter=~Q(resposta_vmw="")),
        traducoes_validadas=Count("id", filter=Q(traducao_vmw_validada=True)),
    )
    por_validar = conteudos["total"] - conteudos["validados"]
    traducoes_por_rever = conteudos["com_emakhuwa"] - conteudos["traducoes_validadas"]
    consultas_em_atraso = Contacto.objects.filter(
        estado=Contacto.AGENDADO, data_prevista__lt=hoje
    ).count()
    unidades_por_confirmar = UnidadeSanitaria.objects.filter(confirmado_em__isnull=True).count()
    perguntas_sem_resposta = EventoUso.objects.filter(
        tipo=EventoUso.PERGUNTA_SEM_RESPOSTA
    ).count()

    # «Requer a sua atenção»: só o que esta pessoa pode de facto resolver.
    pendencias = []
    meus = perfis_de(request.user)
    if CLINICO in meus:
        if por_validar:
            pendencias.append({
                "texto": f"{por_validar} conteúdo(s) à espera da sua validação clínica",
                "url": "/gestao/conteudos/?estado=por-validar",
                "grave": True,
            })
        if traducoes_por_rever:
            pendencias.append({
                "texto": f"{traducoes_por_rever} tradução(ões) para Emakhuwa por rever",
                "url": "/gestao/conteudos/?estado=traducao",
                "grave": False,
            })
    if GESTOR in meus:
        if consultas_em_atraso:
            pendencias.append({
                "texto": f"{consultas_em_atraso} consulta(s) em atraso",
                "url": "/gestao/consultas/?estado=atraso",
                "grave": True,
            })
        if unidades_por_confirmar:
            pendencias.append({
                "texto": f"{unidades_por_confirmar} unidade(s) sanitária(s) com contacto por confirmar",
                "url": "/gestao/unidades/",
                "grave": False,
            })
        if perguntas_sem_resposta:
            pendencias.append({
                "texto": f"{perguntas_sem_resposta} pergunta(s) ficaram sem resposta validada",
                "url": "/gestao/conteudos/",
                "grave": False,
            })

    # Guia de arranque: desaparece sozinho quando o piloto já anda.
    passos = {
        "unidades": UnidadeSanitaria.objects.filter(confirmado_em__isnull=False).exists(),
        "validacao": conteudos["validados"] > 0,
        "traducoes": conteudos["traducoes_validadas"] > 0,
        "gestantes": Gestante.objects.exists(),
    }

    return render(request, "gestao/painel.html", {
        "conteudos": conteudos,
        "por_validar": por_validar,
        "pendencias": pendencias,
        "passos": passos,
        "mostrar_primeiros_passos": not all(passos.values()),
        "gestantes": Gestante.objects.filter(activa=True).count(),
        "consultas_marcadas": Contacto.objects.count(),
        "consultas_realizadas": Contacto.objects.filter(estado=Contacto.REALIZADO).count(),
        "consultas_em_atraso": consultas_em_atraso,
        "perguntas": EventoUso.objects.filter(tipo=EventoUso.PERGUNTA).count(),
        "encaminhamentos": EventoUso.objects.filter(tipo=EventoUso.ALERTA_URGENTE).count(),
    })


# --- Conteúdo clínico --------------------------------------------------------

@exige_perfil()
def conteudos(request):
    itens = Conhecimento.objects.select_related("topico")
    estado = request.GET.get("estado", "")
    if estado == "por-validar":
        itens = itens.filter(Q(validado_em__isnull=True) | Q(validado_por=""))
    elif estado == "validados":
        itens = itens.filter(validado_em__isnull=False).exclude(validado_por="")
    elif estado == "traducao":
        itens = itens.exclude(resposta_vmw="").filter(traducao_vmw_validada=False)
    procura = (request.GET.get("q") or "").strip()
    if procura:
        itens = itens.filter(
            Q(pergunta_pt__icontains=procura) | Q(palavras_chave_pt__icontains=procura)
        )
    return render(request, "gestao/conteudos.html", {
        "itens": itens,
        "estado": estado,
        "procura": procura,
        "pode_validar": pode_validar_conteudo(request.user),
    })


@exige_perfil()
def conteudo_editar(request, pk):
    item = get_object_or_404(Conhecimento, pk=pk)
    pode_editar = pode_validar_conteudo(request.user)
    if request.method == "POST":
        if not pode_editar:
            messages.error(request, "Só um perfil clínico pode alterar conteúdo clínico.")
            return redirect("gestao:conteudo-editar", pk=pk)
        formulario = ConteudoForm(request.POST, instance=item)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Conteúdo guardado.")
            return redirect("gestao:conteudos")
    else:
        formulario = ConteudoForm(instance=item)
    return render(request, "gestao/conteudo_editar.html", {
        "formulario": formulario, "item": item, "pode_editar": pode_editar,
    })


@require_POST
@exige_perfil(CLINICO)
def conteudo_validar(request, pk):
    item = get_object_or_404(Conhecimento, pk=pk)
    nome = request.user.get_full_name().strip() or request.user.get_username()
    item.validado_por = nome
    item.validado_em = timezone.now()
    item.save(update_fields=["validado_por", "validado_em"])
    messages.success(
        request,
        f"Validado. A partir de agora esta resposta é servida às utilizadoras, "
        f"assinada por {nome}.",
    )
    return redirect(request.POST.get("proximo") or "gestao:conteudos")


@require_POST
@exige_perfil(CLINICO)
def conteudo_retirar(request, pk):
    item = get_object_or_404(Conhecimento, pk=pk)
    item.validado_por = ""
    item.validado_em = None
    item.save(update_fields=["validado_por", "validado_em"])
    messages.warning(
        request, "Validação retirada. Esta resposta deixou de ser servida às utilizadoras."
    )
    return redirect(request.POST.get("proximo") or "gestao:conteudos")


# --- Acompanhamento ----------------------------------------------------------

@exige_perfil(GESTOR)
def consultas(request):
    hoje = timezone.localdate()
    itens = Contacto.objects.select_related("gestante", "gestante__unidade_sanitaria")
    estado = request.GET.get("estado", "")
    if estado == "atraso":
        itens = itens.filter(estado=Contacto.AGENDADO, data_prevista__lt=hoje)
    elif estado == "proximas":
        itens = itens.filter(estado=Contacto.AGENDADO, data_prevista__gte=hoje)
    elif estado == "realizadas":
        itens = itens.filter(estado=Contacto.REALIZADO)
    return render(request, "gestao/consultas.html", {
        "itens": itens.order_by("data_prevista")[:300], "estado": estado, "hoje": hoje,
    })


@require_POST
@exige_perfil(GESTOR)
def consulta_marcar(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    novo = request.POST.get("estado")
    if novo in {Contacto.REALIZADO, Contacto.FALHADO, Contacto.AGENDADO}:
        contacto.estado = novo
        contacto.registado_em = timezone.now() if novo != Contacto.AGENDADO else None
        contacto.save(update_fields=["estado", "registado_em"])
        messages.success(request, f"Consulta {contacto.numero} de {contacto.gestante.codigo} actualizada.")
    return redirect(request.POST.get("proximo") or "gestao:consultas")


@exige_perfil(GESTOR)
def gestantes(request):
    itens = Gestante.objects.filter(activa=True).select_related("unidade_sanitaria")
    distrito = (request.GET.get("distrito") or "").strip()
    if distrito:
        itens = itens.filter(distrito__icontains=distrito)
    hoje = timezone.localdate()
    lista = []
    for g in itens.order_by("-data_registo")[:300]:
        lista.append({
            "obj": g,
            "semana": g.semana_actual(hoje),
            "proximo": g.proximo_contacto(hoje),
        })
    return render(request, "gestao/gestantes.html", {"lista": lista, "distrito": distrito})


# --- Unidades sanitárias -----------------------------------------------------

@exige_perfil(GESTOR)
def unidades(request):
    return render(request, "gestao/unidades.html", {
        "itens": UnidadeSanitaria.objects.all(),
    })


@exige_perfil(GESTOR)
def unidade_editar(request, pk=None):
    item = get_object_or_404(UnidadeSanitaria, pk=pk) if pk else None
    if request.method == "POST":
        formulario = UnidadeForm(request.POST, instance=item)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Unidade sanitária guardada.")
            return redirect("gestao:unidades")
    else:
        formulario = UnidadeForm(instance=item)
    return render(request, "gestao/unidade_editar.html", {"formulario": formulario, "item": item})


# --- Equipa ------------------------------------------------------------------

@exige_perfil("superuser")
def equipa(request):
    if request.method == "POST":
        formulario = UtilizadorForm(request.POST)
        if formulario.is_valid():
            utilizador = formulario.save()
            messages.success(
                request,
                f"Conta criada para {utilizador.get_full_name() or utilizador.username}.",
            )
            return redirect("gestao:equipa")
    else:
        formulario = UtilizadorForm()
    pessoas = User.objects.prefetch_related("groups").order_by("username")
    return render(request, "gestao/equipa.html", {"formulario": formulario, "pessoas": pessoas})


# --- Exportação --------------------------------------------------------------

@exige_perfil(GESTOR)
def exportar_metricas(request):
    """CSV dos indicadores agregados, para relatórios e para a candidatura."""
    import csv

    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = (
        f'attachment; filename="maesegura-indicadores-{timezone.localdate()}.csv"'
    )
    escritor = csv.writer(resposta)
    escritor.writerow(["indicador", "valor"])
    escritor.writerow(["gestantes_em_acompanhamento", Gestante.objects.filter(activa=True).count()])
    escritor.writerow(["consultas_marcadas", Contacto.objects.count()])
    escritor.writerow(["consultas_realizadas", Contacto.objects.filter(estado=Contacto.REALIZADO).count()])
    escritor.writerow(["perguntas_respondidas", EventoUso.objects.filter(tipo=EventoUso.PERGUNTA).count()])
    escritor.writerow(["perguntas_sem_resposta", EventoUso.objects.filter(tipo=EventoUso.PERGUNTA_SEM_RESPOSTA).count()])
    escritor.writerow(["encaminhamentos_sinal_de_perigo", EventoUso.objects.filter(tipo=EventoUso.ALERTA_URGENTE).count()])
    escritor.writerow(["conteudos_totais", Conhecimento.objects.count()])
    escritor.writerow([
        "conteudos_validados",
        Conhecimento.objects.exclude(validado_em=None).exclude(validado_por="").count(),
    ])
    return resposta
