from django.contrib import admin

from .models import Contacto, EventoUso, Gestante, UnidadeSanitaria


@admin.register(UnidadeSanitaria)
class UnidadeSanitariaAdmin(admin.ModelAdmin):
    list_display = ("nome", "distrito", "telefone", "confirmado_em")
    list_filter = ("distrito",)
    search_fields = ("nome", "distrito")


class ContactoInline(admin.TabularInline):
    model = Contacto
    extra = 0
    readonly_fields = ("numero", "semana_alvo")


@admin.register(Gestante)
class GestanteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "semana_gestacional_inicial", "data_registo",
                    "data_prevista_parto", "distrito", "idioma", "activa")
    list_filter = ("activa", "idioma", "distrito")
    search_fields = ("codigo",)
    readonly_fields = ("codigo", "consentimento_em", "consentimento_versao")
    inlines = [ContactoInline]


@admin.register(EventoUso)
class EventoUsoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "idioma", "distrito", "criado_em")
    list_filter = ("tipo", "idioma")
