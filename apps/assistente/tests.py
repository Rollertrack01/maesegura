from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.testes import ClienteComCarimbo

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
    client_class = ClienteComCarimbo
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
    client_class = ClienteComCarimbo
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
    client_class = ClienteComCarimbo
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
    client_class = ClienteComCarimbo
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


class PonteDoEmakhuwaTest(TestCase):
    """
    O léxico do «Tradutor e Dicionário Emakhuwa» entrou na v0.6.0 para ajudar
    a ENCONTRAR conteúdo assinado. Estes testes defendem a fronteira: pode
    ajudar a encontrar, não pode decidir sozinho e não toca nas respostas.
    """

    client_class = ClienteComCarimbo

    def setUp(self):
        self.dor = criar_conhecimento(
            pergunta_pt="Tenho dor de cabeça muito forte",
            resposta_pt="Vá já à unidade sanitária mais próxima.",
            palavras_chave_pt="cabeca, dor, cabeça, doer",
            gravidade=Conhecimento.URGENTE,
        )

    def test_normalizacao_junta_grafias_da_mesma_palavra(self):
        from .emakhuwa import normalizada, radical

        # ph/th/kh/tth e vogais longas não podem separar a mesma palavra.
        self.assertEqual(normalizada("ophenta"), normalizada("openta"))
        self.assertEqual(normalizada("maasi"), normalizada("masi"))
        self.assertEqual(normalizada("otthuka"), normalizada("ottuka"))
        # «tth» tem de ser reduzido antes de «th», senão a raiz muda.
        self.assertEqual(normalizada("otthuka"), "otuka")
        self.assertTrue(radical("ohawa"))

    def test_grafia_diferente_da_mesma_palavra_continua_a_encontrar(self):
        """
        O ganho maior da v0.6.0, e o mais silencioso. As chaves em Emakhuwa do
        conteúdo real escrevem «okhuma maasi»; quem escrever «okuma masi» —
        sem a aspirada e sem a vogal longa — está a dizer o mesmo e tem de
        chegar ao mesmo sítio.
        """
        item = {"id": 1, "pergunta_pt": "Rebentaram as águas antes do tempo",
                "chaves_pt": "aguas, rebentar", "chaves_vmw": "maasi, okhuma maasi"}
        self.assertTrue(procurar("okhuma maasi", [item], idioma="vmw"))
        self.assertTrue(procurar("okuma masi", [item], idioma="vmw"))
        self.assertTrue(procurar("owereia muru", [
            {"id": 2, "pergunta_pt": "Dor de cabeça", "chaves_pt": "",
             "chaves_vmw": "muru, owereya muru"}], idioma="vmw"))

    def test_palavra_emakhuwa_chega_a_conteudo_escrito_em_portugues(self):
        """
        Duas palavras reconhecidas pelo léxico chegam a conteúdo cujas chaves
        estão só em português. É para isto que a ponte existe.
        """
        item = {"id": 1, "pergunta_pt": "A criança está doente",
                "chaves_pt": "cabeca, doenca", "chaves_vmw": ""}
        self.assertTrue(procurar("muru ereca", [item], idioma="vmw"))

    def test_uma_so_palavra_da_ponte_nunca_chega_sozinha(self):
        """
        O peso da ponte é mais baixo de propósito. Com um acervo em que
        nenhuma entrada foi confirmada por falante nativo, uma palavra
        reconhecida não pode, sozinha, pôr conteúdo clínico no ecrã.
        """
        item = {"id": 1, "pergunta_pt": "Onde devo ter o bebé",
                "chaves_pt": "cabeca", "chaves_vmw": ""}
        self.assertEqual(procurar("muru", [item], idioma="vmw"), [])

    def test_a_ponte_nao_altera_as_perguntas_em_portugues(self):
        itens = [{"id": self.dor.id, "pergunta_pt": self.dor.pergunta_pt,
                  "chaves_pt": self.dor.palavras_chave_pt, "chaves_vmw": ""}]
        self.assertTrue(procurar("tenho muita dor de cabeça", itens))
        self.assertEqual(procurar("onde compro farinha", itens), [])

    def test_a_ponte_declara_o_que_entendeu(self):
        from .busca import pontes

        entendido = dict(pontes("muru onniwereya"))
        self.assertIn("muru", entendido)
        self.assertIn("cabeça", entendido["muru"])

    def test_o_lexico_nunca_entra_no_texto_servido(self):
        """
        A prova de que a fronteira existe: o conteúdo devolvido é, palavra por
        palavra, o que o clínico assinou. A ponte mexe na pergunta, não aqui.
        """
        itens = [{"id": self.dor.id, "pergunta_pt": self.dor.pergunta_pt,
                  "chaves_pt": "cabeca, doenca", "chaves_vmw": ""}]
        (encontrado, _), = procurar("muru ereca", itens, idioma="vmw")
        self.assertEqual(encontrado["pergunta_pt"], self.dor.pergunta_pt)
        self.assertEqual(encontrado["chaves_vmw"], "")

    def test_conhecimento_json_leva_o_lexico_para_o_telemovel(self):
        resposta = self.client.get("/assistente/conhecimento.json")
        dados = resposta.json()
        self.assertIn("lexico", dados)
        self.assertTrue(dados["lexico"])
        primeira = dados["lexico"][0]
        self.assertEqual(set(primeira), {"lema", "glosa"})

    def test_a_pagina_mostra_como_entendeu_a_pergunta(self):
        resposta = self.client.post("/assistente/", {"pergunta": "muru onniwereya"})
        self.assertContains(resposta, "muru")
        self.assertContains(resposta, "cabeça")


class ParesQueANormalizacaoFundeTest(TestCase):
    """
    A ortografia padronizada (Ngunga & Faquir, 2014) distingue estes pares;
    a nossa normalização funde-os, de propósito, para tolerar a grafia de quem
    escreve num telemóvel. Este teste não corrige a fusão — fixa-a, para que
    ninguém a descubra por acidente, e para que a lista cresça à medida que o
    glossário do dicionário registar novos pares.
    """

    FUNDIDOS = [
        ("omala", "omaala", "acabar / calar-se — duração vocálica"),
        ("ephula", "epula", "nariz / chuva — aspiração"),
        ("otthara", "othara", "retroflexa / aspirada"),
    ]
    DISTINTOS = [
        ("hapa", "khapa", "fígado / cágado — h contra kh"),
        ("efuula", "ephula", "flor / nariz — f contra ph"),
        ("nsu", "ncu", "voz: Central contra Imeetto"),
    ]

    def test_pares_fundidos_estao_declarados(self):
        from .emakhuwa import normalizada

        for a, b, nota in self.FUNDIDOS:
            self.assertEqual(normalizada(a), normalizada(b), f"deixou de fundir: {nota}")

    def test_pares_que_continuam_distintos(self):
        from .emakhuwa import normalizada

        for a, b, nota in self.DISTINTOS:
            self.assertNotEqual(normalizada(a), normalizada(b), f"passou a fundir: {nota}")

    def test_nenhum_par_fundido_esta_no_conteudo_clinico(self):
        """
        A fusão só é inofensiva enquanto os dois membros do par não andarem
        ambos pelo conteúdo. Se um dia andarem, este teste falha e obriga a
        decidir — que é o que se quer.
        """
        import json
        import pathlib
        import re

        caminho = pathlib.Path(__file__).resolve().parent / "dados" / "conhecimento_inicial.json"
        bruto = json.loads(caminho.read_text(encoding="utf-8"))["conhecimentos"]
        palavras = set()
        for c in bruto:
            for campo in ("palavras_chave_vmw", "pergunta_vmw", "resposta_vmw"):
                palavras |= {p.lower() for p in re.split(r"[^\wÀ-ÿ]+", c.get(campo, "") or "") if p}
        for a, b, nota in self.FUNDIDOS:
            self.assertFalse(
                a in palavras and b in palavras,
                f"«{a}» e «{b}» estão ambos no conteúdo e a busca não os distingue ({nota})",
            )


class LexicoTest(TestCase):
    def test_entradas_trazem_variante_e_origem(self):
        from .emakhuwa import ENTRADAS

        self.assertGreater(len(ENTRADAS), 250)
        for e in ENTRADAS:
            self.assertIn("variante", e)
            self.assertIn("origem", e)

    def test_a_forma_central_ganha_sobre_a_de_outra_variante(self):
        """
        Quando duas grafias caem na mesma chave, fica a Central — é a variante
        de Nampula e a norma do projecto.
        """
        from .emakhuwa import procurar_lema

        achado = procurar_lema("epula")
        self.assertIsNotNone(achado)
        self.assertEqual(achado["variante"], "C")

    def test_o_termo_clinico_mais_importante_esta_no_lexico(self):
        """«ephome» é sangue. É a palavra do conteúdo mais urgente que há."""
        from .emakhuwa import procurar_lema

        self.assertEqual(procurar_lema("ephome")["glosa"], "sangue")
