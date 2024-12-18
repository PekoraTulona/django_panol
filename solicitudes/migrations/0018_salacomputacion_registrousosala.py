# Generated by Django 5.1.3 on 2024-12-07 19:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0017_activofijo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SalaComputacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('capacidad', models.PositiveIntegerField(default=0)),
                ('estado', models.CharField(choices=[('libre', 'Libre'), ('ocupada', 'Ocupada')], default='libre', max_length=20)),
                ('hora_inicio', models.DateTimeField(blank=True, null=True)),
                ('hora_fin_prevista', models.DateTimeField(blank=True, null=True)),
                ('usuario_actual', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Salas de Computación',
            },
        ),
        migrations.CreateModel(
            name='RegistroUsoSala',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hora_inicio', models.DateTimeField(auto_now_add=True)),
                ('hora_fin', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('sala', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solicitudes.salacomputacion')),
            ],
            options={
                'verbose_name_plural': 'Registros de Uso de Salas',
            },
        ),
    ]
