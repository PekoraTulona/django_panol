# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import os, re

def validate_avatar_size(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError('El archivo de imagen no debe superar los 5 MB.')

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('profesor', 'Profesor'),
        ('pañolero', 'Pañolero'),
        ('admin', 'Administrador'),
        ('auxiliarpañol', 'Auxliar'),
    ]

    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        default='avatars/default.png',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif']),
            validate_avatar_size
        ]
    )
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Lógica para manejar el avatar por defecto
        if not self.avatar:
            self.avatar = 'avatars/default.png'
        
        # Si hay un avatar existente y se sube uno nuevo, eliminar el anterior
        try:
            old_instance = CustomUser.objects.get(pk=self.pk)
            if old_instance.avatar and old_instance.avatar != self.avatar:
                try:
                    os.remove(old_instance.avatar.path)
                except Exception as e:
                    print(f"Error al eliminar avatar antiguo: {e}")
        except CustomUser.DoesNotExist:
            pass

        super().save(*args, **kwargs)

    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    asignaturas = models.ManyToManyField('Asignatura', blank=True, related_name="profesores")

    username = None

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['rut', 'first_name', 'last_name', 'user_type']  

    def __str__(self):
        return f"{self.email} ({self.user_type})"
    
    def cambiar_contrasena(self, nueva_contrasena):
        """
        Método para cambiar la contraseña de forma segura
        """
        self.set_password(nueva_contrasena)
        self.save()

    def get_solicitudes(self):
        from solicitudes.models import Solicitud
        return Solicitud.objects.filter(usuario=self)

    def tiene_solicitudes(self):
        from solicitudes.models import Solicitud
        return Solicitud.objects.filter(usuario=self).exists()
    
    def cambiar_contrasena(self, contrasena_actual, nueva_contrasena):
        # Verificar contraseña actual
        if not self.check_password(contrasena_actual):
            raise ValidationError("La contraseña actual es incorrecta.")
        
        # Validar la nueva contraseña
        self.validar_contrasena(nueva_contrasena)
        
        # Establecer la nueva contraseña
        self.set_password(nueva_contrasena)
        self.save()

    def validar_contrasena(self, contrasena):
        # Validación de longitud
        if len(contrasena) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        
        # Validación de que no sea solo números
        if contrasena.isdigit():
            raise ValidationError("La contraseña no puede ser solo números.")
        
        # Validación de mayúsculas
        if not re.search(r'[A-Z]', contrasena):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        
        # Validación de números
        if not re.search(r'\d', contrasena):
            raise ValidationError("La contraseña debe contener al menos un número.")
    
    @property
    def profesor_solicitudes(self):
        from solicitudes.models import Solicitud
        if self.user_type == 'profesor':
            return Solicitud.objects.filter(usuario=self)
        return None


class Asignatura(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    diurno_nocturno = models.CharField(
        max_length=10,
        choices=[('Diurno', 'Diurno'), ('Nocturno', 'Nocturno')],
        default='Diurno'
    )

    def __str__(self):
        return self.nombre
    


