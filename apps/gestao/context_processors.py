from django.db.models import Q

from apps.assistente.models import Conhecimento

from .perfis import CLINICO, GESTOR, perfis_de


def painel(request):
    """Perfis e contador de pendências, disponíveis em todo o painel."""
    if not request.path.startswith("/gestao/") or not request.user.is_authenticated:
        return {}
    nomes = perfis_de(request.user)
    contexto = {
        "perfil_clinico": CLINICO in nomes,
        "perfil_gestor": GESTOR in nomes,
        "perfil_superuser": "superuser" in nomes,
    }
    if CLINICO in nomes:
        contexto["por_validar_menu"] = Conhecimento.objects.filter(
            Q(validado_em__isnull=True) | Q(validado_por="")
        ).count()
    return contexto
