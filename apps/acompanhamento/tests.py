from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Contacto, EventoUso, Gestante
from .servicos import gerar_calendario, registar_gestante


class CalculoDaGravidezTest(TestCase):
    def test_dpp_sao_quarenta_semanas_completas(self):
        registo = date(2026, 10, 21)
        self.assertEqual(
            Gestante.calcular_dpp(12, registo), registo + timedelta(days=28 * 7)
        )
        self.assertEqual(Gestante.calcular_dpp(40, registo), registo)

    def test_semana_actual_avanca_uma_por_semana(self):
        gestante = registar_gestante(semana=20)
        Gestante.objects.filter(pk=gestante.pk).update(
            data_registo=timezone.localdate() - timedelta(days=21)
        )
        gestante.refresh_from_db()
        self.assertEqual(gestante.semana_actual(), 23)

    def test_semana_actual_nao_passa_de_42(self):
        gestante = registar_gestante(semana=40)
        Gestante.objects.filter(pk=gestante.pk).update(
            data_registo=timezone.localdate() - timedelta(days=70)
        )
        gestante.refresh_from_db()
        self.assertEqual(gestante.semana_actual(), 42)


class CalendarioOMSTest(TestCase):
    def test_oito_contactos_para_quem_se_regista_cedo(self):
        gestante = registar_gestante(semana=8)
        semanas = list(gestante.contactos.values_list("semana_alvo", flat=True))
        self.assertEqual(semanas, list(Contacto.SEMANAS_OMS))

    def test_nao_marca_consultas_de_semanas_ja_passadas(self):
        gestante = registar_gestante(semana=30)
        semanas = list(gestante.contactos.values_list("semana_alvo", flat=True))
        self.assertEqual(semanas, [30, 34, 36, 38, 40])
        self.assertNotIn(12, semanas)

    def test_datas_nunca_caem_no_passado(self):
        gestante = registar_gestante(semana=35)
        hoje = timezone.localdate()
        for contacto in gestante.contactos.all():
            self.assertGreaterEqual(contacto.data_prevista, hoje)

    def test_calendario_nao_duplica_contactos(self):
        gestante = registar_gestante(semana=12)
        with self.assertRaises(Exception):
            gerar_calendario(gestante)

    def test_consulta_passada_fica_em_atraso(self):
        gestante = registar_gestante(semana=12)
        contacto = gestante.contactos.first()
        Contacto.objects.filter(pk=contacto.pk).update(
            data_prevista=timezone.localdate() - timedelta(days=3)
        )
        contacto.refresh_from_db()
        self.assertTrue(contacto.em_atraso())


class PrivacidadeTest(TestCase):
    def test_modelo_nao_tem_campo_de_nome(self):
        campos = {c.name for c in Gestante._meta.get_fields()}
        for proibido in ("nome", "apelido", "nome_completo", "bi", "documento"):
            self.assertNotIn(proibido, campos)

    def test_codigo_nao_usa_caracteres_confundiveis(self):
        codigos = [registar_gestante(semana=20).codigo for _ in range(25)]
        for codigo in codigos:
            self.assertFalse(set(codigo) & set("O0I1S5"), codigo)

    def test_consentimento_e_registado_com_versao(self):
        gestante = registar_gestante(semana=20)
        self.assertIsNotNone(gestante.consentimento_em)
        self.assertTrue(gestante.consentimento_versao)


class FluxoWebTest(TestCase):
    def test_registo_exige_consentimento(self):
        resposta = self.client.post("/", {"semana": "20"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Gestante.objects.count(), 0)

    def test_registo_valida_a_semana(self):
        resposta = self.client.post("/", {"semana": "99", "consentimento": "sim"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Gestante.objects.count(), 0)

    def test_registo_valido_cria_gestante_e_calendario(self):
        resposta = self.client.post(
            "/", {"semana": "12", "consentimento": "sim", "distrito": "Rapale"}
        )
        self.assertRedirects(resposta, "/acompanhamento/")
        gestante = Gestante.objects.get()
        self.assertEqual(gestante.contactos.count(), 8)
        self.assertTrue(EventoUso.objects.filter(tipo=EventoUso.REGISTO).exists())

    def test_entrar_com_codigo_existente(self):
        gestante = registar_gestante(semana=16)
        self.client.cookies.clear()
        resposta = self.client.post("/entrar/", {"codigo": gestante.codigo.lower()})
        self.assertRedirects(resposta, "/acompanhamento/")

    def test_acompanhamento_sem_sessao_redirecciona(self):
        self.assertRedirects(self.client.get("/acompanhamento/"), "/")
