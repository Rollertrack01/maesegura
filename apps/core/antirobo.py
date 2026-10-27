"""
Protecção anti-robô dos formulários públicos.

Quatro camadas, nesta ordem: campo-armadilha, carimbo de tempo assinado,
limite por endereço IP e bloqueio de senhas. O Cloudflare Turnstile é a quinta,
opcional, e só aparece quando há chaves no .env.

Particularidade deste sistema: as utilizadoras são mulheres grávidas em
comunidades com ligação fraca, muitas vezes com a aplicação instalada e a
funcionar a partir de páginas guardadas no telemóvel. Por isso:

- o carimbo vale 3 dias e o service worker passou a ir à rede primeiro nas
  páginas, para que o carimbo e o token CSRF nunca cheguem velhos ao envio;
- os tempos mínimos são curtos, porque quem preenche já demora por natureza e
  um agente comunitário de saúde pode registar várias mulheres seguidas;
- os limites por IP são generosos nos formulários de registo e de perguntas,
  porque uma unidade sanitária inteira partilha a mesma ligação.

A excepção é a entrada por código: aí o limite é apertado de propósito, porque
é o único ponto onde alguém poderia procurar à força o registo de outra mulher.
"""
import ipaddress
import logging
from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.utils import timezone

logger = logging.getLogger(__name__)

SALT = "maesegura.antirobo"
CAMPO_ARMADILHA = "endereco_web"
CAMPO_CARIMBO = "carimbo"
VALIDADE_SEGUNDOS = 3 * 24 * 60 * 60

# Resultados registados em TentativaPublica
ACEITE = "ACEITE"
FALHOU = "FALHOU"
ARMADILHA = "ARMADILHA"
RAPIDO = "RAPIDO"
SEM_CARIMBO = "SEM_CARIMBO"
EXPIRADO = "EXPIRADO"
DESAFIO = "DESAFIO"
LIMITE = "LIMITE"


@dataclass(frozen=True)
class Regra:
    nome: str
    segundos_minimos: int
    limite_hora: int
    turnstile: bool = False


REGRAS = {
    # Registo: formulário médio. Um agente de saúde pode registar várias
    # mulheres a seguir na mesma unidade, daí o limite alto.
    "registo": Regra("registo", segundos_minimos=3, limite_hora=40),
    # Perguntas: a mesma mulher pergunta várias vezes; escrever já demora.
    "assistente": Regra("assistente", segundos_minimos=2, limite_hora=60),
    # Entrada por código: aqui o limite é a defesa. Seis caracteres de um
    # alfabeto de 24 dão 191 milhões de combinações, mas sem limite nenhum
    # uma máquina podia procurar à vontade o registo de outra pessoa.
    "codigo": Regra("codigo", segundos_minimos=0, limite_hora=10),
    # Login do painel: tempo zero porque os gestores de senhas enviam logo.
    "login": Regra("login", segundos_minimos=0, limite_hora=30),
}

# Bloqueio de senhas
SENHAS_POR_IP = 10
SENHAS_POR_CONTA = 5
JANELA_BLOQUEIO_MINUTOS = 15


@dataclass(frozen=True)
class Veredicto:
    ok: bool
    resultado: str
    mensagem: str = ""

    @property
    def silencioso(self):
        """A armadilha responde como se tivesse corrido bem: o robô não aprende."""
        return self.resultado == ARMADILHA


def ip_do_pedido(request):
    """
    O endereço real atrás do Caddy é o ÚLTIMO de X-Forwarded-For — o que o
    proxy acrescentou. O primeiro é fornecido pelo cliente e seria falsificável.
    """
    bruto = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidato = bruto.split(",")[-1].strip() if bruto else ""
    if not candidato:
        candidato = (request.META.get("REMOTE_ADDR") or "").strip()
    try:
        return str(ipaddress.ip_address(candidato))
    except ValueError:
        # O Postgres recusa um endereço inválido num campo inet.
        return "0.0.0.0"


def carimbo(nome, verificado=False):
    """Valor assinado a colocar no campo escondido do formulário."""
    return signing.dumps(
        {"f": nome, "t": timezone.now().timestamp(), "v": bool(verificado)},
        salt=SALT,
    )


def _ler_carimbo(valor, nome):
    try:
        dados = signing.loads(valor, salt=SALT, max_age=VALIDADE_SEGUNDOS)
    except signing.SignatureExpired:
        return None, EXPIRADO
    except signing.BadSignature:
        return None, SEM_CARIMBO
    if dados.get("f") != nome:
        return None, SEM_CARIMBO
    return dados, None


def _turnstile_configurado():
    return bool(
        getattr(settings, "TURNSTILE_SITE_KEY", "")
        and getattr(settings, "TURNSTILE_SECRET_KEY", "")
    )


def _verificar_turnstile(resposta, ip):
    """
    Se a Cloudflare não responder, deixamos passar e registamos. Um formulário
    de saúde pública não pode ficar inacessível porque um serviço externo caiu.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    if not resposta:
        return False
    corpo = urllib.parse.urlencode({
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": resposta,
        "remoteip": ip,
    }).encode()
    pedido = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify", data=corpo
    )
    try:
        with urllib.request.urlopen(pedido, timeout=6) as r:
            return bool(json.loads(r.read().decode()).get("success"))
    except (urllib.error.URLError, OSError, ValueError) as erro:
        logger.warning("Turnstile indisponível, a deixar passar: %s", erro)
        return True


def verificar(request, nome):
    """
    Corre as camadas por ordem e devolve um Veredicto. Regista sempre a
    tentativa, para a página Segurança do painel poder mostrar o que foi travado.
    """
    from .models import TentativaPublica

    regra = REGRAS[nome]
    ip = ip_do_pedido(request)
    navegador = (request.META.get("HTTP_USER_AGENT") or "")[:200]

    def registar(resultado):
        TentativaPublica.objects.create(
            formulario=nome, ip=ip, resultado=resultado, navegador=navegador
        )

    # 1. Campo-armadilha
    if (request.POST.get(CAMPO_ARMADILHA) or "").strip():
        registar(ARMADILHA)
        return Veredicto(False, ARMADILHA)

    # 2. Carimbo de tempo assinado
    valor = request.POST.get(CAMPO_CARIMBO) or ""
    if not valor:
        registar(SEM_CARIMBO)
        return Veredicto(False, SEM_CARIMBO, "Por segurança, confirme e carregue outra vez no botão.")
    dados, erro = _ler_carimbo(valor, nome)
    if erro:
        registar(erro)
        return Veredicto(False, erro, "A página esteve aberta muito tempo. Confirme e envie outra vez.")

    if not dados.get("v") and regra.segundos_minimos:
        decorridos = timezone.now().timestamp() - float(dados.get("t", 0))
        if decorridos < regra.segundos_minimos:
            registar(RAPIDO)
            return Veredicto(False, RAPIDO, "Por segurança, confirme e carregue outra vez no botão.")

    # 3. Limite por endereço IP
    if TentativaPublica.excedeu(nome, ip, regra.limite_hora):
        registar(LIMITE)
        return Veredicto(False, LIMITE, "Demasiados envios deste local. Tente daqui a uma hora.")

    # 4. Turnstile, quando configurado para este formulário
    if regra.turnstile and _turnstile_configurado():
        if not _verificar_turnstile(request.POST.get("cf-turnstile-response"), ip):
            registar(DESAFIO)
            return Veredicto(False, DESAFIO, "Confirme que não é um robô e envie outra vez.")

    registar(ACEITE)
    return Veredicto(True, ACEITE)


def entrada_bloqueada(request, utilizador=""):
    """
    True quando há senhas erradas a mais deste IP ou desta conta na janela.
    Bloqueia MESMO com a senha certa — é o que trava a adivinhação.
    """
    from .models import TentativaPublica

    ip = ip_do_pedido(request)
    return TentativaPublica.bloqueado_por_senhas(
        ip=ip,
        utilizador=utilizador,
        por_ip=SENHAS_POR_IP,
        por_conta=SENHAS_POR_CONTA,
        minutos=JANELA_BLOQUEIO_MINUTOS,
    )


def registar_senha(request, utilizador, acertou):
    from .models import TentativaPublica

    TentativaPublica.objects.create(
        formulario="login",
        ip=ip_do_pedido(request),
        utilizador_tentado=(utilizador or "")[:150],
        resultado=ACEITE if acertou else FALHOU,
        navegador=(request.META.get("HTTP_USER_AGENT") or "")[:200],
    )
