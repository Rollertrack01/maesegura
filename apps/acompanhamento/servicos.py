"""Regras de negócio do acompanhamento, isoladas das vistas para serem testáveis."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Contacto, EventoUso, Gestante, versao_consentimento_actual


def gerar_calendario(gestante):
    """
    Cria os contactos pré-natais que ainda fazem sentido para a idade gestacional
    de entrada. Uma mulher que se regista à 30ª semana não recebe a consulta da 12ª.
    """
    hoje = timezone.localdate()
    criados = []
    for indice, semana in enumerate(Contacto.SEMANAS_OMS, start=1):
        if semana < gestante.semana_gestacional_inicial:
            continue
        deslocamento = (semana - gestante.semana_gestacional_inicial) * 7
        data = gestante.data_registo + timedelta(days=deslocamento)
        if data < hoje:
            data = hoje
        criados.append(
            Contacto(
                gestante=gestante,
                numero=indice,
                semana_alvo=semana,
                data_prevista=data,
            )
        )
    Contacto.objects.bulk_create(criados)
    return criados


@transaction.atomic
def registar_gestante(*, semana, distrito="", unidade=None, telefone="", idioma="pt"):
    hoje = timezone.localdate()
    gestante = Gestante.objects.create(
        semana_gestacional_inicial=semana,
        data_registo=hoje,
        data_prevista_parto=Gestante.calcular_dpp(semana, hoje),
        distrito=distrito,
        unidade_sanitaria=unidade,
        telefone=telefone,
        idioma=idioma,
        consentimento_em=timezone.now(),
        consentimento_versao=versao_consentimento_actual(),
    )
    gerar_calendario(gestante)
    EventoUso.registar(EventoUso.REGISTO, idioma=idioma, distrito=distrito)
    return gestante
