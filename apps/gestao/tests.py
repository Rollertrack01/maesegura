from django.contrib.auth.models import Group, User
from django.test import TestCase

from apps.core.testes import ClienteComCarimbo
from django.utils import timezone

from apps.acompanhamento.models import Contacto, UnidadeSanitaria
from apps.acompanhamento.servicos import registar_gestante
from apps.assistente.models import Conhecimento, Topico

from .perfis import CLINICO, GESTOR, garantir_grupos, pode_validar_conteudo


def criar_utilizador(nome, perfil=None, superuser=False, nome_proprio="", apelido=""):
    if superuser:
        return User.objects.create_superuser(nome, f"{nome}@exemplo.mz", "senha-longa-123")
    utilizador = User.objects.create_user(
        nome, f"{nome}@exemplo.mz", "senha-longa-123",
        first_name=nome_proprio, last_name=apelido,
    )
    if perfil:
        garantir_grupos()
        utilizador.groups.add(Group.objects.get(name=perfil))
    return utilizador


def criar_conteudo(**extra):
    topico = Topico.objects.first() or Topico.objects.create(codigo="t", nome_pt="Tópico")
    valores = {
        "topico": topico,
        "pergunta_pt": "Estou a sangrar pela vagina. O que faço?",
        "resposta_pt": "Vá já à unidade sanitária mais próxima, a qualquer hora do dia ou da noite.",
        "palavras_chave_pt": "sangue, sangrar, hemorragia",
        "gravidade": Conhecimento.URGENTE,
        "fonte": "OMS",
    }
    valores.update(extra)
    return Conhecimento.objects.create(**valores)


class AcessoTest(TestCase):
    client_class = ClienteComCarimbo
    def test_painel_exige_autenticacao(self):
        resposta = self.client.get("/gestao/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/gestao/entrar/", resposta["Location"])

    def test_conta_sem_perfil_nao_entra(self):
        criar_utilizador("sem_perfil")
        resposta = self.client.post(
            "/gestao/entrar/", {"username": "sem_perfil", "password": "senha-longa-123"}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "ainda não tem perfil")

    def test_clinico_entra_e_ve_o_painel(self):
        criar_utilizador("clinica", CLINICO)
        resposta = self.client.post(
            "/gestao/entrar/", {"username": "clinica", "password": "senha-longa-123"},
            follow=True,
        )
        self.assertContains(resposta, "Painel principal")

    def test_django_admin_mudou_de_sitio(self):
        """/gestao/ é o painel próprio; o admin técnico vive em /sistema/."""
        criar_utilizador("tecnico", superuser=True)
        self.client.force_login(User.objects.get(username="tecnico"))
        self.assertEqual(self.client.get("/sistema/").status_code, 200)
        self.assertContains(self.client.get("/gestao/"), "Painel de gestão")


class SeparacaoDePoderesTest(TestCase):
    """O gestor coordena; só o clínico assina. É isto que torna a regra defensável."""
    client_class = ClienteComCarimbo

    def setUp(self):
        self.conteudo = criar_conteudo()

    def test_gestor_nao_pode_validar_conteudo(self):
        gestor = criar_utilizador("gestor", GESTOR)
        self.assertFalse(pode_validar_conteudo(gestor))
        self.client.force_login(gestor)
        resposta = self.client.post(f"/gestao/conteudos/{self.conteudo.pk}/validar/")
        self.assertEqual(resposta.status_code, 403)
        self.conteudo.refresh_from_db()
        self.assertFalse(self.conteudo.validado)

    def test_gestor_nao_pode_alterar_conteudo(self):
        self.client.force_login(criar_utilizador("gestor2", GESTOR))
        self.client.post(f"/gestao/conteudos/{self.conteudo.pk}/", {
            "topico": self.conteudo.topico_id,
            "gravidade": Conhecimento.INFORMATIVO,
            "pergunta_pt": "Alterado por quem não devia",
            "resposta_pt": "Texto suficientemente longo para passar a validação do formulário.",
            "fonte": "x",
        })
        self.conteudo.refresh_from_db()
        self.assertEqual(self.conteudo.pergunta_pt, "Estou a sangrar pela vagina. O que faço?")

    def test_clinico_valida_e_assina_com_o_proprio_nome(self):
        clinica = criar_utilizador("clinica", CLINICO, nome_proprio="Ana", apelido="Mucavele")
        self.client.force_login(clinica)
        resposta = self.client.post(
            f"/gestao/conteudos/{self.conteudo.pk}/validar/", follow=True
        )
        self.conteudo.refresh_from_db()
        self.assertTrue(self.conteudo.validado)
        self.assertEqual(self.conteudo.validado_por, "Ana Mucavele")
        self.assertContains(resposta, "Ana Mucavele")

    def test_validar_torna_o_conteudo_servivel(self):
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 0)
        self.client.force_login(criar_utilizador("clinica2", CLINICO, nome_proprio="Ana", apelido="M"))
        self.client.post(f"/gestao/conteudos/{self.conteudo.pk}/validar/")
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 1)

    def test_retirar_validacao_deixa_de_servir(self):
        clinica = criar_utilizador("clinica3", CLINICO, nome_proprio="Ana", apelido="M")
        self.client.force_login(clinica)
        self.client.post(f"/gestao/conteudos/{self.conteudo.pk}/validar/")
        self.client.post(f"/gestao/conteudos/{self.conteudo.pk}/retirar/")
        self.assertEqual(Conhecimento.objects.publicaveis().count(), 0)

    def test_clinico_nao_ve_seccoes_de_gestao(self):
        self.client.force_login(criar_utilizador("clinica4", CLINICO))
        self.assertEqual(self.client.get("/gestao/consultas/").status_code, 403)
        self.assertEqual(self.client.get("/gestao/unidades/").status_code, 403)

    def test_so_superuser_gere_a_equipa(self):
        self.client.force_login(criar_utilizador("gestor3", GESTOR))
        self.assertEqual(self.client.get("/gestao/equipa/").status_code, 403)
        self.client.force_login(criar_utilizador("tecnico2", superuser=True))
        self.assertEqual(self.client.get("/gestao/equipa/").status_code, 200)


class TrabalhoDoGestorTest(TestCase):
    client_class = ClienteComCarimbo
    def setUp(self):
        self.gestor = criar_utilizador("gestora", GESTOR)
        self.client.force_login(self.gestor)

    def test_marca_consulta_como_realizada(self):
        gestante = registar_gestante(semana=12)
        contacto = gestante.contactos.first()
        self.client.post(f"/gestao/consultas/{contacto.pk}/estado/", {"estado": "realizado"})
        contacto.refresh_from_db()
        self.assertEqual(contacto.estado, Contacto.REALIZADO)
        self.assertIsNotNone(contacto.registado_em)

    def test_lista_de_gestantes_nao_mostra_telefone(self):
        registar_gestante(semana=20, telefone="840000000", distrito="Rapale")
        corpo = self.client.get("/gestao/gestantes/").content.decode()
        self.assertNotIn("840000000", corpo)
        self.assertIn("Rapale", corpo)

    def test_cria_unidade_sanitaria(self):
        self.client.post("/gestao/unidades/nova/", {
            "nome": "Centro de Saúde de Rapale", "distrito": "Rapale",
            "tipo": "Centro de saúde", "telefone": "+258 26 000 000", "confirmado_em": "",
        })
        self.assertTrue(UnidadeSanitaria.objects.filter(nome__startswith="Centro").exists())

    def test_unidade_por_confirmar_nao_aparece_as_utilizadoras(self):
        UnidadeSanitaria.objects.create(nome="X", distrito="Y")
        UnidadeSanitaria.objects.create(nome="Z", distrito="Y", confirmado_em=timezone.localdate())
        corpo = self.client.get("/").content.decode()
        self.assertIn("Z", corpo)
        self.assertNotIn(">X (Y)<", corpo)

    def test_exporta_indicadores_em_csv(self):
        resposta = self.client.get("/gestao/exportar/indicadores.csv")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/csv", resposta["Content-Type"])
        self.assertIn("conteudos_validados", resposta.content.decode())


class CriarPerfisTest(TestCase):
    client_class = ClienteComCarimbo
    def test_comando_e_idempotente(self):
        from django.core.management import call_command

        call_command("criar_perfis", verbosity=0)
        call_command("criar_perfis", verbosity=0)
        self.assertEqual(Group.objects.filter(name__in=[CLINICO, GESTOR]).count(), 2)
