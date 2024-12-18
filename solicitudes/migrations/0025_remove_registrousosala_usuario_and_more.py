# Generated by Django 5.1.3 on 2024-12-14 19:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0024_solicitud_profesor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registrousosala',
            name='usuario',
        ),
        migrations.RemoveField(
            model_name='salacomputacion',
            name='usuario_actual',
        ),
        migrations.AddField(
            model_name='registrousosala',
            name='alumno',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='solicitudes.alumno'),
        ),
        migrations.AddField(
            model_name='salacomputacion',
            name='alumno_actual',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='solicitudes.alumno'),
        ),
    ]