from django import forms
from .models import Solicitud, DetalleSolicitud, Herramienta, CategoriaHerramienta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Solicitud, ActivoFijo
from django.core.exceptions import ValidationError
from django.utils import timezone
from usuarios.models import CustomUser
from .models import SalaComputacion, Alumno
from django.db.models import Q




class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ['nombres', 'apellidos', 'rut', 'correo']


class SalaComputacionForm(forms.ModelForm):
    class Meta:
        model = SalaComputacion
        fields = [
            'nombre', 
            'descripcion', 
            'capacidad', 
            'estado'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'})
        }

class OcuparSalaForm(forms.Form):
    sala = forms.ModelChoiceField(
        queryset=SalaComputacion.objects.all(),  # Changed to show all rooms
        label="Seleccionar Sala"
    )
    alumnos = forms.ModelMultipleChoiceField(
        queryset=Alumno.objects.all(),
        label="Seleccionar Alumnos",
        widget=forms.CheckboxSelectMultiple
    )


    def clean(self):
        cleaned_data = super().clean()
        sala = cleaned_data.get('sala')
        alumnos = cleaned_data.get('alumnos')

        # Check if sala is valid
        if not sala:
            raise forms.ValidationError("Debe seleccionar una sala.")

        # Check if alumnos is valid
        if not alumnos:
            raise forms.ValidationError("Debe seleccionar al menos un alumno.")

        # Check room capacity
        if sala.capacidad > 0 and len(alumnos) > sala.capacidad:
            raise forms.ValidationError(f"La sala tiene un límite de {sala.capacidad} alumnos.")

        return cleaned_data

class LiberarSalaForm(forms.Form):
    sala = forms.ModelChoiceField(
        queryset=SalaComputacion.objects.filter(estado='ocupada'),
        label="Seleccionar Sala"
    )

class SolicitudFiltroForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Solicitud.ESTADOS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='profesor'),
        required=False,
        label="Profesor",
        widget=forms.Select(attrs={'class': 'form-control'})
    )



class ReportarHerramientaForm(forms.ModelForm):
    class Meta:
        model = Herramienta
        fields = ['nombre', 'descripcion', 'imagen', 'rota']  # Agregar el campo 'rota'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imagen'].required = True


class HerramientaFiltroForm(forms.Form):
    categoria = forms.ModelChoiceField(
        queryset=CategoriaHerramienta.objects.all(), 
        required=False, 
        label='Filtrar por Categoría',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadir la opción predeterminada para el campo `asignatura`
        self.fields['categoria'].empty_label = "--Categorias--"

    busqueda = forms.CharField(
        max_length=100, 
        required=False, 
        label='Buscar Herramienta',
        widget=forms.TextInput(attrs={'placeholder': 'Nombre de herramienta...'})
    )

class DetalleSolicitudForm(forms.ModelForm):
    herramienta = forms.ModelChoiceField(
        queryset=Herramienta.objects.filter(stock_disponible__gt=0),
        label='Seleccionar Herramienta',
        required=False,  # Permitir que sea opcional
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    activo_fijo = forms.ModelChoiceField(
        queryset=ActivoFijo.objects.filter(stock_disponible__gt=0),
        label='Seleccionar Activo Fijo',
        required=False,  # Permitir que sea opcional
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cantidad = forms.IntegerField(
        min_value=1,
        label='Cantidad',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DetalleSolicitud
        fields = ['herramienta', 'activo_fijo', 'cantidad']
        widgets = {
            'herramienta': forms.Select(attrs={'class': 'form-control'}),
            'activo_fijo': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
        }

    def clean(self):
        cleaned_data = super().clean()
        herramienta = cleaned_data.get('herramienta')
        activo_fijo = cleaned_data.get('activo_fijo')
        cantidad = cleaned_data.get('cantidad')

        if not herramienta and not activo_fijo:
            raise forms.ValidationError("Debes seleccionar al menos una herramienta o un activo fijo.")

        if herramienta and cantidad:
            if cantidad > herramienta.stock_disponible:
                self.add_error(
                    'cantidad',
                    f"Solo hay {herramienta.stock_disponible} unidades disponibles de '{herramienta.nombre}'."
                )

        if activo_fijo and cantidad:
            if cantidad > activo_fijo.stock_disponible:
                self.add_error(
                    'cantidad',
                    f"Solo hay {activo_fijo.stock_disponible} unidades disponibles de '{activo_fijo.nombre}'."
                )

        return cleaned_data

# Formset para manejar múltiples herramientas
DetalleSolicitudFormSet = forms.inlineformset_factory(
    Solicitud, 
    DetalleSolicitud, 
    form=DetalleSolicitudForm, 
    extra=0,  # Permite un solo formulario vacío inicial
    can_delete=True,
    max_num=15,  # Máximo de herramientas que se pueden solicitar
    validate_max=True,  # Habilita la validación para el máximo número de formularios
)


def clean(self):
    cleaned_data = super().clean()
    herramienta = cleaned_data.get('herramienta')
    cantidad = cleaned_data.get('cantidad')

    if herramienta and cantidad:
        if cantidad > herramienta.stock_disponible:
            self.add_error(
                'cantidad',
                f"Solo hay {herramienta.stock_disponible} unidades disponibles de '{herramienta.nombre}'."
            )
        
    return cleaned_data


from django.utils.timezone import now

class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = [
            'alumno',
            'fecha_retiro_solicitada',
            'fecha_devolucion_solicitada',
            'observaciones',
            'asignatura',
        ]
        widgets = {
            'fecha_retiro_solicitada': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'min': now().isoformat(),
                    'placeholder': 'Seleccione una fecha de retiro',
                }
            ),
            'fecha_devolucion_solicitada': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'placeholder': 'Seleccione una fecha de devolución',
                }
            ),
            'observaciones': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control',
                    'placeholder': 'Ingrese observaciones adicionales aquí',
                }
            ),
            'asignatura': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.user = user
            if user.user_type == 'pañolero':  # Cambiar aquí para usar user_type
                # Ocultar el campo `asignatura` para pañoleros
                self.fields['asignatura'].required = False
                self.fields['asignatura'].widget = forms.HiddenInput()

    def clean_asignatura(self):
        asignatura = self.cleaned_data.get('asignatura')
        if not asignatura and self.user.user_type != 'pañolero':  # Cambiar aquí para usar user_type
            raise forms.ValidationError("El campo 'Asignatura' es obligatorio para profesores.")
        return asignatura

    def clean(self):
        cleaned_data = super().clean()
        retiro = cleaned_data.get('fecha_retiro_solicitada')
        devolucion = cleaned_data.get('fecha_devolucion_solicitada')

        if retiro and devolucion:
            if retiro < now():
                raise forms.ValidationError({
                    'fecha_retiro_solicitada': 'La fecha de retiro no puede ser en el pasado.'
                })
            if devolucion <= retiro:
                raise forms.ValidationError({
                    'fecha_devolucion_solicitada': 'La fecha de devolución debe ser posterior a la de retiro.'
                })

        return cleaned_data


class SolicitudFiltroForm(forms.Form):
    ESTADO_CHOICES = [
        ('', 'Todos los Estados'),
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
    ]

    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES, 
        required=False, 
        label='Filtrar por Estado'
    )
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Desde'
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Hasta'
    )


class HerramientaForm(forms.ModelForm):
    """
    Formulario para crear y editar herramientas
    """
    categoria = forms.ModelChoiceField(
        queryset=CategoriaHerramienta.objects.all(),
        label='Categoría',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Herramienta
        fields = [
            'nombre', 
            'descripcion', 
            'categoria', 
            'stock_total', 
            'stock_disponible', 
            'codigo', 
            'imagen'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stock_total': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalización de Crispy Forms
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='form-group col-md-6 mb-3'),
                Column('categoria', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            'descripcion',
            Row(
                Column('stock_total', css_class='form-group col-md-4 mb-3'),
                Column('stock_disponible', css_class='form-group col-md-4 mb-3'),
                Column('codigo', css_class='form-group col-md-4 mb-3'),
                css_class='form-row'
            ),
            'imagen',
            Div(
                Submit('submit', 'Guardar Herramienta', css_class='btn btn-primary'),
                css_class='text-center mt-3'
            )
        )

    def clean(self):
        """
        Validaciones personalizadas
        """
        cleaned_data = super().clean()
        stock_total = cleaned_data.get('stock_total', 0)
        stock_disponible = cleaned_data.get('stock_disponible', 0)

        # Validar que el stock disponible no sea mayor al stock total
        if stock_disponible > stock_total:
            raise forms.ValidationError(
                "El stock disponible no puede ser mayor al stock total"
            )

        return cleaned_data

class CategoriaHerramientaForm(forms.ModelForm):
    """
    Formulario para crear y editar categorías de herramientas
    """
    class Meta:
        model = CategoriaHerramienta
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalización de Crispy Forms
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nombre',
            'descripcion',
            Div(
                Submit('submit', 'Guardar Categoría', css_class='btn btn-primary'),
                css_class='text-center mt-3'
            )
        )

class HerramientaBajaForm(forms.Form):
    """
    Formulario para dar de baja una herramienta
    """
    motivo = forms.ChoiceField(
        choices=[
            ('roto', 'Herramienta Rota'),
            ('perdido', 'Herramienta Perdida'),
            ('obsoleto', 'Herramienta Obsoleta'),
            ('otro', 'Otro Motivo')
        ],
        label='Motivo de Baja',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    descripcion = forms.CharField(
        label='Descripción Detallada',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Proporcione detalles adicionales sobre la baja de la herramienta'
        }),
        required=False
    )
    cantidad = forms.IntegerField(
        label='Cantidad a Dar de Baja',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'min': 1
        }),
        min_value=1
    )

    def __init__(self, *args, **kwargs):
        herramienta = kwargs.pop('herramienta', None)
        super().__init__(*args, **kwargs)
        
        if herramienta:
            # Limitar la cantidad máxima a dar de baja
            self.fields['cantidad'].max_value = herramienta.stock_disponible
            self.fields['cantidad'].widget.attrs['max'] = herramienta.stock_disponible

        # Personalización de Crispy Forms
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'motivo',
            'descripcion',
            'cantidad',
            Div(
                Submit('submit', 'Dar de Baja', css_class='btn btn-danger'),
                css_class='text-center mt-3'
            )
        )

    def clean_cantidad(self):
        """
        Validar que la cantidad a dar de baja sea válida
        """
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0")
        return cantidad
    

class ActivoFijoForm(forms.ModelForm):
    class Meta:
        model = ActivoFijo  # Usa el modelo ActivoFijo, no DetalleSolicitud
        fields = [
            'nombre', 'categoria', 'prioridad', 'codigo',
            'fecha_ultimo_mantenimiento', 'fecha_proximo_mantenimiento',
            'stock_total', 'stock_disponible', 'descripcion'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'prioridad': forms.Select(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_ultimo_mantenimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'fecha_proximo_mantenimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'stock_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_disponible': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# Formset para manejar múltiples detalles de solicitud de activos fijos
DetalleSolicitudActivoFijoFormSet = forms.inlineformset_factory(
    Solicitud,  # Modelo padre
    DetalleSolicitud,  # Modelo hijo
    form=DetalleSolicitudForm,  # Usa el formulario DetalleSolicitudForm que ya tienes
    extra=1,  # Número de formularios vacíos adicionales
    can_delete=True,
    max_num=15,
    validate_max=True
)