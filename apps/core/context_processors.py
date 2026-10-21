from apps.core.i18n import IDIOMA_POR_DEFEITO


def idioma(request):
    actual = getattr(request, "idioma", IDIOMA_POR_DEFEITO)
    return {
        "idioma": actual,
        "idioma_alternativo": "vmw" if actual == "pt" else "pt",
    }
