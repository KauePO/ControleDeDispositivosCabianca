from django.db.models import Count, Q, Sum

from .horarios import AULAS_POR_NUMERO
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


def reservas_que_ocupam_aulas(data, numeros_aulas, reserva_id=None):
    condicao = Q()
    for numero in numeros_aulas:
        aula = AULAS_POR_NUMERO[numero]
        condicao |= Q(aulas__numero_aula=numero) | Q(
            aulas__isnull=True,
            hora_inicio__lt=aula["fim"],
            hora_fim__gt=aula["inicio"],
        )
    query = Reserva.objects.filter(data=data).filter(condicao).distinct()
    if reserva_id:
        query = query.exclude(pk=reserva_id)
    return query


def disponibilidade(data, hora_inicio, hora_fim, tipo=None, reserva_id=None, aulas=None):
    tipos = TipoDispositivo.objects.all()
    if tipo:
        tipos = tipos.filter(pk=tipo.pk if hasattr(tipo, "pk") else tipo)
    tipos = list(tipos)
    tipo_ids = [item.pk for item in tipos]
    totais = dict(
        Dispositivo.objects.filter(ativo=True, tipo_id__in=tipo_ids)
        .values_list("tipo_id")
        .annotate(total=Count("pk"))
    )

    reservados = {}
    if aulas:
        for numero in aulas:
            reservas = reservas_que_ocupam_aulas(data, [numero], reserva_id).values("pk")
            por_tipo = ItemReserva.objects.filter(reserva_id__in=reservas, tipo_dispositivo_id__in=tipo_ids)
            por_tipo = dict(por_tipo.values_list("tipo_dispositivo_id").annotate(total=Sum("quantidade")))
            for tipo_id, quantidade in por_tipo.items():
                reservados[tipo_id] = max(reservados.get(tipo_id, 0), quantidade)
    else:
        ids_reservas = reservas_sobrepostas(data, hora_inicio, hora_fim, reserva_id).values("pk")
        reservados = dict(
            ItemReserva.objects.filter(reserva_id__in=ids_reservas, tipo_dispositivo_id__in=tipo_ids)
            .values_list("tipo_dispositivo_id")
            .annotate(total=Sum("quantidade"))
        )

    resultado = []
    for item in tipos:
        total = totais.get(item.pk, 0)
        reservado = reservados.get(item.pk, 0)
        resultado.append({"tipo": item, "total": total, "reservado": reservado, "disponivel": total - reservado})
    return resultado


def validar_itens(data, hora_inicio, hora_fim, itens, reserva_id=None, aulas=None):
    if hora_inicio >= hora_fim:
        return {"__all__": "O horário final deve ser posterior ao inicial."}
    erros = {}
    for tipo_id, quantidade in itens.items():
        if quantidade <= 0:
            continue
        tipo = TipoDispositivo.objects.get(pk=tipo_id)
        linha = disponibilidade(data, hora_inicio, hora_fim, tipo, reserva_id, aulas)[0]
        if quantidade > linha["disponivel"]:
            erros[str(tipo_id)] = f"{tipo.nome}: restam {linha['disponivel']} dispositivo(s) neste período."
    return erros
