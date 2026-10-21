from django.core.management.base import BaseCommand

from apps.gestao.perfis import garantir_grupos


class Command(BaseCommand):
    help = "Cria os grupos de perfil do painel de gestão (Clínico, Gestor)."

    def handle(self, *args, **opcoes):
        grupos = garantir_grupos()
        self.stdout.write(self.style.SUCCESS(
            "Perfis disponíveis: " + ", ".join(g.name for g in grupos)
        ))
        self.stdout.write(
            "Atribua perfis às contas em /gestao/equipa/ (só o superuser vê essa secção)."
        )
