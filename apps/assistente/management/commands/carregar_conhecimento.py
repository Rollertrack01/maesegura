import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.assistente.models import Conhecimento, Topico

FICHEIRO = Path(__file__).resolve().parents[3] / "assistente" / "dados" / "conhecimento_inicial.json"


class Command(BaseCommand):
    help = (
        "Carrega a base de conhecimento inicial. Por defeito o conteúdo entra SEM "
        "validação clínica e, portanto, não é servido às utilizadoras."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ficheiro", default=str(FICHEIRO), help="Caminho do JSON a carregar."
        )
        parser.add_argument(
            "--validar-como",
            default="",
            metavar="NOME E CREDENCIAL",
            help=(
                "Marca o conteúdo como validado por esta pessoa. Use apenas em ambiente "
                "de demonstração ou quando o clínico validou de facto."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **opcoes):
        dados = json.loads(Path(opcoes["ficheiro"]).read_text(encoding="utf-8"))
        validador = opcoes["validar_como"].strip()

        topicos = {}
        for bruto in dados["topicos"]:
            topico, _ = Topico.objects.update_or_create(
                codigo=bruto["codigo"],
                defaults={
                    "nome_pt": bruto["nome_pt"],
                    "nome_vmw": bruto.get("nome_vmw", ""),
                    "ordem": bruto.get("ordem", 0),
                },
            )
            topicos[topico.codigo] = topico

        criados = actualizados = 0
        for bruto in dados["conhecimentos"]:
            valores = {
                "topico": topicos[bruto["topico"]],
                "pergunta_vmw": bruto.get("pergunta_vmw", ""),
                "resposta_pt": bruto["resposta_pt"],
                "resposta_vmw": bruto.get("resposta_vmw", ""),
                "palavras_chave_pt": bruto.get("palavras_chave_pt", ""),
                "palavras_chave_vmw": bruto.get("palavras_chave_vmw", ""),
                "gravidade": bruto.get("gravidade", Conhecimento.INFORMATIVO),
                "destaque": bruto.get("destaque", False),
                "fonte": bruto["fonte"],
            }
            if validador:
                valores["validado_por"] = validador
                valores["validado_em"] = timezone.now()

            _, foi_criado = Conhecimento.objects.update_or_create(
                pergunta_pt=bruto["pergunta_pt"], defaults=valores
            )
            criados += int(foi_criado)
            actualizados += int(not foi_criado)

        self.stdout.write(
            self.style.SUCCESS(
                f"{criados} conteúdos criados, {actualizados} actualizados, "
                f"{len(topicos)} tópicos."
            )
        )
        if validador:
            self.stdout.write(
                self.style.WARNING(f"Marcado como validado por: {validador}.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Conteúdo por validar: nada será servido às utilizadoras até um "
                    "profissional de saúde validar em /gestao/."
                )
            )
        self.stdout.write(
            self.style.WARNING(
                "Traduções para Emakhuwa são rascunhos — marque traducao_vmw_validada "
                "só depois da revisão por falante nativo."
            )
        )
