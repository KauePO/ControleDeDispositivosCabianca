from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class TipoDispositivo(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "tipo de dispositivo"
        verbose_name_plural = "tipos de dispositivo"

    def __str__(self):
        return self.nome


class Dispositivo(models.Model):
    tipo = models.ForeignKey(TipoDispositivo, on_delete=models.PROTECT, related_name="dispositivos")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="dispositivos")
    numero_patrimonio = models.CharField(max_length=80, unique=True, blank=True, null=True)
    numero_id = models.CharField(max_length=80, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo__nome", "numero_patrimonio"]
        constraints = [
            models.UniqueConstraint(fields=["tipo", "numero_id"], name="dispositivo_id_unico_por_tipo"),
        ]
        verbose_name = "dispositivo"
        verbose_name_plural = "dispositivos"

    def __str__(self):
        identificacao = self.numero_patrimonio or self.numero_id or "sem identificação"
        return f"{self.tipo} ({identificacao})"


class Reserva(models.Model):
    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservas")
    nome_professor = models.CharField(max_length=150, blank=True)
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["data", "hora_inicio"]
        constraints = [models.CheckConstraint(condition=models.Q(hora_inicio__lt=models.F("hora_fim")), name="reserva_horario_valido")]
        verbose_name = "reserva"
        verbose_name_plural = "reservas"

    def clean(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValidationError({"hora_fim": "O horário final deve ser posterior ao inicial."})

    @property
    def professor_exibicao(self):
        return self.nome_professor or self.professor.get_full_name() or self.professor.username

    def __str__(self):
        return f"{self.data:%d/%m/%Y} - {self.professor_exibicao}"


class ItemReserva(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="itens")
    tipo_dispositivo = models.ForeignKey(TipoDispositivo, on_delete=models.PROTECT, related_name="itens_reserva")
    quantidade = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reserva", "tipo_dispositivo"], name="item_tipo_unico_por_reserva"),
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="item_quantidade_positiva"),
        ]
        verbose_name = "item de reserva"
        verbose_name_plural = "itens de reserva"
