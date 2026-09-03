from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reservas/", views.reserva_list, name="reserva_list"),
    path("reservas/nova/", views.reserva_create, name="reserva_create"),
    path("reservas/<int:pk>/editar/", views.reserva_update, name="reserva_update"),
    path("reservas/<int:pk>/excluir/", views.reserva_delete, name="reserva_delete"),
    path("dispositivos/", views.dispositivo_list, name="dispositivo_list"),
    path("dispositivos/exportar/", views.dispositivo_export, name="dispositivo_export"),
    path("dispositivos/novo/", views.dispositivo_create, name="dispositivo_create"),
    path("dispositivos/<int:pk>/editar/", views.dispositivo_update, name="dispositivo_update"),
] 
