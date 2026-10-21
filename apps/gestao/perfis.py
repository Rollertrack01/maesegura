"""
Perfis de acesso ao painel de gestão.

Três perfis, porque três pessoas diferentes trabalham neste sistema e não
devem ver o mesmo:

- CLINICO — profissional de saúde. Revê e assina o conteúdo clínico. É o
  único que pode validar: a assinatura que aparece à grávida é a dele.
- GESTOR — coordenação da Energisa. Acompanha indicadores, gere unidades
  sanitárias e consultas. Não pode validar conteúdo clínico, por mais
  administrador que seja, porque não tem competência para o assinar.
- Superuser — equipa técnica. Vê tudo e tem acesso ao Django admin, que fica
  fora do painel, em /sistema/.

A separação entre gerir e validar não é burocracia: é o que torna
defensável dizer ao UNICEF que nenhum conteúdo clínico chega à utilizadora
sem revisão profissional.
"""
from functools import wraps

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

CLINICO = "Clínico"
GESTOR = "Gestor"
PERFIS = (CLINICO, GESTOR)


def perfis_de(utilizador):
    if not utilizador.is_authenticated:
        return set()
    if utilizador.is_superuser:
        return set(PERFIS) | {"superuser"}
    return set(utilizador.groups.values_list("name", flat=True))


def tem_perfil(utilizador, *necessarios):
    return bool(perfis_de(utilizador) & set(necessarios))


def pode_validar_conteudo(utilizador):
    """Só o clínico assina. O gestor, mesmo sendo chefe, não assina."""
    return tem_perfil(utilizador, CLINICO)


def exige_perfil(*necessarios):
    def decorador(vista):
        @wraps(vista)
        def envolvida(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/gestao/entrar/?proximo={request.path}")
            if necessarios and not tem_perfil(request.user, *necessarios):
                raise PermissionDenied(
                    "A sua conta não tem perfil para aceder a esta secção."
                )
            return vista(request, *args, **kwargs)

        return envolvida

    return decorador


def garantir_grupos():
    """Cria os grupos se não existirem. Idempotente."""
    return [Group.objects.get_or_create(name=nome)[0] for nome in PERFIS]
