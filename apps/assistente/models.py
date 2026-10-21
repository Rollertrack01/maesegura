from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Topico(models.Model):
    codigo = models.SlugField(max_length=40, unique=True)
    nome_pt = models.CharField(max_length=80)
    nome_vmw = models.CharField(max_length=80, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "tópico"
        verbose_name_plural = "tópicos"
        ordering = ["ordem", "nome_pt"]

    def __str__(self):
        return self.nome_pt

    def nome(self, idioma="pt"):
        return (self.nome_vmw or self.nome_pt) if idioma == "vmw" else self.nome_pt


class ConhecimentoQuerySet(models.QuerySet):
    def publicaveis(self):
        """
        O que a aplicação pode servir. Com EXIGIR_VALIDACAO_CLINICA activo
        (defeito), só entra conteúdo com validação humana registada.
        """
        if settings.EXIGIR_VALIDACAO_CLINICA:
            return self.filter(validado_em__isnull=False).exclude(validado_por="")
        return self.all()


class Conhecimento(models.Model):
    """
    Uma unidade de conteúdo clínico revisto. O assistente nunca gera texto:
    recupera e devolve exactamente o que um profissional de saúde validou.
    """

    INFORMATIVO = "informativo"
    ATENCAO = "atencao"
    URGENTE = "urgente"
    GRAVIDADES = [
        (INFORMATIVO, "Informativo"),
        (ATENCAO, "Falar com agente de saúde"),
        (URGENTE, "Sinal de perigo — encaminhar já"),
    ]

    topico = models.ForeignKey(Topico, on_delete=models.PROTECT, related_name="conhecimentos")
    pergunta_pt = models.CharField(max_length=240)
    pergunta_vmw = models.CharField(max_length=240, blank=True)
    resposta_pt = models.TextField()
    resposta_vmw = models.TextField(blank=True)
    palavras_chave_pt = models.TextField(
        blank=True, help_text="Separadas por vírgula. Como a mulher escreveria, não termos técnicos."
    )
    palavras_chave_vmw = models.TextField(blank=True, help_text="Separadas por vírgula.")
    gravidade = models.CharField(max_length=16, choices=GRAVIDADES, default=INFORMATIVO)
    semana_minima = models.PositiveSmallIntegerField(null=True, blank=True)
    semana_maxima = models.PositiveSmallIntegerField(null=True, blank=True)
    fonte = models.CharField(
        max_length=240, help_text="Norma ou documento de origem. Ex.: OMS, Recomendações ANC 2016."
    )
    validado_por = models.CharField(
        max_length=160, blank=True, help_text="Nome e credencial do profissional que reviu."
    )
    validado_em = models.DateTimeField(null=True, blank=True)
    traducao_vmw_validada = models.BooleanField(
        default=False,
        help_text="A tradução para Emakhuwa foi revista por falante nativo com formação em saúde.",
    )
    destaque = models.BooleanField(default=False, help_text="Mostrar na lista de perguntas frequentes.")
    actualizado_em = models.DateTimeField(auto_now=True)

    objects = ConhecimentoQuerySet.as_manager()

    class Meta:
        verbose_name = "conteúdo clínico"
        verbose_name_plural = "conteúdos clínicos"
        ordering = ["topico__ordem", "pergunta_pt"]

    def __str__(self):
        return self.pergunta_pt

    def clean(self):
        if self.validado_em and not self.validado_por:
            raise ValidationError(
                {"validado_por": "Indique quem validou. Não se publica conteúdo clínico anónimo."}
            )
        if self.validado_por and not self.validado_em:
            raise ValidationError({"validado_em": "Indique a data da validação."})

    @property
    def validado(self):
        return bool(self.validado_em and self.validado_por)

    def pergunta(self, idioma="pt"):
        return (self.pergunta_vmw or self.pergunta_pt) if idioma == "vmw" else self.pergunta_pt

    def resposta(self, idioma="pt"):
        return (self.resposta_vmw or self.resposta_pt) if idioma == "vmw" else self.resposta_pt

    def termos(self, idioma="pt"):
        campos = [self.pergunta_pt, self.palavras_chave_pt]
        if idioma == "vmw":
            campos += [self.pergunta_vmw, self.palavras_chave_vmw]
        return ", ".join(c for c in campos if c)

    def para_json(self):
        """Forma exportada para o service worker — o mesmo conteúdo, offline."""
        return {
            "id": self.pk,
            "topico": self.topico.codigo,
            "pergunta_pt": self.pergunta_pt,
            "pergunta_vmw": self.pergunta_vmw,
            "resposta_pt": self.resposta_pt,
            "resposta_vmw": self.resposta_vmw,
            "chaves_pt": self.palavras_chave_pt,
            "chaves_vmw": self.palavras_chave_vmw,
            "gravidade": self.gravidade,
            "fonte": self.fonte,
            "validado_por": self.validado_por,
            "traducao_vmw_validada": self.traducao_vmw_validada,
        }
