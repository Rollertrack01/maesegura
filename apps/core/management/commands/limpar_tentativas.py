from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import TentativaPublica


class Command(BaseCommand):
    help = "Apaga tentativas públicas com mais de 90 dias."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=90)

    def handle(self, *args, **opcoes):
        limite = timezone.now() - timedelta(days=opcoes["dias"])
        apagadas, _ = TentativaPublica.objects.filter(criado_em__lt=limite).delete()
        self.stdout.write(self.style.SUCCESS(f"{apagadas} tentativa(s) apagada(s)."))
