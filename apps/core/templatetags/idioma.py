from django import template

from apps.core.i18n import traduzir

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, chave):
    return traduzir(chave, context.get("idioma", "pt"))
