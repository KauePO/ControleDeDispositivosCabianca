from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Dispositivo, ItemReserva, Reserva, TipoDispositivo
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
