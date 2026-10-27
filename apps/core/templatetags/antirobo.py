from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.core.antirobo import CAMPO_ARMADILHA, CAMPO_CARIMBO, REGRAS, carimbo

register = template.Library()

_ESCONDIDO = (
    "position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden"
)


@register.simple_tag
def antirobo(nome, verificado=False):
    """
    Campos escondidos da protecção. `verificado=True` quando o formulário volta
    com erros de preenchimento: a pessoa não deve esperar o tempo mínimo outra vez.
    """
    if nome not in REGRAS:
        raise template.TemplateSyntaxError(f"Formulário desconhecido: {nome}")
    return format_html(
        '<div style="{}" aria-hidden="true">'
        '<label for="id_{}">Não preencha este campo</label>'
        '<input type="text" name="{}" id="id_{}" value="" tabindex="-1" autocomplete="off">'
        "</div>"
        '<input type="hidden" name="{}" value="{}">',
        mark_safe(_ESCONDIDO),
        CAMPO_ARMADILHA,
        CAMPO_ARMADILHA,
        CAMPO_ARMADILHA,
        CAMPO_CARIMBO,
        carimbo(nome, verificado=verificado),
    )


@register.simple_tag
def turnstile(nome):
    """Widget do Turnstile. Não aparece se não houver chaves no .env."""
    regra = REGRAS.get(nome)
    chave = getattr(settings, "TURNSTILE_SITE_KEY", "")
    if not regra or not regra.turnstile or not chave:
        return ""
    return format_html(
        '<div class="cf-turnstile" data-sitekey="{}" data-language="pt"></div>'
        '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>',
        chave,
    )
