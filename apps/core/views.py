from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.assistente.emakhuwa import ENTRADAS as ENTRADAS_LEXICO


@require_GET
def saude(request):
    """Healthcheck usado pelo Docker e pela monitorização externa."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        base_dados = "ok"
    except Exception:  # pragma: no cover - caminho de falha de infra-estrutura
        base_dados = "falha"
    estado = 200 if base_dados == "ok" else 503
    return JsonResponse(
        {
            "estado": "ok" if estado == 200 else "degradado",
            "base_dados": base_dados,
            "validacao_clinica_exigida": settings.EXIGIR_VALIDACAO_CLINICA,
            "llm_activo": settings.LLM_ACTIVO,
            # Declarado aqui de propósito. Quem avaliar o sistema não tem de
            # acreditar na nossa palavra sobre o que o léxico do Emakhuwa faz:
            # vê, num endereço público, que serve para procurar e que não
            # escreve resposta nenhuma.
            "lexico_emakhuwa": {
                "entradas": len(ENTRADAS_LEXICO),
                "usado_para": "procura",
                "escreve_respostas": False,
                "validado_por_falante_nativo": False,
            },
        },
        status=estado,
    )


@require_GET
@cache_control(max_age=0, no_cache=True)
def service_worker(request):
    """Servido na raiz para que o âmbito do service worker cubra todo o site."""
    return render(request, "sw.js", content_type="application/javascript")


@require_GET
def offline(request):
    return render(request, "offline.html")
