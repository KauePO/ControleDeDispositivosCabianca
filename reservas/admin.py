from django.contrib import admin

from .models import Categoria, Dispositivo, ItemReserva, Reserva, TipoDispositivo


@admin.register(Categoria, TipoDispositivo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("numero_patrimonio", "tipo", "categoria", "ativo")
    list_filter = ("tipo", "categoria", "ativo")
    search_fields = ("numero_patrimonio", "numero_id")


class ItemReservaInline(admin.TabularInline):
    model = ItemReserva
    extra = 0


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("data", "hora_inicio", "hora_fim", "professor_exibicao")
    list_filter = ("data",)
    inlines = (ItemReservaInline,)
