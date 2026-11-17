from django.contrib import admin

from .models import AulaReserva, Categoria, Dispositivo, ItemReserva, Reserva, TipoDispositivo


@admin.register(Categoria, TipoDispositivo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("numero_patrimonio", "tipo", "categoria", "ativo", "observacao")
    list_filter = ("tipo", "categoria", "ativo", "observacao")
    search_fields = ("numero_patrimonio", "numero_id", "comentarios")


class ItemReservaInline(admin.TabularInline):
    model = ItemReserva
    extra = 0


class AulaReservaInline(admin.TabularInline):
    model = AulaReserva
    extra = 0


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("data", "aulas_reservadas", "professor_exibicao")
    list_filter = ("data",)
    inlines = (AulaReservaInline, ItemReservaInline)

    @admin.display(description="Aulas / horário")
    def aulas_reservadas(self, reserva):
        aulas = reserva.aulas_exibicao
        if aulas:
            return ", ".join(aula["nome"] for aula in aulas)
        return f"{reserva.hora_inicio:%H:%M}–{reserva.hora_fim:%H:%M} (legada)"
