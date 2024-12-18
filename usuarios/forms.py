# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Asignatura
import re
from django.contrib.auth import authenticate
import re
from django.core.exceptions import ValidationError
from django.conf import settings
import os


    
class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['nombre', 'diurno_nocturno']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'diurno_nocturno': forms.Select(attrs={'class': 'form-control'})
        }


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        required=True
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    remember_me = forms.BooleanField(
        label="Mantener sesión iniciada",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise forms.ValidationError("Correo o contraseña incorrectos.")
        return self.cleaned_data
    



class CambiarContrasenaForm(forms.Form):
    contrasena_actual = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Contraseña Actual",
        error_messages={
            'required': 'Por favor ingrese su contraseña actual'
        }
    )
    nueva_contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Nueva Contraseña",
        help_text="""La contraseña debe cumplir con los siguientes requisitos:
        - Mínimo 8 caracteres
        - Al menos una letra mayúscula
        - Al menos un número"""
    )
    confirmar_contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirmar Nueva Contraseña",
        error_messages={
            'required': 'Por favor confirme su nueva contraseña'
        }
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_nueva_contrasena(self):
        nueva_contrasena = self.cleaned_data.get('nueva_contrasena')
        
        # Validación de longitud
        if len(nueva_contrasena) < 8:
            raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        
        # Validación de que no sea solo números
        if nueva_contrasena.isdigit():
            raise forms.ValidationError("La contraseña no puede ser solo números.")
        
        # Validación de mayúsculas
        if not re.search(r'[A-Z]', nueva_contrasena):
            raise forms.ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        
        # Validación de números
        if not re.search(r'\d', nueva_contrasena):
            raise forms.ValidationError("La contraseña debe contener al menos un número.")
        
        return nueva_contrasena

    def clean(self):
        cleaned_data = super().clean()
        nueva_contrasena = cleaned_data.get('nueva_contrasena')
        confirmar_contrasena = cleaned_data.get('confirmar_contrasena')
        contrasena_actual = cleaned_data.get('contrasena_actual')

        # Validar que las contraseñas coincidan
        if nueva_contrasena and confirmar_contrasena and nueva_contrasena != confirmar_contrasena:
            raise forms.ValidationError("Las contraseñas no coinciden.")

        # Validar contraseña actual
        if contrasena_actual and not self.user.check_password(contrasena_actual):
            raise forms.ValidationError("La contraseña actual es incorrecta.")

        return cleaned_data


def validate_file_size(value):
    filesize = value.size
    
    if filesize > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(f"El tamaño máximo del archivo es {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} MB")

def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Formato de imagen no permitido. Formatos válidos: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}")

class ProfesorPerfilForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False, 
        validators=[validate_file_size, validate_file_extension],
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'telefono', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        # Verificar que el email no esté siendo usado por otro usuario
        users = CustomUser.objects.exclude(pk=self.instance.pk)
        if users.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está siendo utilizado.")
        return email

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombres")
    last_name = forms.CharField(max_length=30, required=True, label="Apellidos")
    rut = forms.CharField(max_length=12, required=True, label="RUT")
    telefono = forms.CharField(max_length=12, required=True, label="telefono")
    email = forms.EmailField(required=True, label="Correo Electrónico")
    avatar = forms.ImageField(
        required=False, 
        validators=[validate_file_size, validate_file_extension],
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Mínimo 8 caracteres, incluye al menos 1 mayúscula y 1 número.",
    )
    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, required=True, label="Tipo de Usuario")
    asignaturas = forms.ModelMultipleChoiceField(queryset=Asignatura.objects.all(), required=False, label="Asignaturas", widget=forms.CheckboxSelectMultiple)

    
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'rut','telefono', 'email', 'password1', 'password2', 'user_type','asignaturas','avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el usuario es un profesor, se mostrarán las asignaturas
        if self.instance and self.instance.user_type != 'profesor':
            self.fields['asignaturas'].widget.attrs['CheckboxSelectMultiple'] = 'display:none;'

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe tener al menos una letra mayúscula.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe incluir al menos un número.")
        return password

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[0-9kK]$', rut):
            raise ValidationError("Ingrese un RUT válido (formato: 12.345.678-9).")
        return rut

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        
        # Mostrar campo de asignatura solo si el user_type es 'profesor'
        user_type = cleaned_data.get('user_type')
        asignaturas = cleaned_data.get('asignaturas')

        if user_type == 'profesor' and not asignaturas:
            raise ValidationError("Debe asignar al menos una asignatura al profesor.")

        return cleaned_data


class CustomUserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombres")
    last_name = forms.CharField(max_length=30, required=True, label="Apellidos")
    rut = forms.CharField(max_length=12, required=True, label="RUT")
    telefono = forms.CharField(max_length=12, required=True, label="Telefono")
    email = forms.EmailField(required=True, label="Correo Electrónico", widget=forms.EmailInput(attrs={'readonly': 'readonly'}))
    avatar = forms.ImageField(
        required=False,
        validators=[validate_file_size, validate_file_extension],
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Mínimo 8 caracteres, incluye al menos 1 mayúscula y 1 número.",
    )
    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, required=True, label="Tipo de Usuario")
    asignaturas = forms.ModelMultipleChoiceField(queryset=Asignatura.objects.all(), required=False, label="Asignaturas", widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'rut', 'telefono', 'email', 'password1', 'password2', 'user_type', 'asignaturas', 'avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el usuario es un profesor, se mostrarán las asignaturas
        if self.instance and self.instance.user_type != 'profesor':
            self.fields['asignaturas'].widget.attrs['CheckboxSelectMultiple'] = 'display:none;'

        # Si estamos editando un usuario, hacemos que el correo no sea editable
        if self.instance:
            self.fields['email'].disabled = True

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if password and not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe tener al menos una letra mayúscula.")
        if password and not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe incluir al menos un número.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)  # Cambiar la contraseña del usuario
        if commit:
            user.save()
        return user