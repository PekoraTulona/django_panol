# Generated by Django 5.1.3 on 2024-12-04 03:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0014_alter_reporteherramienta_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporteherramienta',
            name='imagen',
            field=models.ImageField(blank=True, null=True, upload_to='reportes_herramientas/'),
        ),
    ]
