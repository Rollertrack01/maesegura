from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core import signing
from django.test import Client, TestCase
from django.utils import timezone

from apps.acompanhamento.models import Gestante
from apps.gestao.perfis import garantir_grupos

from .antirobo import CAMPO_ARMADILHA, CAMPO_CARIMBO, SALT, carimbo, ip_do_pedido
from .models import TentativaPublica
from .testes import ClienteComCarimbo


def dados_de_registo(**extra):
    base = {"semana": "20", "consentimento": "sim"}
    base.update(extra)
    return base


class CarimboTest(TestCase):
    """Cliente cru, sem carimbo: é o que faz um robô."""

    def test_sem_carimbo_nada_e_gravado(self):
        resposta = Client().post("/", dados_de_registo())
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertTrue(TentativaPublica.objects.filter(resultado="SEM_CARIMBO").exists())

    def test_formulario_volta_com_os_dados_escritos(self):
        resposta = Client().post("/", dados_de_registo(distrito="Rapale"))
        self.assertContains(resposta, "Rapale")

    def test_carimbo_de_outro_formulario_nao_serve(self):
        resposta = Client().post("/", dados_de_registo(**{CAMPO_CARIMBO: carimbo("login")}))
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertEqual(resposta.status_code, 200)

    def test_assinatura_adulterada_e_recusada(self):
        valido = carimbo("registo")
        falso = valido[:-4] + ("aaaa" if not valido.endswith("aaaa") else "bbbb")
        Client().post("/", dados_de_registo(**{CAMPO_CARIMBO: falso}))
        self.assertEqual(Gestante.objects.count(), 0)

    def test_carimbo_expirado_e_recusado(self):
        antigo = signing.dumps(
            {"f": "registo", "t": timezone.now().timestamp(), "v": False}, salt=SALT
        )
        with patch("apps.core.antirobo.signing.loads", side_effect=signing.SignatureExpired):
            Client().post("/", dados_de_registo(**{CAMPO_CARIMBO: antigo}))
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertTrue(TentativaPublica.objects.filter(resultado="EXPIRADO").exists())


class TempoMinimoTest(TestCase):
    def test_envio_rapido_demais_e_recusado(self):
        resposta = Client().post(
            "/", dados_de_registo(**{CAMPO_CARIMBO: carimbo("registo")})
        )
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertTrue(TentativaPublica.objects.filter(resultado="RAPIDO").exists())
        self.assertContains(resposta, "carregue outra vez")

    def test_com_o_tempo_cumprido_passa(self):
        antes = timezone.now() - timedelta(seconds=30)
        with patch("apps.core.antirobo.timezone.now", return_value=antes):
            valor = carimbo("registo")
        resposta = Client().post("/", dados_de_registo(**{CAMPO_CARIMBO: valor}))
        self.assertRedirects(resposta, "/acompanhamento/")
        self.assertEqual(Gestante.objects.count(), 1)

    def test_carimbo_verificado_dispensa_a_espera(self):
        """Formulário devolvido por erros não obriga a esperar outra vez."""
        resposta = Client().post(
            "/", dados_de_registo(**{CAMPO_CARIMBO: carimbo("registo", verificado=True)})
        )
        self.assertRedirects(resposta, "/acompanhamento/")


class ArmadilhaTest(TestCase):
    def test_armadilha_responde_como_sucesso_e_nao_grava(self):
        """O robô não pode aprender o que o travou."""
        resposta = Client().post("/", dados_de_registo(**{
            CAMPO_CARIMBO: carimbo("registo", verificado=True),
            CAMPO_ARMADILHA: "http://spam.exemplo",
        }))
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertTrue(TentativaPublica.objects.filter(resultado="ARMADILHA").exists())

    def test_armadilha_vazia_nao_atrapalha(self):
        resposta = ClienteComCarimbo().post("/", dados_de_registo(**{CAMPO_ARMADILHA: ""}))
        self.assertRedirects(resposta, "/acompanhamento/")

    def test_campo_esta_escondido_e_fora_da_navegacao(self):
        corpo = Client().get("/").content.decode()
        self.assertIn('name="endereco_web"', corpo)
        self.assertIn("left:-10000px", corpo)
        self.assertIn('tabindex="-1"', corpo)
        self.assertIn('aria-hidden="true"', corpo)


class LimitePorIPTest(TestCase):
    def test_limite_do_registo_devolve_aviso(self):
        for _ in range(40):
            TentativaPublica.objects.create(formulario="registo", ip="127.0.0.1", resultado="ACEITE")
        resposta = ClienteComCarimbo().post("/", dados_de_registo())
        self.assertEqual(Gestante.objects.count(), 0)
        self.assertContains(resposta, "Demasiados envios")

    def test_entrada_por_codigo_tem_limite_apertado(self):
        """É o único ponto onde se poderia procurar à força o registo de outra mulher."""
        cliente = ClienteComCarimbo()
        for _ in range(10):
            cliente.post("/entrar/", {"codigo": "AAAAAA"})
        resposta = cliente.post("/entrar/", {"codigo": "AAAAAA"})
        self.assertContains(resposta, "Demasiados envios")

    def test_limite_conta_por_formulario(self):
        for _ in range(10):
            TentativaPublica.objects.create(formulario="codigo", ip="127.0.0.1", resultado="ACEITE")
        # o registo tem limite próprio e não é afectado
        self.assertRedirects(
            ClienteComCarimbo().post("/", dados_de_registo()), "/acompanhamento/"
        )


class BloqueioDeSenhasTest(TestCase):
    def setUp(self):
        garantir_grupos()
        self.pessoa = User.objects.create_user("ana", "a@x.mz", "senha-longa-123")
        self.pessoa.groups.add(Group.objects.get(name="Clínico"))

    def test_senhas_erradas_bloqueiam_mesmo_com_a_senha_certa(self):
        cliente = ClienteComCarimbo()
        for _ in range(5):
            cliente.post("/gestao/entrar/", {"username": "ana", "password": "errada"})
        resposta = cliente.post("/gestao/entrar/", {"username": "ana", "password": "senha-longa-123"})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Aguarde 15 minutos")
        self.assertNotIn("_auth_user_id", cliente.session)

    def test_mensagem_nao_revela_se_a_conta_existe(self):
        cliente = ClienteComCarimbo()
        for _ in range(5):
            cliente.post("/gestao/entrar/", {"username": "inexistente", "password": "x"})
        resposta = cliente.post("/gestao/entrar/", {"username": "inexistente", "password": "x"})
        corpo = resposta.content.decode()
        self.assertNotIn("não existe", corpo)
        self.assertNotIn("inexistente não", corpo)

    def test_entrada_valida_continua_a_funcionar(self):
        resposta = ClienteComCarimbo().post(
            "/gestao/entrar/", {"username": "ana", "password": "senha-longa-123"}
        )
        self.assertRedirects(resposta, "/gestao/", target_status_code=200)

    def test_bloqueio_passa_depois_da_janela(self):
        cliente = ClienteComCarimbo()
        for _ in range(5):
            cliente.post("/gestao/entrar/", {"username": "ana", "password": "errada"})
        antigas = timezone.now() - timedelta(minutes=16)
        TentativaPublica.objects.filter(resultado="FALHOU").update(criado_em=antigas)
        resposta = cliente.post("/gestao/entrar/", {"username": "ana", "password": "senha-longa-123"})
        self.assertRedirects(resposta, "/gestao/", target_status_code=200)


class EnderecoRealTest(TestCase):
    def _pedido(self, **meta):
        from django.test import RequestFactory

        return RequestFactory().get("/", **meta)

    def test_usa_o_ultimo_endereco_da_cadeia(self):
        """O primeiro é fornecido pelo cliente; o último foi o proxy que pôs."""
        pedido = self._pedido(HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.9", REMOTE_ADDR="172.18.0.2")
        self.assertEqual(ip_do_pedido(pedido), "10.0.0.9")

    def test_sem_cabecalho_usa_remote_addr(self):
        self.assertEqual(ip_do_pedido(self._pedido(REMOTE_ADDR="192.168.1.5")), "192.168.1.5")

    def test_endereco_invalido_nao_rebenta(self):
        pedido = self._pedido(HTTP_X_FORWARDED_FOR="nao-e-um-ip", REMOTE_ADDR="")
        self.assertEqual(ip_do_pedido(pedido), "0.0.0.0")


class TurnstileTest(TestCase):
    def test_sem_chaves_o_desafio_nao_aparece(self):
        self.assertNotIn("cf-turnstile", Client().get("/").content.decode())

    def test_cloudflare_em_baixo_deixa_passar(self):
        """Um formulário de saúde pública não pode depender de um serviço externo."""
        from .antirobo import _verificar_turnstile

        with patch("urllib.request.urlopen", side_effect=OSError("sem rede")):
            self.assertTrue(_verificar_turnstile("resposta", "1.2.3.4"))


class PaginaSegurancaTest(TestCase):
    client_class = ClienteComCarimbo

    def setUp(self):
        garantir_grupos()
        self.tecnico = User.objects.create_superuser("tecnico", "t@x.mz", "senha-longa-123")

    def test_so_a_equipa_tecnica_ve(self):
        gestor = User.objects.create_user("coord", "c@x.mz", "senha-longa-123")
        gestor.groups.add(Group.objects.get(name="Gestor"))
        self.client.force_login(gestor)
        self.assertEqual(self.client.get("/gestao/seguranca/").status_code, 403)

    def test_mostra_o_que_foi_bloqueado(self):
        TentativaPublica.objects.create(formulario="registo", ip="1.2.3.4", resultado="ARMADILHA")
        self.client.force_login(self.tecnico)
        resposta = self.client.get("/gestao/seguranca/")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "1.2.3.4")

    def test_nao_guarda_o_que_a_mulher_escreveu(self):
        self.client.post("/assistente/", {"pergunta": "estou a sangrar muito"})
        for t in TentativaPublica.objects.all():
            self.assertNotIn("sangrar", str(t.__dict__))


class LimpezaTest(TestCase):
    def test_apaga_tentativas_com_mais_de_90_dias(self):
        from django.core.management import call_command

        TentativaPublica.objects.create(formulario="registo", ip="1.1.1.1", resultado="ACEITE")
        antiga = TentativaPublica.objects.create(formulario="registo", ip="1.1.1.1", resultado="ACEITE")
        TentativaPublica.objects.filter(pk=antiga.pk).update(
            criado_em=timezone.now() - timedelta(days=100)
        )
        call_command("limpar_tentativas", verbosity=0)
        self.assertEqual(TentativaPublica.objects.count(), 1)
