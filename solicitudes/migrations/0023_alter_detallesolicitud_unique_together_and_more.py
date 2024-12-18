# Generated by Django 5.1.3 on 2024-12-11 00:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0022_detalleactivosolicitud'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='detallesolicitud',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='detallesolicitud',
            name='activo_fijo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.activofijo'),
        ),
        migrations.AlterField(
            model_name='detallesolicitud',
            name='herramienta',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.herramienta'),
        ),
        migrations.AlterUniqueTogether(
            name='detallesolicitud',
            unique_together={('solicitud', 'herramienta', 'activo_fijo')},
        ),
        migrations.DeleteModel(
            name='DetalleActivoSolicitud',
        ),
    ]