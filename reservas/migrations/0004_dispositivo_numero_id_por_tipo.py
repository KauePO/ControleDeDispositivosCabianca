from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reservas", "0003_alter_dispositivo_numero_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispositivo",
            name="numero_id",
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddConstraint(
            model_name="dispositivo",
            constraint=models.UniqueConstraint(
                fields=("tipo", "numero_id"),
                name="dispositivo_id_unico_por_tipo",
            ),
        ),
    ]