# Generated by Django 5.1.3 on 2024-12-07 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0016_herramienta_fecha_reporte_rota'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivoFijo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('tipo', models.CharField(max_length=50)),
                ('fecha_ultimo_mantenimiento', models.DateField()),
                ('fecha_proximo_mantenimiento', models.DateField()),
                ('descripcion', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
