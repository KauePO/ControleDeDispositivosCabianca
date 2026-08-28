from django.db.models import Sum

from .models import Dispositivo, ItemReserva, Reserva, TipoDispositivo


def reservas_sobrepostas(data, hora_inicio, hora_fim, reserva_id=None):
    query = Reserva.objects.filter(
        data=data,
        hora_inicio__lt=hora_fim,
        hora_fim__gt=hora_inicio,
    )
    if reserva_id:
        query = query.exclude(pk=reserva_id)
    return query


def disponibilidade(data, hora_inicio, hora_fim, tipo=None, reserva_id=None):
    tipos = TipoDispositivo.objects.all()
    if tipo:
        tipos = tipos.filter(pk=tipo.pk if hasattr(tipo, "pk") else tipo)
    ids_reservas = reservas_sobrepostas(data, hora_inicio, hora_fim, reserva_id).values("pk")
    resultado = []
    for item in tipos:
        total = Dispositivo.objects.filter(tipo=item, ativo=True).count()
        reservado = ItemReserva.objects.filter(reserva_id__in=ids_reservas, tipo_dispositivo=item).aggregate(total=Sum("quantidade"))["total"] or 0
        resultado.append({"tipo": item, "total": total, "reservado": reservado, "disponivel": total - reservado})
    return resultado


def validar_itens(data, hora_inicio, hora_fim, itens, reserva_id=None):
    if hora_inicio >= hora_fim:
        return {"__all__": "O horário final deve ser posterior ao inicial."}
    erros = {}
    for tipo_id, quantidade in itens.items():
        if quantidade <= 0:
            continue
        tipo = TipoDispositivo.objects.get(pk=tipo_id)
        linha = disponibilidade(data, hora_inicio, hora_fim, tipo, reserva_id)[0]
        if quantidade > linha["disponivel"]:
            erros[str(tipo_id)] = f"{tipo.nome}: restam {linha['disponivel']} dispositivo(s) neste período."
    return erros
