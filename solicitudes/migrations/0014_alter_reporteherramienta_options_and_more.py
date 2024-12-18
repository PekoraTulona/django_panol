# Generated by Django 5.1.3 on 2024-12-04 01:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0013_reporteherramienta'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reporteherramienta',
            options={'ordering': ['-fecha_reporte']},
        ),
        migrations.AddField(
            model_name='reporteherramienta',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('confirmado', 'Confirmado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=20),
        ),
    ]
