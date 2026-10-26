from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("reservas", "0004_dispositivo_numero_id_por_tipo"),
    ]

    operations = [
        migrations.CreateModel(
            name="AulaReserva",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero_aula", models.PositiveSmallIntegerField(choices=[(1, "1ª aula · 07:10–08:00"), (2, "2ª aula · 08:00–08:50"), (3, "3ª aula · 08:50–09:40"), (4, "4ª aula · 09:55–10:45"), (5, "5ª aula · 10:45–11:35"), (6, "6ª aula · 11:35–12:25"), (7, "7ª aula · 13:30–14:20"), (8, "8ª aula · 14:20–15:10"), (9, "9ª aula · 15:10–16:00")])),
                ("reserva", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aulas", to="reservas.reserva")),
            ],
            options={
                "verbose_name": "aula reservada",
                "verbose_name_plural": "aulas reservadas",
                "ordering": ["numero_aula"],
            },
        ),
        migrations.AddConstraint(
            model_name="aulareserva",
            constraint=models.UniqueConstraint(fields=("reserva", "numero_aula"), name="aula_unica_por_reserva"),
        ),
    ]