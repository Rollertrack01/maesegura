from datetime import timedelta

from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class TentativaPublica(models.Model):
    """
    Registo das tentativas nos pontos de entrada públicos.

    Não é auditoria: serve para contar limites e para a página Segurança do
    painel. As linhas com mais de 90 dias são apagadas pelo comando
    `limpar_tentativas`.

    Privacidade: guardamos o endereço IP e o nome de utilizador tentado no
    login, nunca o texto que a mulher escreveu nem o código que introduziu.
    """

    RESULTADOS = [
        ("ACEITE", "Aceite"),
        ("FALHOU", "Senha errada"),
        ("ARMADILHA", "Campo-armadilha preenchido"),
        ("RAPIDO", "Enviado depressa demais"),
        ("SEM_CARIMBO", "Sem carimbo válido"),
        ("EXPIRADO", "Carimbo expirado"),
        ("DESAFIO", "Falhou o desafio"),
        ("LIMITE", "Limite por IP atingido"),
    ]

    formulario = models.CharField(max_length=32)
    ip = models.GenericIPAddressField()
    utilizador_tentado = models.CharField(max_length=150, blank=True)
    resultado = models.CharField(max_length=16, choices=RESULTADOS)
    navegador = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "tentativa pública"
        verbose_name_plural = "tentativas públicas"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["formulario", "ip", "criado_em"]),
            models.Index(fields=["resultado", "criado_em"]),
        ]

    def __str__(self):
        return f"{self.formulario} · {self.ip} · {self.resultado}"

    @property
    def bloqueada(self):
        return self.resultado not in ("ACEITE", "FALHOU")

    @classmethod
    def excedeu(cls, formulario, ip, limite_hora):
        """Conta na base de dados, não em memória: cada worker do Gunicorn
        teria a sua própria contagem e o limite não valeria nada."""
        desde = timezone.now() - timedelta(hours=1)
        return cls.objects.filter(
            formulario=formulario, ip=ip, criado_em__gte=desde
        ).count() >= limite_hora

    @classmethod
    def bloqueado_por_senhas(cls, *, ip, utilizador, por_ip, por_conta, minutos):
        desde = timezone.now() - timedelta(minutes=minutos)
        base = cls.objects.filter(formulario="login", resultado="FALHOU", criado_em__gte=desde)
        if base.filter(ip=ip).count() >= por_ip:
            return True
        if utilizador and base.filter(utilizador_tentado=utilizador).count() >= por_conta:
            return True
        return False

    @classmethod
    def resumo(cls, dias=30):
        desde = timezone.now() - timedelta(days=dias)
        recentes = cls.objects.filter(criado_em__gte=desde)
        bloqueadas = recentes.exclude(resultado__in=["ACEITE", "FALHOU"])
        return {
            "dias": dias,
            "total": recentes.count(),
            "bloqueadas": bloqueadas.count(),
            "senhas_erradas": recentes.filter(resultado="FALHOU").count(),
            "por_motivo": list(
                bloqueadas.values("resultado").annotate(total=Count("id")).order_by("-total")
            ),
            "por_formulario": list(
                bloqueadas.values("formulario").annotate(total=Count("id")).order_by("-total")
            ),
            "ips": list(
                bloqueadas.values("ip")
                .annotate(total=Count("id"))
                .order_by("-total")[:10]
            ),
        }
