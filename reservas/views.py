from datetime import time
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DashboardFilterForm, DispositivoFilterForm, DispositivoForm, ReservaForm
from .models import Dispositivo, ItemReserva, Reserva
from .services import disponibilidade


def dashboard(request):
    form_data = request.GET or {"data": timezone.localdate().isoformat()}
    form = DashboardFilterForm(form_data)
    data = None
    hora_inicio, hora_fim = time.min, time.max
    if form.is_valid():
        data = form.cleaned_data.get("data")
        hora_inicio = form.cleaned_data.get("hora_inicio") or time.min
        hora_fim = form.cleaned_data.get("hora_fim") or time.max
        linhas = disponibilidade(data, hora_inicio, hora_fim, form.cleaned_data.get("tipo")) if data else []
        categoria = form.cleaned_data.get("categoria")
        if categoria:
            linhas = [linha for linha in linhas if Dispositivo.objects.filter(tipo=linha["tipo"], categoria=categoria, ativo=True).exists()]
    else:
        linhas = []
    return render(request, "reservas/dashboard.html", {"form": form, "linhas": linhas, "data_selecionada": data})


@login_required
def reserva_list(request):
    reservas = Reserva.objects.select_related("professor").prefetch_related("itens__tipo_dispositivo")
    if not request.user.is_staff:
        reservas = reservas.filter(professor=request.user)
    return render(request, "reservas/reserva_list.html", {"reservas": reservas})


@login_required
def reserva_create(request):
    form = ReservaForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            reserva = form.save(commit=False)
            reserva.professor = request.user
            reserva.save()
            ItemReserva.objects.bulk_create([ItemReserva(reserva=reserva, tipo_dispositivo_id=tipo_id, quantidade=quantidade) for tipo_id, quantidade in form.itens().items()])
        messages.success(request, "Reserva criada com sucesso.")
        return redirect("reserva_list")
    return render(request, "reservas/reserva_form.html", {"form": form, "titulo": "Nova reserva"})


@login_required
def reserva_update(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.professor != request.user and not request.user.is_staff:
        messages.error(request, "Você não pode editar esta reserva.")
        return redirect("reserva_list")
    form = ReservaForm(request.POST or None, instance=reserva)
    if form.is_valid():
        with transaction.atomic():
            reserva = form.save()
            reserva.itens.all().delete()
            ItemReserva.objects.bulk_create([ItemReserva(reserva=reserva, tipo_dispositivo_id=tipo_id, quantidade=quantidade) for tipo_id, quantidade in form.itens().items()])
        messages.success(request, "Reserva atualizada com sucesso.")
        return redirect("reserva_list")
    return render(request, "reservas/reserva_form.html", {"form": form, "titulo": "Editar reserva"})


@login_required
def reserva_delete(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.professor != request.user and not request.user.is_staff:
        messages.error(request, "Você não pode excluir esta reserva.")
        return redirect("reserva_list")
    if request.method == "POST":
        reserva.delete()
        messages.success(request, "Reserva excluída.")
        return redirect("reserva_list")
    return render(request, "reservas/confirm_delete.html", {"objeto": reserva})


@login_required
def dispositivo_list(request):
    form = DispositivoFilterForm(request.GET or None)
    dispositivos = dispositivos_filtrados(form)
    resumo = resumo_dispositivos(dispositivos)
    return render(request, "reservas/dispositivo_list.html", {"dispositivos": dispositivos, "form": form, "resumo": resumo})


def dispositivos_filtrados(form):
    dispositivos = Dispositivo.objects.select_related("tipo", "categoria")
    if form.is_valid():
        if form.cleaned_data.get("tipo"):
            dispositivos = dispositivos.filter(tipo=form.cleaned_data["tipo"])
        if form.cleaned_data.get("categoria"):
            dispositivos = dispositivos.filter(categoria=form.cleaned_data["categoria"])
    return dispositivos


def resumo_dispositivos(dispositivos):
    total = dispositivos.count()
    ativo = dispositivos.filter(ativo=True).count()
    return {"total": total, "ativo": ativo, "inativo": total - ativo}


@login_required
def dispositivo_export(request):
    form = DispositivoFilterForm(request.GET or None)
    dispositivos = dispositivos_filtrados(form)
    resumo = resumo_dispositivos(dispositivos)

    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dispositivos"
    sheet.append(["Total de dispositivos", resumo["total"]])
    sheet.append(["Total ativo", resumo["ativo"]])
    sheet.append(["Total inativo", resumo["inativo"]])
    sheet.append([])
    sheet.append(["Patrimônio", "Tipo", "Categoria", "ID", "Status"])
    for dispositivo in dispositivos:
        sheet.append([
            dispositivo.numero_patrimonio or "",
            dispositivo.tipo.nome,
            dispositivo.categoria.nome if dispositivo.categoria else "",
            dispositivo.numero_id or "",
            "Ativo" if dispositivo.ativo else "Inativo",
        ])
    sheet.freeze_panes = "A6"
    for column in sheet.columns:
        width = max(len(str(cell.value or "")) for cell in column) + 2
        sheet.column_dimensions[column[0].column_letter].width = min(width, 35)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="dispositivos.xlsx"'
    return response


@login_required
def dispositivo_create(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    form = DispositivoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Dispositivo cadastrado.")
        return redirect("dispositivo_list")
    return render(request, "reservas/dispositivo_form.html", {"form": form})


@login_required
def dispositivo_update(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    form = DispositivoForm(request.POST or None, instance=dispositivo)
    if form.is_valid():
        form.save()
        messages.success(request, "Dispositivo atualizado.")
        return redirect("dispositivo_list")
    return render(request, "reservas/dispositivo_form.html", {"form": form, "titulo": "Editar dispositivo"})
