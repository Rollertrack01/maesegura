from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.acompanhamento.models import EventoUso

from .busca import fichar, procurar
from .models import Conhecimento, Topico


def criar_conhecimento(**extra):
    topico = Topico.objects.first() or Topico.objects.create(codigo="t", nome_pt="Tópico")
    valores = {
        "topico": topico,
        "pergunta_pt": "Estou a sangrar pela vagina. O que faço?",
        "resposta_pt": "Vá já à unidade sanitária.",
        "palavras_chave_pt": "sangue, sangrar, hemorragia, perder sangue",
        "gravidade": Conhecimento.URGENTE,
        "fonte": "OMS",
        "validado_por": "Dra. Exemplo, médica",
        "validado_em": timezone.now(),
    }
    valores.update(extra)
    return Conhecimento.objects.create(**valores)


class BuscaTest(TestCase):
    def test_fichar_remove_acentos_e_palavras_vazias(self):
        self.assertEqual(fichar("Tenho uma dor de cabeça"), {"dor", "cabeca"})

    def test_encontra_pela_palavra_chave_mesmo_com_frase_diferente(self):
        item = {"id": 1, "pergunta_pt": "Estou a sangrar", "chaves_pt": "sangue, hemorragia, perder sangue"}
        resultados = procurar("estou a perder sangue, muito sangue", [item])
        self.assertEqual(len(resultados), 1)

    def test_nao_devolve_nada_quando_nao_ha_relacao(self):
        item = {"id": 1, "pergunta_pt": "Estou a sangrar", "chaves_pt": "sangue, hemorragia"}
        self.assertEqual(procurar("onde compro farinha", [item]), [])

    def test_pergunta_vazia_nao_devolve_resultados(self):
        item = {"id": 1, "pergunta_pt": "Estou a sangrar", "chaves_pt": "sangue"}
        self.assertEqual(procurar("", [item]), [])

    def test_palavra_chave_em_emakhuwa_encontra_conteudo(self):
        item = {
            "id": 1,
            "pergunta_pt": "Estou a sangrar",
            "chaves_pt": "sangue",
            "pergunta_vmw": "Kinnakhuma ephome",
            "chaves_vmw": "ephome, nikhuma",
        }
        self.assertEqual(len(procurar("kinnakhuma ephome", [item], idioma="vmw")), 1)

    def test_descarta_correspondencias_fracas_ao_lado_de_uma_forte(self):
        """Uma palavra comum não deve arrastar conteúdos sem relação."""
        forte = {"id": 1, "pergunta_pt": "Estou a sangrar", "chaves_pt": "sangue, sangrar, perder sangue"}
        fraco = {"id": 2, "pergunta_pt": "Tive convulsões", "chaves_pt": "convulsao, perder os sentidos"}
        resultados = procurar("estou a perder muito sangue", [forte, fraco])
        self.assertEqual([r[0]["id"] for r in resultados], [1])

    def test_uma_palavra_em_comum_nao_chega_quando_ha_mais_palavras(self):
        item = {"id": 1, "pergunta_pt": "Onde devo ter o bebé?", "chaves_pt": "onde ter o bebe, maternidade"}
        self.assertEqual(procurar("onde compro farinha para o bebe", [item]), [])

    def test_pergunta_de_uma_so_palavra_ainda_encontra(self):
        item = {"id": 1, "pergunta_pt": "Quantas consultas devo fazer?", "chaves_pt": "consultas, pre natal"}
        self.assertEqual(len(procurar("quantas consultas devo fazer", [item])), 1)

    def test_pergunta_fora_do_dominio_nao_devolve_nada(self):
        item = {"id": 1, "pergunta_pt": "Estou a sangrar", "chaves_pt": "sangue, sangrar"}
        for fora in ("qual e o preco do milho", "quero saber sobre futebol", "preciso de dinheiro"):
            self.assertEqual(procurar(fora, [item]), [], fora)

    def test_ordena_pelo_melhor_resultado(self):
        fraco = {"id": 1, "pergunta_pt": "Dor de barriga", "chaves_pt": "dor"}
        forte = {"id": 2, "pergunta_pt": "Dor de cabeça forte", "chaves_pt": "dor, cabeca, forte"}
        resultados = procurar("dor de cabeça forte", [fraco, forte])
        self.assertEqual(resultados[0][0]["id"], 2)


class ValidacaoClinicaTest(TestCase):
    def test_conteudo_por_validar_nao_e_publicavel(self):
        criar_conhecimento(validado_por="", validado_em=None)
        self.assertEqual(Conhecimento.objects.count(), 1)
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 0)

    def test_conteudo_validado_e_publicavel(self):
        criar_conhecimento()
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 1)

    def test_nao_se_publica_validacao_anonima(self):
        item = Conhecimento(
            topico=Topico.objects.create(codigo="x", nome_pt="X"),
            pergunta_pt="p",
            resposta_pt="r",
            fonte="f",
            validado_em=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    @override_settings(EXIGIR_VALIDACAO_CLINICA=False)
    def test_modo_sem_validacao_e_explicito(self):
        criar_conhecimento(validado_por="", validado_em=None)
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 1)


class AssistenteWebTest(TestCase):
    def test_pergunta_sem_resposta_validada_nao_inventa(self):
        criar_conhecimento(validado_por="", validado_em=None)
        resposta = self.client.post("/assistente/", {"pergunta": "estou a sangrar"})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, "Vá já à unidade sanitária.")
        self.assertTrue(
            EventoUso.objects.filter(tipo=EventoUso.PERGUNTA_SEM_RESPOSTA).exists()
        )

    def test_pergunta_com_resposta_validada_devolve_conteudo(self):
        criar_conhecimento()
        resposta = self.client.post("/assistente/", {"pergunta": "estou a perder sangue"})
        self.assertContains(resposta, "Vá já à unidade sanitária.")
        self.assertTrue(EventoUso.objects.filter(tipo=EventoUso.PERGUNTA).exists())

    def test_sinal_de_perigo_gera_encaminhamento(self):
        criar_conhecimento()
        self.client.post("/assistente/", {"pergunta": "estou a perder sangue"})
        self.assertTrue(EventoUso.objects.filter(tipo=EventoUso.ALERTA_URGENTE).exists())

    def test_json_so_expoe_conteudo_validado(self):
        criar_conhecimento()
        criar_conhecimento(
            pergunta_pt="Outra", palavras_chave_pt="outra", validado_por="", validado_em=None
        )
        dados = self.client.get("/assistente/conhecimento.json").json()
        self.assertEqual(dados["total"], 1)


class CarregadorTest(TestCase):
    def test_carrega_sem_validar_por_defeito(self):
        call_command("carregar_conhecimento", verbosity=0)
        self.assertGreater(Conhecimento.objects.count(), 0)
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 0)

    def test_carrega_e_valida_quando_pedido(self):
        call_command("carregar_conhecimento", validar_como="Dra. Exemplo", verbosity=0)
        self.assertEqual(
            Conhecimento.objects.count(), Conhecimento.objects.publicaveis().count()
        )

    def test_e_idempotente(self):
        call_command("carregar_conhecimento", verbosity=0)
        total = Conhecimento.objects.count()
        call_command("carregar_conhecimento", verbosity=0)
        self.assertEqual(Conhecimento.objects.count(), total)

    def test_todo_o_conteudo_declara_fonte(self):
        call_command("carregar_conhecimento", verbosity=0)
        self.assertFalse(Conhecimento.objects.filter(fonte="").exists())
