# Generated by Django 5.1.3 on 2024-12-13 21:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_alter_customuser_telefono'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='user_type',
            field=models.CharField(choices=[('profesor', 'Profesor'), ('pañolero', 'Pañolero'), ('admin', 'Administrador'), ('auxiliarpañol', 'Auxliar')], max_length=20),
        ),
    ]