from apps.core.i18n import CODIGOS, IDIOMA_POR_DEFEITO

CHAVE_SESSAO = "idioma"


class IdiomaMiddleware:
    """Idioma por ?lang=, memorizado na sessão. Sem cookies de terceiros."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pedido = request.GET.get("lang")
        if pedido in CODIGOS:
            request.session[CHAVE_SESSAO] = pedido
        request.idioma = request.session.get(CHAVE_SESSAO, IDIOMA_POR_DEFEITO)
        return self.get_response(request)
