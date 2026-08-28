from datetime import time

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CadastroForm, DashboardFilterForm, DispositivoForm, ReservaForm
from .models import Dispositivo, ItemReserva, Reserva
from .services import disponibilidade


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = CadastroForm(request.POST or None)
    if form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Cadastro realizado com sucesso.")
        return redirect("dashboard")
    return render(request, "registration/signup.html", {"form": form})


def dashboard(request):
    form = DashboardFilterForm(request.GET or None)
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
    dispositivos = Dispositivo.objects.select_related("tipo", "categoria")
    return render(request, "reservas/dispositivo_list.html", {"dispositivos": dispositivos})


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
