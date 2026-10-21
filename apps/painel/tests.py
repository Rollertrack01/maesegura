from django.test import TestCase

from apps.acompanhamento.models import EventoUso
from apps.acompanhamento.servicos import registar_gestante


class PainelPublicoTest(TestCase):
    def test_painel_abre_sem_autenticacao(self):
        self.assertEqual(self.client.get("/painel/").status_code, 200)

    def test_json_abre_sem_autenticacao_e_permite_cors(self):
        resposta = self.client.get("/api/metricas.json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Access-Control-Allow-Origin"], "*")

    def test_metricas_contam_gestantes_activas(self):
        registar_gestante(semana=12)
        registar_gestante(semana=20)
        dados = self.client.get("/api/metricas.json").json()
        self.assertEqual(dados["gestantes_em_acompanhamento"], 2)
        # 8 contactos a partir da 12ª semana + 7 a partir da 20ª
        self.assertEqual(dados["consultas_marcadas"], 15)

    def test_taxa_de_resposta_e_calculada(self):
        EventoUso.registar(EventoUso.PERGUNTA)
        EventoUso.registar(EventoUso.PERGUNTA)
        EventoUso.registar(EventoUso.PERGUNTA_SEM_RESPOSTA)
        dados = self.client.get("/api/metricas.json").json()
        self.assertEqual(dados["perguntas_feitas"], 3)
        self.assertEqual(dados["taxa_resposta_percentagem"], 66.7)

    def test_json_nao_expoe_dados_pessoais(self):
        gestante = registar_gestante(semana=12, telefone="840000000", distrito="Rapale")
        corpo = self.client.get("/api/metricas.json").content.decode()
        self.assertNotIn("840000000", corpo)
        self.assertNotIn(gestante.codigo, corpo)

    def test_sem_dados_nao_rebenta(self):
        dados = self.client.get("/api/metricas.json").json()
        self.assertEqual(dados["taxa_resposta_percentagem"], 0.0)


class SaudeTest(TestCase):
    def test_healthcheck(self):
        dados = self.client.get("/saude/").json()
        self.assertEqual(dados["estado"], "ok")
        self.assertTrue(dados["validacao_clinica_exigida"])
        self.assertFalse(dados["llm_activo"])
