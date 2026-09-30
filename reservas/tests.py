from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook

from .forms import ReservaForm
from .models import Categoria, Dispositivo, ItemReserva, Reserva, TipoDispositivo
from .services import disponibilidade, validar_itens


class DisponibilidadeTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="prof", password="senha")
        self.tipo = TipoDispositivo.objects.create(nome="Notebook Prata")
        for numero in range(3):
            Dispositivo.objects.create(tipo=self.tipo, numero_patrimonio=f"P{numero}", numero_id=f"ID{numero}")

    def test_sobreposicao_subtrai_reserva(self):
        reserva = Reserva.objects.create(professor=self.usuario, data=date(2026, 8, 27), hora_inicio=time(8), hora_fim=time(10))
        ItemReserva.objects.create(reserva=reserva, tipo_dispositivo=self.tipo, quantidade=2)
        linha = disponibilidade(date(2026, 8, 27), time(9), time(11), self.tipo)[0]
        self.assertEqual((linha["total"], linha["reservado"], linha["disponivel"]), (3, 2, 1))

    def test_edicao_exclui_a_propria_reserva_do_calculo(self):
        reserva = Reserva.objects.create(professor=self.usuario, data=date(2026, 8, 27), hora_inicio=time(8), hora_fim=time(10))
        ItemReserva.objects.create(reserva=reserva, tipo_dispositivo=self.tipo, quantidade=3)
        self.assertEqual(validar_itens(reserva.data, time(8), time(10), {self.tipo.pk: 3}, reserva.pk), {})

    def test_rejeita_excesso(self):
        self.assertIn(str(self.tipo.pk), validar_itens(date(2026, 8, 27), time(8), time(10), {self.tipo.pk: 4}))

    def test_formulario_converte_selecao_multiplas_em_intervalo(self):
        form = ReservaForm(data={
            "data": "2026-08-27",
            "horarios": ["08:50", "07:10", "08:00"],
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual((form.cleaned_data["hora_inicio"], form.cleaned_data["hora_fim"]), (time(7, 10), time(8, 50)))

    def test_formulario_exige_no_minimo_dois_horarios(self):
        form = ReservaForm(data={
            "data": "2026-08-27",
            "horarios": ["07:10"],
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("horarios", form.errors)

    def test_formulario_rejeita_horarios_com_intervalo_pulado(self):
        form = ReservaForm(data={
            "data": "2026-08-27",
            "horarios": ["07:10", "08:50"],
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("horarios", form.errors)

    def test_formulario_rejeita_valor_de_horario_nao_permitido(self):
        form = ReservaForm(data={
            "data": "2026-08-27",
            "horarios": ["07:10", "07:30"],
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("horarios", form.errors)

    def test_tela_exibe_opcoes_multiplas_sem_campos_inicio_fim(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get("/reservas/nova/")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'name="horarios"', count=9)
        for horario in ("07:10", "08:00", "08:50", "09:55", "10:45", "11:35", "13:30", "14:20", "15:10"):
            self.assertContains(resposta, f'value="{horario}"')
        self.assertNotContains(resposta, 'name="hora_inicio"')
        self.assertNotContains(resposta, 'name="hora_fim"')

    def test_criacao_persiste_intervalo_e_disponibilidade_usa_selecao(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post("/reservas/nova/", {
            "data": "2026-08-27",
            "horarios": ["07:10", "08:00", "08:50"],
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertRedirects(resposta, "/reservas/")
        reserva = Reserva.objects.get(data=date(2026, 8, 27))
        self.assertEqual((reserva.hora_inicio, reserva.hora_fim), (time(7, 10), time(8, 50)))
        self.assertEqual(reserva.itens.get(tipo_dispositivo=self.tipo).quantidade, 1)
        linha = disponibilidade(reserva.data, time(8, 45), time(8, 55), self.tipo)[0]
        self.assertEqual(linha["reservado"], 1)
        self.assertContains(self.client.get("/reservas/"), "07:10 - 08:50")

    def test_edicao_preserva_horarios_legados_ate_alteracao_explicita(self):
        reserva = Reserva.objects.create(
            professor=self.usuario,
            data=date(2026, 8, 27),
            hora_inicio=time(7, 30),
            hora_fim=time(9),
        )
        ItemReserva.objects.create(reserva=reserva, tipo_dispositivo=self.tipo, quantidade=1)
        self.client.force_login(self.usuario)
        resposta = self.client.get(f"/reservas/{reserva.pk}/editar/")
        self.assertEqual(resposta.status_code, 200)
        opcoes_iniciais = ["07:10", "08:00", "08:50", "09:55"]
        resposta = self.client.post(f"/reservas/{reserva.pk}/editar/", {
            "data": "2026-08-27",
            "horarios": opcoes_iniciais,
            f"tipo_{self.tipo.pk}": "1",
        })
        self.assertRedirects(resposta, "/reservas/")
        reserva.refresh_from_db()
        self.assertEqual((reserva.hora_inicio, reserva.hora_fim), (time(7, 30), time(9)))

    def test_usuario_pode_se_cadastrar_e_entra_automaticamente(self):
        resposta = self.client.post("/cadastro/", {
            "username": "nova-professora",
            "email": "professora@example.com",
            "password1": "Senha-forte-123",
            "password2": "Senha-forte-123",
        })
        self.assertRedirects(resposta, "/")
        self.assertTrue(resposta.wsgi_request.user.is_authenticated)
        self.assertTrue(get_user_model().objects.filter(username="nova-professora").exists())

    def test_dispositivo_pode_ser_cadastrado_sem_patrimonio_e_id(self):
        dispositivo = Dispositivo.objects.create(tipo=self.tipo)
        self.assertIsNone(dispositivo.numero_patrimonio)
        self.assertIsNone(dispositivo.numero_id)

    def test_numero_id_pode_se_repetir_em_tipos_diferentes(self):
        outro_tipo = TipoDispositivo.objects.create(nome="Notebook Laranja")
        Dispositivo.objects.create(tipo=self.tipo, numero_id="10")
        dispositivo = Dispositivo.objects.create(tipo=outro_tipo, numero_id="10")
        self.assertEqual(dispositivo.numero_id, "10")

    def test_numero_id_nao_pode_se_repetir_no_mesmo_tipo(self):
        Dispositivo.objects.create(tipo=self.tipo, numero_id="10")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dispositivo.objects.create(tipo=self.tipo, numero_id="10")

    def test_lista_filtra_por_tipo_e_exporta_planilha(self):
        outro_tipo = TipoDispositivo.objects.create(nome="Tablet")
        Dispositivo.objects.create(tipo=outro_tipo, numero_patrimonio="T-1")
        usuario = self.usuario
        self.client.force_login(usuario)
        lista = self.client.get(f"/dispositivos/?tipo={self.tipo.pk}")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.context["dispositivos"]), 3)
        resposta = self.client.get(f"/dispositivos/exportar/?tipo={self.tipo.pk}")
        self.assertEqual(resposta.status_code, 200)
        workbook = load_workbook(BytesIO(resposta.content))
        valores = list(workbook.active.values)
        self.assertEqual(valores[0], ("Total de dispositivos", 3, None, None, None))
        self.assertEqual(valores[1], ("Total ativo", 3, None, None, None))
        self.assertEqual(valores[2], ("Total inativo", 0, None, None, None))
        self.assertEqual(valores[4], ("Patrimônio", "Tipo", "Categoria", "ID", "Status"))
        self.assertTrue(all(linha[1] == self.tipo.nome for linha in valores[5:]))

    def test_painel_reflete_filtro_de_categoria(self):
        categoria = Categoria.objects.create(nome="Uso em aula")
        dispositivo = Dispositivo.objects.first()
        dispositivo.categoria = categoria
        dispositivo.ativo = False
        dispositivo.save()
        self.client.force_login(self.usuario)
        resposta = self.client.get(f"/dispositivos/?categoria={categoria.pk}")
        self.assertEqual(resposta.context["resumo"], {"total": 1, "ativo": 0, "inativo": 1})

    def test_dashboard_usa_data_atual_por_padrao(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get("/")
        self.assertEqual(resposta.context["data_selecionada"], timezone.localdate())
        self.assertContains(resposta, timezone.localdate().strftime("%d"))

    def test_navbar_nao_exibe_cadastro_de_dispositivo(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get("/")
        self.assertNotContains(resposta, "Cadastrar dispositivo")

    def test_admin_pode_editar_dispositivo_e_usuario_comum_nao(self):
        dispositivo = Dispositivo.objects.first()
        self.client.force_login(self.usuario)
        resposta = self.client.post(f"/dispositivos/{dispositivo.pk}/editar/", {"tipo": self.tipo.pk, "numero_patrimonio": "ALTERADO"})
        self.assertRedirects(resposta, "/")
        self.assertEqual(Dispositivo.objects.get(pk=dispositivo.pk).numero_patrimonio, "P0")
        admin = get_user_model().objects.create_superuser(username="admin", password="senha", email="")
        self.client.force_login(admin)
        resposta = self.client.post(f"/dispositivos/{dispositivo.pk}/editar/", {"tipo": self.tipo.pk, "numero_patrimonio": "ALTERADO"})
        self.assertRedirects(resposta, "/dispositivos/")
        self.assertEqual(Dispositivo.objects.get(pk=dispositivo.pk).numero_patrimonio, "ALTERADO")
