"""
Painel público de métricas.

O UNICEF Venture Fund exige que a empresa gere dados em tempo real publicamente
acessíveis e mensuráveis. Esta é a implementação desse requisito: números
agregados, sem qualquer dado pessoal, servidos em HTML e em JSON aberto.
"""
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.acompanhamento.models import Contacto, EventoUso, Gestante
from apps.assistente.models import Conhecimento


def _metricas():
    agora = timezone.now()
    eventos = dict(
        EventoUso.objects.values_list("tipo").annotate(total=Count("id")).values_list("tipo", "total")
    )
    perguntas = eventos.get(EventoUso.PERGUNTA, 0)
    sem_resposta = eventos.get(EventoUso.PERGUNTA_SEM_RESPOSTA, 0)
    total_perguntas = perguntas + sem_resposta

    por_idioma = {
        linha["idioma"]: linha["total"]
        for linha in EventoUso.objects.filter(tipo=EventoUso.PERGUNTA)
        .values("idioma")
        .annotate(total=Count("id"))
    }

    marcados = Contacto.objects.count()
    realizados = Contacto.objects.filter(estado=Contacto.REALIZADO).count()

    conhecimento_total = Conhecimento.objects.count()
    conhecimento_validado = Conhecimento.objects.exclude(validado_em=None).exclude(validado_por="").count()
    conhecimento_vmw = (
        Conhecimento.objects.exclude(resposta_vmw="").count()
    )

    return {
        "actualizado_em": agora.isoformat(),
        "gestantes_em_acompanhamento": Gestante.objects.filter(activa=True).count(),
        "perguntas_feitas": total_perguntas,
        "perguntas_com_resposta_validada": perguntas,
        "taxa_resposta_percentagem": round(perguntas / total_perguntas * 100, 1) if total_perguntas else 0.0,
        "encaminhamentos_sinal_de_perigo": eventos.get(EventoUso.ALERTA_URGENTE, 0),
        "consultas_marcadas": marcados,
        "consultas_realizadas": realizados,
        "conteudos_totais": conhecimento_total,
        "conteudos_validados_por_clinico": conhecimento_validado,
        "conteudos_com_emakhuwa": conhecimento_vmw,
        "perguntas_por_idioma": por_idioma,
        "licenca": "MIT",
        "nota": "Dados agregados e anónimos. Nenhum dado pessoal é recolhido ou publicado.",
    }


@require_GET
def painel(request):
    dados = _metricas()
    maximo_idioma = max(dados["perguntas_por_idioma"].values(), default=0) or 1
    barras = [
        {
            "idioma": idioma,
            "total": total,
            "percentagem": round(total / maximo_idioma * 100),
        }
        for idioma, total in sorted(dados["perguntas_por_idioma"].items())
    ]
    return render(request, "painel/painel.html", {"m": dados, "barras": barras})


@require_GET
def metricas_json(request):
    resposta = JsonResponse(_metricas(), json_dumps_params={"ensure_ascii": False})
    resposta["Access-Control-Allow-Origin"] = "*"
    resposta["Cache-Control"] = "public, max-age=60"
    return resposta
