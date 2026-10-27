from django.contrib import admin

from .models import TentativaPublica


@admin.register(TentativaPublica)
class TentativaPublicaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "formulario", "ip", "resultado", "utilizador_tentado")
    list_filter = ("formulario", "resultado")
    search_fields = ("ip", "utilizador_tentado")
    readonly_fields = [c.name for c in TentativaPublica._meta.fields]

    def has_add_permission(self, request):
        return False
