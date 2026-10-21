from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from apps.gestao.perfis import perfis_de

register = template.Library()

_ABRE = (
    '<svg class="icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
)

# Ícones de traço, desenhados aqui para não depender de biblioteca externa
# nem de uma segunda ligação de rede — o painel tem de abrir em ligação fraca.
ICONES = {
    "painel": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/>'
              '<rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "conteudo": '<path d="M5 3h9l5 5v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/>'
                '<path d="M14 3v5h5"/><path d="M8 13h8M8 17h5"/>',
    "calendario": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'
                  '<path d="M9 15l2 2 4-4"/>',
    "pessoas": '<path d="M16 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20"/><circle cx="9" cy="7" r="3.5"/>'
               '<path d="M22 20v-1.5a4 4 0 0 0-3-3.87"/><path d="M16 3.5a4 4 0 0 1 0 7"/>',
    "hospital": '<path d="M4 21V8l8-5 8 5v13"/><path d="M9 21v-5h6v5"/><path d="M12 8v4M10 10h4"/>',
    "descarregar": '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 20h16"/>',
    "equipa": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "chave": '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9"/><path d="m17 6 2 2"/><path d="m14 9 2 2"/>',
    "grafico": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "telemovel": '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>',
    "externo": '<path d="M14 4h6v6"/><path d="M20 4 11 13"/>'
               '<path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "mais": '<path d="M12 5v14M5 12h14"/>',
    "voltar": '<path d="M15 6 9 12l6 6"/>',
    "vazio": '<circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "feito": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 4.5-5"/>',
}


@register.simple_tag
def icone(nome, tamanho=20):
    corpo = ICONES.get(nome)
    if not corpo:
        return ""
    return mark_safe(
        _ABRE.replace('class="icone"', f'class="icone" width="{tamanho}" height="{tamanho}"')
        + corpo
        + "</svg>"
    )


@register.simple_tag
def activo(request, nome):
    try:
        return "activo" if request.path == reverse(nome) else ""
    except Exception:  # pragma: no cover
        return ""


@register.simple_tag
def perfis_do(utilizador):
    nomes = perfis_de(utilizador)
    if "superuser" in nomes:
        return "Administração técnica"
    return ", ".join(sorted(nomes)) or "sem perfil"
