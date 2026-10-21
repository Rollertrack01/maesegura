import secrets
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.i18n import IDIOMAS, IDIOMA_POR_DEFEITO

ALFABETO_CODIGO = "ACDEFGHJKLMNPQRTUVWXY349"  # sem caracteres confundíveis (0/O, 1/I, S/5)


def gerar_codigo(tamanho=6):
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(tamanho))


class UnidadeSanitaria(models.Model):
    nome = models.CharField(max_length=120)
    distrito = models.CharField(max_length=80)
    telefone = models.CharField(max_length=30, blank=True)
    tipo = models.CharField(max_length=40, blank=True, help_text="Centro de saúde, hospital rural, etc.")
    confirmado_em = models.DateField(
        null=True, blank=True,
        help_text="Data em que o contacto foi confirmado com a unidade. Sem isto não é mostrada.",
    )

    class Meta:
        verbose_name = "unidade sanitária"
        verbose_name_plural = "unidades sanitárias"
        ordering = ["distrito", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.distrito})"

    @property
    def confirmada(self):
        return self.confirmado_em is not None


class Gestante(models.Model):
    """
    Registo mínimo por desenho: não existe campo para o nome.
    A identificação é um código curto que a utilizadora guarda.
    """

    codigo = models.CharField(max_length=12, unique=True, default=gerar_codigo, editable=False)
    semana_gestacional_inicial = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(4), MaxValueValidator(42)]
    )
    data_registo = models.DateField(default=timezone.localdate)
    data_prevista_parto = models.DateField()
    distrito = models.CharField(max_length=80, blank=True)
    unidade_sanitaria = models.ForeignKey(
        UnidadeSanitaria, null=True, blank=True, on_delete=models.SET_NULL, related_name="gestantes"
    )
    telefone = models.CharField(max_length=30, blank=True)
    idioma = models.CharField(max_length=8, choices=IDIOMAS, default=IDIOMA_POR_DEFEITO)
    consentimento_em = models.DateTimeField()
    consentimento_versao = models.CharField(max_length=20)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "gestante"
        verbose_name_plural = "gestantes"
        ordering = ["-data_registo"]

    def __str__(self):
        return f"Gestante {self.codigo}"

    @staticmethod
    def calcular_dpp(semana, data_registo):
        """Data prevista do parto: 40 semanas completas a partir da idade gestacional."""
        return data_registo + timedelta(days=(40 - semana) * 7)

    def semana_actual(self, hoje=None):
        hoje = hoje or timezone.localdate()
        decorridas = (hoje - self.data_registo).days // 7
        return min(self.semana_gestacional_inicial + decorridas, 42)

    def proximo_contacto(self, hoje=None):
        hoje = hoje or timezone.localdate()
        return (
            self.contactos.filter(estado=Contacto.AGENDADO, data_prevista__gte=hoje)
            .order_by("data_prevista")
            .first()
        )


class Contacto(models.Model):
    """
    Consulta pré-natal. O calendário segue o modelo de 8 contactos da OMS
    (recomendações de cuidados pré-natais, 2016): 12, 20, 26, 30, 34, 36, 38 e 40 semanas.
    Carece de validação do parceiro clínico face às normas do MISAU.
    """

    AGENDADO = "agendado"
    REALIZADO = "realizado"
    FALHADO = "falhado"
    ESTADOS = [
        (AGENDADO, "Marcada"),
        (REALIZADO, "Realizada"),
        (FALHADO, "Não realizada"),
    ]

    SEMANAS_OMS = (12, 20, 26, 30, 34, 36, 38, 40)

    gestante = models.ForeignKey(Gestante, on_delete=models.CASCADE, related_name="contactos")
    numero = models.PositiveSmallIntegerField()
    semana_alvo = models.PositiveSmallIntegerField()
    data_prevista = models.DateField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default=AGENDADO)
    registado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "consulta pré-natal"
        verbose_name_plural = "consultas pré-natais"
        ordering = ["gestante", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["gestante", "numero"], name="contacto_unico_por_gestante")
        ]

    def __str__(self):
        return f"Contacto {self.numero} ({self.semana_alvo}ª semana) — {self.gestante.codigo}"

    def em_atraso(self, hoje=None):
        hoje = hoje or timezone.localdate()
        return self.estado == self.AGENDADO and self.data_prevista < hoje


class EventoUso(models.Model):
    """
    Telemetria anónima que alimenta o painel público.
    Não guarda texto livre da utilizadora nem qualquer identificador directo.
    """

    REGISTO = "registo"
    PERGUNTA = "pergunta"
    PERGUNTA_SEM_RESPOSTA = "pergunta_sem_resposta"
    ALERTA_URGENTE = "alerta_urgente"
    CONSULTA_VISTA = "consulta_vista"
    TIPOS = [
        (REGISTO, "Registo de gestante"),
        (PERGUNTA, "Pergunta respondida"),
        (PERGUNTA_SEM_RESPOSTA, "Pergunta sem resposta validada"),
        (ALERTA_URGENTE, "Encaminhamento por sinal de perigo"),
        (CONSULTA_VISTA, "Consulta consultada"),
    ]

    tipo = models.CharField(max_length=32, choices=TIPOS)
    idioma = models.CharField(max_length=8, default=IDIOMA_POR_DEFEITO)
    distrito = models.CharField(max_length=80, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "evento de uso"
        verbose_name_plural = "eventos de uso"
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["tipo", "criado_em"])]

    @classmethod
    def registar(cls, tipo, idioma=IDIOMA_POR_DEFEITO, distrito=""):
        return cls.objects.create(tipo=tipo, idioma=idioma, distrito=distrito or "")


def versao_consentimento_actual():
    return settings.VERSAO_CONSENTIMENTO
