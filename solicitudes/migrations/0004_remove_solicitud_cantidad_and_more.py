# Generated by Django 5.1.3 on 2024-11-30 19:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0003_remove_solicitud_fecha_devolucion_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='solicitud',
            name='cantidad',
        ),
        migrations.RemoveField(
            model_name='solicitud',
            name='herramienta',
        ),
    ]
