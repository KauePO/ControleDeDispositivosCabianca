from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from openpyxl import load_workbook

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
