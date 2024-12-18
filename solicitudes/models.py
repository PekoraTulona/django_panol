from django.db import models
from usuarios.models import CustomUser
from django.utils import timezone
from usuarios.models import Asignatura
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from datetime import timedelta


class Alumno(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    correo = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.rut}"


class ActivoFijo(models.Model):
    PRIORIDAD_CHOICES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ]
    
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(
        'CategoriaHerramienta', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='activos'
    )
    fecha_ultimo_mantenimiento = models.DateField()
    fecha_proximo_mantenimiento = models.DateField()
    descripcion = models.TextField(null=True, blank=True)
    prioridad = models.CharField(
        max_length=10, 
        choices=PRIORIDAD_CHOICES, 
        default='media'
    )
    stock_total = models.PositiveIntegerField(default=10)
    stock_disponible = models.PositiveIntegerField(default=10)
    codigo = models.CharField(max_length=50, unique=True, blank=True, null=True)
    roto = models.BooleanField(default=False)
    reportado_por = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_reporte_roto = models.DateTimeField(null=True, blank=True)

    def calcular_proximo_mantenimiento(self):
        """
        Calcula la próxima fecha de mantenimiento según la prioridad
        """
        if self.prioridad == 'alta':
            return self.fecha_ultimo_mantenimiento + timedelta(days=90)  # Cada 3 meses
        elif self.prioridad == 'media':
            return self.fecha_ultimo_mantenimiento + timedelta(days=180)  # Cada 6 meses
        else:  # baja
            return self.fecha_ultimo_mantenimiento + timedelta(days=365)  # Cada año

    def marcar_como_roto(self, usuario):
        """
        Método para marcar el activo como roto
        """
        self.roto = True
        self.reportado_por = usuario
        self.fecha_reporte_roto = timezone.now()
        self.stock_disponible = 0
        self.save()

    def actualizar_stock(self, cantidad):
        """
        Método para actualizar el stock disponible
        """
        if cantidad <= self.stock_disponible:
            self.stock_disponible -= cantidad
            self.save()
            return True
        return False

    def devolver_al_stock(self, cantidad):
        """
        Método para devolver activos al stock cuando se cancela una solicitud
        """
        if cantidad > 0:
            # Asegurarse de no exceder el stock total
            self.stock_disponible = min(self.stock_disponible + cantidad, self.stock_total)
            self.save()
            return True
        return False

    def __str__(self):
        return self.nombre

class CategoriaHerramienta(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Categorías de Herramientas"

class Herramienta(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey('CategoriaHerramienta', on_delete=models.SET_NULL, null=True, related_name='herramientas')
    stock_total = models.PositiveIntegerField(default=50)
    stock_disponible = models.PositiveIntegerField(default=50)
    codigo = models.CharField(max_length=50, unique=True, blank=True, null=True)
    imagen = models.ImageField(upload_to='herramientas/', blank=True, null=True)
    rota = models.BooleanField(default=False)  # Campo para indicar si la herramienta está rota
    reportado_por = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)  # Quien reportó la herramienta
    fecha_reporte_rota = models.DateTimeField(null=True, blank=True)
    
    def marcar_como_rota(self, usuario):
        """
        Método para marcar la herramienta como rota
        """
        self.rota = True
        self.reportado_por = usuario
        self.fecha_reporte_rota = timezone.now()
        self.save()

    def __str__(self):
        return self.nombre

    def actualizar_stock(self, cantidad):
        """
        Método para actualizar el stock disponible
        """
        if cantidad <= self.stock_disponible:
            self.stock_disponible -= cantidad
            self.save()
            return True
        return False

    def devolver_al_stock(self, cantidad):
        """
        Método para devolver herramientas al stock cuando se cancela una solicitud
        """
        if cantidad > 0:
            # Asegurarse de no exceder el stock total
            self.stock_disponible = min(self.stock_disponible + cantidad, self.stock_total)
            self.save()
            return True
        return False

    class Meta:
        verbose_name_plural = "Herramientas"

class Solicitud(models.Model):
    ESTADOS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='pendiente')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.SET_NULL, null=True)
    # Nuevos campos de fecha
    fecha_retiro_solicitada = models.DateTimeField(null=True, blank=True)
    fecha_devolucion_solicitada = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Solicitud {self.id} - {self.usuario.username}"

    def duracion_prestamo(self):
        """
        Calcula la duración del préstamo si ya se ha realizado
        """
        if self.fecha_retiro_real and self.fecha_devolucion_real:
            return self.fecha_devolucion_real - self.fecha_retiro_real
        return None

    def is_overdue(self):
        """
        Verifica si la solicitud está vencida
        """
        if self.fecha_devolucion_solicitada and timezone.now() > self.fecha_devolucion_solicitada:
            return True
        return False

    def calcular_total_herramientas(self):
        """
        Calcula el total de herramientas en la solicitud
        """
        return sum(detalle.cantidad for detalle in self.detalles.filter(herramienta__isnull=False)) + \
           sum(detalle.cantidad for detalle in self.detalles.filter(activo_fijo__isnull=False))

    def get_estado_color(self):
        """
        Devuelve una clase de color para el estado
        """
        colores = {
            'pendiente': 'warning',
            'aprobada': 'success',
            'rechazada': 'danger',
            'en_proceso': 'info',
            'completada': 'primary',
            'cancelado': 'secondary',
        }
        return colores.get(self.estado, 'secondary')

    class Meta:
        verbose_name_plural = "Solicitudes"

class DetalleSolicitud(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='detalles')
    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE, null=True, blank=True)
    activo_fijo = models.ForeignKey(ActivoFijo, on_delete=models.CASCADE, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        if self.herramienta:
            return f"{self.cantidad} x {self.herramienta.nombre}"
        elif self.activo_fijo:
            return f"{self.cantidad} x {self.activo_fijo.nombre}"
        return "Detalle vacío"

    def save(self, *args, **kwargs):
        """
        Validar disponibilidad al guardar
        """
        if self.herramienta:
            if self.cantidad <= self.herramienta.stock_disponible:
                super().save(*args, **kwargs)
            else:
                raise ValueError("Cantidad solicitada supera el stock disponible para la herramienta")
        elif self.activo_fijo:
            if self.cantidad <= self.activo_fijo.stock_disponible:
                super().save(*args, **kwargs)
            else:
                raise ValueError("Cantidad solicitada supera el stock disponible para el activo fijo")
        else:
            raise ValueError("Debe seleccionar al menos una herramienta o un activo fijo")

    class Meta:
        verbose_name_plural = "Detalles de Solicitudes"
        unique_together = ['solicitud', 'herramienta', 'activo_fijo']  # Evitar duplicados

class ReporteHerramienta(models.Model):
    TIPO_REPORTE_CHOICES = [
        ('consumida', 'Herramienta Consumida'),
        ('rota', 'Herramienta Rota'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('rechazado', 'Rechazado')
    ]

    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE, related_name='reportes')
    profesor = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tipo_reporte = models.CharField(max_length=20, choices=TIPO_REPORTE_CHOICES)
    cantidad = models.PositiveIntegerField(default=1)
    fecha_reporte = models.DateTimeField(default=timezone.now)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    imagen = models.ImageField(upload_to='reportes_herramientas/', null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"Reporte de {self.herramienta.nombre} - {self.get_tipo_reporte_display()}"

    def clean(self):
        # Validaciones antes de guardar
        if self.tipo_reporte == 'consumida' and self.cantidad > self.herramienta.stock_disponible:
            raise ValidationError(f"La cantidad ({self.cantidad}) supera el stock disponible ({self.herramienta.stock_disponible})")

    def save(self, *args, **kwargs):
        # Realizar validaciones
        self.full_clean()
        
        # Si el reporte ya está confirmado, actualizar la herramienta
        if self.estado == 'confirmado':
            self.actualizar_herramienta()
        
        super().save(*args, **kwargs)

    def actualizar_herramienta(self):
        herramienta = self.herramienta
        
        # Evitar actualizaciones múltiples
        if herramienta.reportes.filter(estado='confirmado', tipo_reporte=self.tipo_reporte).exists():
            return
        
        try:
            with transaction.atomic():
                if self.tipo_reporte == 'consumida':
                    # Reducir el stock disponible y total
                    herramienta.stock_total = max(0, herramienta.stock_total - self.cantidad)
                    herramienta.stock_disponible = max(0, herramienta.stock_disponible - self.cantidad)
                    
                elif self.tipo_reporte == 'rota':
                    # Marcar como rota y reducir el stock total y disponible
                    if not herramienta.rota:
                        herramienta.rota = True
                        herramienta.stock_total = max(0, herramienta.stock_total - self.cantidad)
                        herramienta.stock_disponible = max(0, herramienta.stock_disponible - self.cantidad)
                        herramienta.reportado_por = self.profesor
                        herramienta.fecha_reporte_rota = timezone.now()

                herramienta.save()
        except Exception as e:
            # Manejar cualquier error durante la actualización
            raise ValidationError(f"Error al actualizar la herramienta: {str(e)}")

    def confirmar(self):
        """
        Método para confirmar un reporte
        """
        if self.estado != 'pendiente':
            raise ValidationError("Solo se pueden confirmar reportes pendientes")
        
        self.estado = 'confirmado'
        self.save()

    def rechazar(self):
        """
        Método para rechazar un reporte
        """
        if self.estado != 'pendiente':
            raise ValidationError("Solo se pueden rechazar reportes pendientes")
        
        self.estado = 'rechazado'
        self.save()


class SalaComputacion(models.Model):
    ESTADO_CHOICES = [
        ('libre', 'Libre'),
        ('ocupada', 'Ocupada'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    capacidad = models.PositiveIntegerField(default=0)
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='libre'
    )
    
    # Campos para seguimiento de uso actual
    alumno_actual = models.ForeignKey(
        Alumno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    hora_inicio = models.DateTimeField(null=True, blank=True)
    hora_fin_prevista = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.nombre
    
    def ocupar_sala(self, alumno, duracion_horas=1):
        """
        Método para ocupar la sala
        """
        if self.estado == 'libre':
            self.estado = 'ocupada'
            self.alumno_actual = alumno
            self.hora_inicio = timezone.now()
            self.hora_fin_prevista = timezone.now() + timezone.timedelta(hours=duracion_horas)
            self.save()
            return True
        return False
    
    def liberar_sala(self):
        """
        Método para liberar la sala
        """
        if self.estado == 'ocupada':
            self.estado = 'libre'
            self.alumno_actual = None
            self.hora_inicio = None
            self.hora_fin_prevista = None
            self.save()
            return True
        return False
    
    def get_estado_color(self):
        """
        Devuelve un color para el estado de la sala
        """
        colores = {
            'libre': 'success',
            'ocupada': 'danger'
        }
        return colores.get(self.estado, 'secondary')
    
    class Meta:
        verbose_name_plural = "Salas de Computación"

class RegistroUsoSala(models.Model):
    sala = models.ForeignKey(SalaComputacion, on_delete=models.CASCADE)
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    hora_inicio = models.DateTimeField(auto_now_add=True)
    hora_fin = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.sala.nombre} - {self.alumno.nombres} {self.alumno.apellidos}"
    
    def finalizar_uso(self):
        """
        Método para finalizar el uso de la sala
        """
        self.hora_fin = timezone.now()
        self.save()
    
    class Meta:
        verbose_name_plural = "Registros de Uso de Salas"
