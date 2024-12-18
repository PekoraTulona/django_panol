# Generated by Django 5.1.3 on 2024-12-03 20:55

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0012_herramienta_reportado_por_herramienta_rota_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReporteHerramienta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_reporte', models.CharField(choices=[('consumida', 'Herramienta Consumida'), ('rota', 'Herramienta Rota')], max_length=20)),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('fecha_reporte', models.DateTimeField(default=django.utils.timezone.now)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('herramienta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to='solicitudes.herramienta')),
                ('profesor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
