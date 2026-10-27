"""Apoio aos testes dos formulários protegidos."""
from django.test import Client

from apps.core.antirobo import CAMPO_CARIMBO, carimbo


class ClienteComCarimbo(Client):
    """
    Cliente de teste que acrescenta um carimbo verificado aos POST.

    Usamos isto em vez de desligar a protecção: assim os testes exercitam o
    mesmo caminho que uma pessoa real percorre, e um erro na protecção aparece
    nos testes em vez de aparecer em produção.

    `formulario` é o nome da regra ("registo", "codigo", "assistente", "login").
    """

    formulario = None

    def __init__(self, *args, formulario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if formulario:
            self.formulario = formulario

    def post(self, caminho, dados=None, *args, formulario=None, **kwargs):
        nome = formulario or self.formulario or self._adivinhar(caminho)
        if nome and isinstance(dados, dict) and CAMPO_CARIMBO not in dados:
            dados = {**dados, CAMPO_CARIMBO: carimbo(nome, verificado=True)}
        return super().post(caminho, dados, *args, **kwargs)

    @staticmethod
    def _adivinhar(caminho):
        if caminho.startswith("/assistente/"):
            return "assistente"
        if caminho.startswith("/entrar/"):
            return "codigo"
        if caminho.startswith("/gestao/entrar/"):
            return "login"
        if caminho == "/":
            return "registo"
        return None
