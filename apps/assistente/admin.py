from django.contrib import admin
from django.utils import timezone

from .models import Conhecimento, Topico


@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ("nome_pt", "nome_vmw", "codigo", "ordem")


@admin.register(Conhecimento)
class ConhecimentoAdmin(admin.ModelAdmin):
    list_display = ("pergunta_pt", "topico", "gravidade", "tem_emakhuwa", "validado_por", "validado_em")
    list_filter = ("gravidade", "topico", "destaque")
    search_fields = ("pergunta_pt", "pergunta_vmw", "palavras_chave_pt")
    actions = ["marcar_validado"]
    fieldsets = (
        (None, {"fields": ("topico", "gravidade", "destaque", "semana_minima", "semana_maxima")}),
        ("Português", {"fields": ("pergunta_pt", "resposta_pt", "palavras_chave_pt")}),
        ("Emakhuwa", {"fields": ("pergunta_vmw", "resposta_vmw", "palavras_chave_vmw")}),
        ("Validação clínica", {
            "fields": ("fonte", "validado_por", "validado_em"),
            "description": "Sem estes dois campos preenchidos, o conteúdo não é servido à utilizadora.",
        }),
    )

    @admin.display(boolean=True, description="Emakhuwa")
    def tem_emakhuwa(self, obj):
        return bool(obj.resposta_vmw)

    @admin.action(description="Marcar como validado por mim, agora")
    def marcar_validado(self, request, queryset):
        nome = request.user.get_full_name() or request.user.get_username()
        actualizados = queryset.update(validado_por=nome, validado_em=timezone.now())
        self.message_user(request, f"{actualizados} conteúdo(s) validado(s) por {nome}.")
