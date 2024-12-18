# Generated by Django 5.1.3 on 2024-12-08 17:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0018_salacomputacion_registrousosala'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alumno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombres', models.CharField(max_length=100)),
                ('apellidos', models.CharField(max_length=100)),
                ('rut', models.CharField(max_length=12, unique=True)),
                ('correo', models.EmailField(max_length=254, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='solicitud',
            name='alumno',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.alumno'),
        ),
    ]
