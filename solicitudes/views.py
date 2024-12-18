from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from usuarios.models import CustomUser, Asignatura
from .models import Herramienta, CategoriaHerramienta, ActivoFijo, Alumno
from .forms import SolicitudForm, HerramientaFiltroForm, DetalleSolicitudFormSet, CategoriaHerramientaForm, HerramientaForm, DetalleSolicitud, ActivoFijoForm, SolicitudFiltroForm, SalaComputacionForm
from .models import Solicitud, ReporteHerramienta
from django.utils import timezone
from django.db.models.functions import TruncMonth
from django.db.models import Count, Sum, Q
from reportlab.lib.pagesizes import A3, A4, letter, landscape
from django.db import transaction
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from .models import SalaComputacion, RegistroUsoSala
from .forms import OcuparSalaForm, LiberarSalaForm, AlumnoForm
from django.views.decorators.http import require_GET
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO

import io
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, 
    Table, 
    TableStyle, 
    Paragraph, 
    Spacer, 
    Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.db.models import Count, Value
from django.db.models.functions import Coalesce
from reportlab.platypus import PageBreak
from django.http import JsonResponse
import json
import logging

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@csrf_exempt  # Temporal para depuración, luego cambia a csrf_protect
@require_POST
def actualizar_mantenimiento(request, activo_id):
    try:
        # Parsear el JSON de la solicitud
        data = json.loads(request.body)
        nueva_fecha = data.get('nueva_fecha_mantenimiento')
        prioridad = data.get('prioridad')  # Opcional, si quieres actualizar la prioridad

        logger.info(f"Solicitud recibida para actualizar mantenimiento - Activo ID: {activo_id}")
        logger.info(f"Nueva fecha: {nueva_fecha}")

        # Validar que la fecha no esté vacía
        if not nueva_fecha:
            logger.error("Fecha de mantenimiento no proporcionada")
            return JsonResponse({
                'success': False, 
                'error': 'Fecha de mantenimiento no proporcionada'
            }, status=400)

        # Obtener el activo por ID
        try:
            activo = ActivoFijo.objects.get(id=activo_id)
        except ActivoFijo.DoesNotExist:
            logger.error(f"Activo con ID {activo_id} no encontrado")
            return JsonResponse({
                'success': False, 
                'error': 'Activo no encontrado'
            }, status=404)

        # Convertir la fecha
        try:
            fecha_mantenimiento = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Formato de fecha inválido: {nueva_fecha}")
            return JsonResponse({
                'success': False, 
                'error': 'Formato de fecha inválido'
            }, status=400)

        # Actualizar prioridad si se proporciona
        if prioridad and prioridad in ['alta', 'media', 'baja']:
            activo.prioridad = prioridad

        # Actualizar fechas de mantenimiento
        activo.fecha_ultimo_mantenimiento = fecha_mantenimiento
        activo.fecha_proximo_mantenimiento = activo.calcular_proximo_mantenimiento()
        
        activo.save()

        logger.info(f"Mantenimiento actualizado para activo {activo_id}")
        return JsonResponse({
            'success': True,
            'mensaje': 'Fecha de mantenimiento actualizada exitosamente',
            'prioridad': activo.prioridad,
            'proximo_mantenimiento': activo.fecha_proximo_mantenimiento.strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

def listar_activos(request):
    activos = ActivoFijo.objects.all()

    # Filtros por nombre y mes
    nombre = request.GET.get('nombre', '')
    mes = request.GET.get('mes', '')
    if nombre:
        activos = activos.filter(nombre__icontains=nombre)
    if mes:
        activos = activos.filter(fecha_proximo_mantenimiento__month=mes)

    return render(request, 'dashboards/panol/activos/listar.html', {'activos': activos})

def crear_activo(request):
    if request.method == 'POST':
        form = ActivoFijoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_activos')
    else:
        form = ActivoFijoForm()
    return render(request, 'dashboards/panol/activos/crear.html', {'form': form})

def editar_activo(request, pk):
    activo = get_object_or_404(ActivoFijo, pk=pk)
    if request.method == 'POST':
        form = ActivoFijoForm(request.POST, instance=activo)
        if form.is_valid():
            form.save()
            return redirect('listar_activos')
    else:
        form = ActivoFijoForm(instance=activo)
    return render(request, 'dashboards/panol/activos/editar.html', {'form': form})

def eliminar_activo(request, pk):
    activo = get_object_or_404(ActivoFijo, pk=pk)
    activo.delete()
    return redirect('listar_activos')


@login_required
def lista_reportes_herramientas(request):
    # Obtener parámetros de filtro para reportes
    filtro_tipo = request.GET.get('tipo_reporte', '')
    filtro_herramienta = request.GET.get('herramienta', '')
    filtro_profesor = request.GET.get('profesor', '')
    filtro_fecha_inicio = request.GET.get('fecha_inicio', '')
    filtro_fecha_fin = request.GET.get('fecha_fin', '')

    # Obtener parámetros de filtro para herramientas rotas
    filtro_herramienta_rota = request.GET.get('herramienta_rota', '')
    filtro_tipo_reporte_rota = request.GET.get('tipo_reporte_rota', '')
    filtro_fecha_inicio_rota = request.GET.get('fecha_inicio_rota', '')
    filtro_fecha_fin_rota = request.GET.get('fecha_fin_rota', '')

    try:
        # Filtrar reportes pendientes
        reportes_pendientes = ReporteHerramienta.objects.filter(estado='pendiente')
        
        # Filtrar reportes completados (no pendientes)
        reportes_completados = ReporteHerramienta.objects.exclude(estado='pendiente')

        # Aplicar filtros a reportes
        if filtro_tipo:
            reportes_pendientes = reportes_pendientes.filter(tipo_reporte=filtro_tipo)
            reportes_completados = reportes_completados.filter(tipo_reporte=filtro_tipo)
        
        if filtro_herramienta:
            reportes_pendientes = reportes_pendientes.filter(herramienta__nombre__icontains=filtro_herramienta)
            reportes_completados = reportes_completados.filter(herramienta__nombre__icontains=filtro_herramienta)
        
        if filtro_profesor:
            reportes_pendientes = reportes_pendientes.filter(
                Q(profesor__first_name__icontains=filtro_profesor) | 
                Q(profesor__last_name__icontains=filtro_profesor)
            )
            reportes_completados = reportes_completados.filter(
                Q(profesor__first_name__icontains=filtro_profesor) | 
                Q(profesor__last_name__icontains=filtro_profesor)
            )

        if filtro_fecha_inicio:
            reportes_pendientes = reportes_pendientes.filter(fecha_reporte__gte=filtro_fecha_inicio)
            reportes_completados = reportes_completados.filter(fecha_reporte__gte=filtro_fecha_inicio)

        if filtro_fecha_fin:
            reportes_pendientes = reportes_pendientes.filter(fecha_reporte__lte=filtro_fecha_fin)
            reportes_completados = reportes_completados.filter(fecha_reporte__lte=filtro_fecha_fin)

        # Obtener herramientas rotas
        herramientas_rotas = Herramienta.objects.filter(rota=True)

        # Aplicar filtros a herramientas rotas
        if filtro_herramienta_rota:
            herramientas_rotas = herramientas_rotas.filter(nombre__icontains=filtro_herramienta_rota)

        if filtro_tipo_reporte_rota:
            herramientas_rotas = herramientas_rotas.filter(reportes__tipo_reporte=filtro_tipo_reporte_rota).distinct()

        if filtro_fecha_inicio_rota:
            herramientas_rotas = herramientas_rotas.filter(reportes__fecha_reporte__gte=filtro_fecha_inicio_rota)

        if filtro_fecha_fin_rota:
            herramientas_rotas = herramientas_rotas.filter(reportes__fecha_reporte__lte=filtro_fecha_fin_rota)

        # Preparar contexto
        context = {
            'reportes_pendientes': reportes_pendientes,
            'reportes_completados': reportes_completados,
            'herramientas_rotas': herramientas_rotas,
            'tipos_reporte': ReporteHerramienta.TIPO_REPORTE_CHOICES,
            'estados_reporte': ReporteHerramienta.ESTADO_CHOICES,
            'filtro_tipo': filtro_tipo,
            'filtro_herramienta': filtro_herramienta,
            'filtro_profesor': filtro_profesor,
            'filtro_fecha_inicio': filtro_fecha_inicio,
            'filtro_fecha_fin': filtro_fecha_fin,
            'filtro_herramienta_rota': filtro_herramienta_rota,
            'filtro_tipo_reporte_rota': filtro_tipo_reporte_rota,
            'filtro_fecha_inicio_rota': filtro_fecha_inicio_rota,
            'filtro_fecha_fin_rota': filtro_fecha_fin_rota,
        }

        return render(request, 'dashboards/panol/lista_reportes_herramientas.html', context)

    except Exception as e:
        print(f"Error al obtener reportes: {e}")
        return render(request, 'dashboards/panol/lista_reportes_herramientas.html', {
            'error': str(e)
        })

@login_required
def detalle_reporte_herramienta(request, reporte_id):
    reporte = get_object_or_404(ReporteHerramienta, id=reporte_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        try:
            with transaction.atomic():
                if accion == 'confirmar':
                    # Verificar si el reporte ya ha sido confirmado
                    if reporte.estado == 'confirmado':
                        messages.warning(request, 'Este reporte ya ha sido confirmado')
                        return redirect('lista_reportes_herramientas')
                    
                    # Confirmar el reporte
                    reporte.confirmar()
                    messages.success(request, 'Reporte confirmado exitosamente')
                
                elif accion == 'rechazar':
                    # Marcar reporte como rechazado
                    reporte.rechazar()
                    messages.warning(request, 'Reporte rechazado')
                
                return redirect('lista_reportes_herramientas')
        
        except Exception as e:
            messages.error(request, f'Error al procesar el reporte: {str(e)}')
            return redirect('lista_reportes_herramientas')

    # Si no es POST, mostrar detalles del reporte
    context = {
        'reporte': reporte
    }

    return render(request, 'dashboards/panol/detalle_reporte_herramienta.html', context)


@login_required
def generar_pdf_reportes_herramientas(request):
    # Obtener filtros
    filtro_tipo = request.GET.get('tipo_reporte', '')
    filtro_herramienta = request.GET.get('herramienta', '')
    filtro_estado = request.GET.get('estado', 'pendiente')
    filtro_herramienta_rota = request.GET.get('herramienta_rota', '')
    filtro_tipo_reporte_rota = request.GET.get('tipo_reporte_rota', '')

    reportes = ReporteHerramienta.objects.all()
    if filtro_tipo:
        reportes = reportes.filter(tipo_reporte=filtro_tipo)
    if filtro_herramienta:
        reportes = reportes.filter(herramienta__nombre__icontains=filtro_herramienta)
    if filtro_estado:
        reportes = reportes.filter(estado=filtro_estado)

    herramientas_rotas = Herramienta.objects.filter(rota=True)
    if filtro_herramienta_rota:
        herramientas_rotas = herramientas_rotas.filter(nombre__icontains=filtro_herramienta_rota)
    if filtro_tipo_reporte_rota:
        herramientas_rotas = herramientas_rotas.filter(reportes__tipo_reporte=filtro_tipo_reporte_rota).distinct()

    # Crear respuesta y documento PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reportes_herramientas.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)

    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']

    # Agregar logo (opcional)
    try:
        logo_path = 'usuarios/static/images/Logotipo_Inacap.png'  # Cambiar por la ruta del logo
        elements.append(Image(logo_path, width=100, height=50))
    except:
        pass

    # Título principal
    elements.append(Paragraph("Reporte de Herramientas", title_style))

    # Crear tabla de reportes
    data_reportes = [['Herramienta', 'Tipo', 'Cantidad', 'Profesor', 'Fecha', 'Estado']]
    for reporte in reportes:
        data_reportes.append([
            reporte.herramienta.nombre,
            reporte.get_tipo_reporte_display(),
            str(reporte.cantidad),
            f"{reporte.profesor.first_name} {reporte.profesor.last_name}",
            reporte.fecha_reporte.strftime('%d/%m/%Y'),
            reporte.get_estado_display()
        ])
    tabla_reportes = crear_tabla(data_reportes)
    elements.append(tabla_reportes)

    # Salto de página y herramientas rotas
    elements.append(PageBreak())
    elements.append(Paragraph("Herramientas Rotas", title_style))
    data_herramientas_rotas = [['Nombre', 'Código', 'Categoría', 'Reportado Por', 'Fecha']]
    for herramienta in herramientas_rotas:
        ultimo_reporte = herramienta.reportes.last()
        data_herramientas_rotas.append([
            herramienta.nombre,
            herramienta.codigo,
            herramienta.categoria.nombre if herramienta.categoria else "N/A",
            ultimo_reporte.profesor.get_full_name() if ultimo_reporte else "Desconocido",
            ultimo_reporte.fecha_reporte.strftime('%d/%m/%Y') if ultimo_reporte else "N/A"
        ])
    tabla_herramientas_rotas = crear_tabla(data_herramientas_rotas)
    elements.append(tabla_herramientas_rotas)

    # Construir PDF
    doc.build(elements)
    return response

def crear_tabla(data):
    """Crea una tabla con estilos aplicados."""
    tabla = Table(data)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    return tabla


@login_required
def reportar_herramienta(request):
    if request.method == 'POST':
        # Depuración: imprimir todos los datos del POST
        print("Datos recibidos en el POST:")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        
        # Imprimir archivos recibidos
        print("Archivos recibidos:")
        for key, value in request.FILES.items():
            print(f"{key}: {value}")

        herramienta_id = request.POST.get('herramienta_id')
        tipo_reporte = request.POST.get('tipo_reporte')
        imagen = request.FILES.get('imagen')
        
        try:
            # Convertir cantidad a entero con validación
            cantidad = int(request.POST.get('cantidad', 1))
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        except ValueError as e:
            print(f"Error de cantidad: {e}")
            messages.error(request, 'Cantidad inválida')
            return redirect('estadisticas_profesor')

        observaciones = request.POST.get('observaciones', '')

        try:
            # Obtener la herramienta
            herramienta = Herramienta.objects.get(id=herramienta_id)
            
            # Depuración de la herramienta
            print(f"Herramienta encontrada: {herramienta.nombre}")
            print(f"Stock disponible: {herramienta.stock_disponible}")

            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                # Crear el reporte
                try:
                    reporte = ReporteHerramienta.objects.create(
                        herramienta=herramienta,
                        profesor=request.user,
                        tipo_reporte=tipo_reporte,
                        cantidad=cantidad,
                        observaciones=observaciones,
                        imagen=imagen
                    )
                    
                    # Depuración del reporte creado
                    print(f"Reporte creado exitosamente:")
                    print(f"ID: {reporte.id}")
                    print(f"Tipo: {reporte.tipo_reporte}")
                    print(f"Cantidad: {reporte.cantidad}")
                    print(f"Estado: {reporte.estado}")

                    messages.success(request, 'Reporte de herramienta registrado exitosamente')
                    return redirect('estadisticas_profesor')
                
                except ValidationError as ve:
                    # Capturar errores de validación específicos
                    print(f"Error de validación: {ve}")
                    messages.error(request, f'Error de validación: {ve}')
                except Exception as e:
                    # Capturar cualquier otro error
                    print(f"Error al crear reporte: {e}")
                    messages.error(request, f'Error al crear reporte: {str(e)}')
        
        except Herramienta.DoesNotExist:
            print(f"Herramienta con ID {herramienta_id} no encontrada")
            messages.error(request, 'Herramienta no encontrada')
        
        return redirect('estadisticas_profesor')

    # Si no es POST, renderizar el formulario
    herramientas = Herramienta.objects.filter(stock_disponible__gt=0)
    return render(request, 'dashboards/profe/reportar_herramienta.html', {'herramientas': herramientas})




def get_grouped_concat(queryset, field):
    # Filtra valores no nulos y convierte a cadena
    valores_unicos = queryset.values_list(field, flat=True).distinct()
    valores_filtrados = [str(valor) for valor in valores_unicos if valor is not None]
    
    return Coalesce(
        Value(','.join(valores_filtrados) if valores_filtrados else ''),
        Value('')
    )
# En tu vista, modificarías la consulta así:
solicitudes = Solicitud.objects.all()
profesores_solicitudes = solicitudes.values(
    'usuario__first_name', 
    'usuario__last_name'
).annotate(
    total_solicitudes=Count('id'),
    asignaturas=get_grouped_concat(solicitudes, 'asignatura__nombre')
).order_by('-total_solicitudes')

@login_required
def estadisticas_panol(request):
    # Filtros de búsqueda
    estado = request.GET.get('estado')
    profesor_id = request.GET.get('profesor')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Consulta base de solicitudes con select_related para optimizar
    solicitudes = Solicitud.objects.select_related(
        'usuario', 
        'asignatura'
    ).prefetch_related(
        'detalles__herramienta', 
        'detalles__activo_fijo'  # Añadir prefetch para activos fijos
    )
    
    # Aplicar filtros
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    if profesor_id:
        solicitudes = solicitudes.filter(usuario_id=profesor_id)
    
    if fecha_inicio and fecha_fin:
        solicitudes = solicitudes.filter(
            created_at__range=[fecha_inicio, fecha_fin]
        )
    
    # Preparar datos para la tabla
    datos_solicitudes = []
    for solicitud in solicitudes:
        # Obtener detalles de herramientas y activos fijos
        detalles_items = []
        for detalle in solicitud.detalles.all():
            if detalle.herramienta:
                detalles_items.append(
                    f"{detalle.cantidad} x {detalle.herramienta.nombre} (Herramienta)"
                )
            elif detalle.activo_fijo:
                detalles_items.append(
                    f"{detalle.cantidad} x {detalle.activo_fijo.nombre} (Activo Fijo)"
                )
            else:
                detalles_items.append(f"{detalle.cantidad} x Sin item")
        
        datos_solicitudes.append({
            'id': solicitud.id,
            'profesor': f"{solicitud.usuario.first_name} {solicitud.usuario.last_name}",
            'profesor_id': solicitud.usuario.id,
            'asignatura': solicitud.asignatura.nombre if solicitud.asignatura else 'Sin asignatura',
            'estado': solicitud.get_estado_display(),
            'estado_color': solicitud.get_estado_color(),
            'fecha_creacion': solicitud.created_at,
            'items': ', '.join(detalles_items),
            'observaciones': solicitud.observaciones or 'Sin observaciones'
        })
    
    # Obtener lista de profesores para el filtro
    profesores = CustomUser.objects.filter(
        id__in=Solicitud.objects.values_list('usuario_id', flat=True).distinct()
    )
    
    # Estadísticas generales
    estadisticas = {
        'total_solicitudes': solicitudes.count(),
        'solicitudes_por_estado': solicitudes.values('estado').annotate(
            total=Count('id')
        ).order_by('-total')
    }
    
    # Renderizar template
    context = {
        'solicitudes': datos_solicitudes,
        'estadisticas': estadisticas,
        'estados_choices': Solicitud.ESTADOS_CHOICES,
        'profesores': profesores,
        'filtros': {
            'estado': estado,
            'profesor_id': int(profesor_id) if profesor_id else None,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
    }
    
    return render(request, 'dashboards/admin/estadisticas_panol.html', context)


@login_required
def lista_solicitudes(request):
    # Usar el campo correcto según el error
    solicitudes = Solicitud.objects.filter(usuario=request.user).order_by('-created_at')
    
    # Filtros opcionales
    estado = request.GET.get('estado')
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    # Paginación
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(solicitudes, 10)  # 10 solicitudes por página
    
    page = request.GET.get('page')
    try:
        solicitudes_paginadas = paginator.page(page)
    except PageNotAnInteger:
        solicitudes_paginadas = paginator.page(1)
    except EmptyPage:
        solicitudes_paginadas = paginator.page(paginator.num_pages)
    
    # Preparar contexto
    context = {
        'solicitudes': solicitudes_paginadas,
        'estados': Solicitud.ESTADOS_CHOICES,  # Asegúrate de que este campo exista
    }
    
    return render(request, 'dashboards/profe/lista_solicitudes.html', context)

@login_required
def detalle_solicitud(request, solicitud_id):
    from django.shortcuts import get_object_or_404
    
    solicitud = get_object_or_404(Solicitud, id=solicitud_id, usuario=request.user)
    
    # Obtener los detalles de la solicitud
    detalles = solicitud.detalles.all()
    
    context = {
        'solicitud': solicitud,
        'detalles': detalles,
    }
    
    return render(request, 'dashboards/profe/detalle_solicitud.html', context)


@login_required
def crear_solicitud(request):
    # Validación de permisos
    if request.user.user_type != 'profesor':
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')

    # Filtrado de herramientas y activos fijos disponibles
    herramientas = Herramienta.objects.filter(stock_disponible__gt=0)
    activos_fijos = ActivoFijo.objects.filter(stock_disponible__gt=0)
    categorias = CategoriaHerramienta.objects.all()
    
    # Manejo del filtro de herramientas
    filtro_form = HerramientaFiltroForm(request.GET)
    if filtro_form.is_valid():
        categoria = filtro_form.cleaned_data['categoria']
        busqueda = filtro_form.cleaned_data['busqueda']

        if categoria:
            herramientas = herramientas.filter(categoria=categoria)
        
        if busqueda:
            herramientas = herramientas.filter(nombre__icontains=busqueda)

    if request.method == 'POST':
        solicitud_form = SolicitudForm(request.POST, user=request.user)
        detalle_formset = DetalleSolicitudFormSet(request.POST)

        # Validación general del formulario
        if solicitud_form.is_valid():
            # Cambio en la validación de detalles
            detalles_validos = [
                form 
                for form in detalle_formset 
                if form.is_valid() and (
                    form.cleaned_data.get('herramienta') or 
                    form.cleaned_data.get('activo_fijo')
                )
            ]

            if not detalles_validos:
                messages.error(request, 'Debe seleccionar al menos una herramienta o un activo fijo.')
                context = _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form)
                return render(request, 'dashboards/profe/crear_solicitud.html', context)

            # Validación de formset
            if detalle_formset.is_valid():
                try:
                    # Iniciar transacción para garantizar consistencia
                    with transaction.atomic():
                        # Guardar solicitud
                        solicitud = solicitud_form.save(commit=False)
                        solicitud.usuario = request.user
                        solicitud.save()

                        # Guardar y procesar detalles de solicitud
                        for form in detalle_formset:
                            if form.is_valid() and (form.cleaned_data.get('herramienta') or form.cleaned_data.get('activo_fijo')):
                                detalle = form.save(commit=False)
                                detalle.solicitud = solicitud
                                
                                # Validar y actualizar stock de herramientas
                                if detalle.herramienta:
                                    _validar_y_actualizar_stock(detalle.herramienta, detalle.cantidad)
                                
                                # Validar y actualizar stock de activos fijos
                                if detalle.activo_fijo:
                                    _validar_y_actualizar_stock(detalle.activo_fijo, detalle.cantidad)
                                
                                detalle.save()

                        messages.success(request, 'Solicitud creada exitosamente')
                        return redirect('lista_solicitudes')

                except ValidationError as e:
                    messages.error(request, str(e))
                    context = _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form)
                    return render(request, 'dashboards/profe/crear_solicitud.html', context)

            else:
                # Mostrar errores del formset
                messages.error(request, 'Por favor, corrija los errores en los detalles de la solicitud.')
                context = _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form)
                return render(request, 'dashboards/profe/crear_solicitud.html', context)

        else:
            # Mostrar errores del formulario de solicitud
            messages.error(request, 'Por favor, corrija los errores en el formulario.')
            context = _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form)
            return render(request, 'dashboards/profe/crear_solicitud.html', context)

    else:
        # Inicializar formularios para GET
        solicitud_form = SolicitudForm(user=request.user)
        detalle_formset = DetalleSolicitudFormSet()

    # Preparar contexto para renderizar
    context = _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form)
    return render(request, 'dashboards/profe/crear_solicitud.html', context)

def _preparar_contexto(solicitud_form, detalle_formset, herramientas, activos_fijos, categorias, filtro_form):
    """Función auxiliar para preparar el contexto"""
    return {
        'solicitud_form': solicitud_form,
        'detalle_formset': detalle_formset,
        'herramientas': herramientas,
        'activos_fijos': activos_fijos,
        'categorias': categorias,
        'filtro_form': filtro_form,
    }

def _validar_y_actualizar_stock(item, cantidad):
    """Función auxiliar para validar y actualizar stock"""
    if item.stock_disponible < cantidad:
        raise ValidationError(f'Stock insuficiente para {item.nombre}')
    
    item.stock_disponible -= cantidad
    item.save()



@transaction.atomic
def cancelar_solicitud(request, solicitud_id):
    try:
        solicitud = Solicitud.objects.get(id=solicitud_id)
        
        if solicitud.estado != 'pendiente':
            messages.error(request, "Solo se pueden cancelar solicitudes pendientes.")
            return redirect('lista_solicitudes')
        
        # Devolver las herramientas al stock
        for detalle in solicitud.detalles.all():
            herramienta = detalle.herramienta
            herramienta.devolver_al_stock(detalle.cantidad)
        
        # Cambiar el estado de la solicitud
        solicitud.estado = 'cancelada'
        solicitud.save()
        
        messages.success(request, "Solicitud cancelada y herramientas devueltas al stock.")
        return redirect('lista_solicitudes')
    
    except Solicitud.DoesNotExist:
        messages.error(request, "Solicitud no encontrada.")
        return redirect('lista_solicitudes')
    except Exception as e:
        messages.error(request, f"Error al cancelar la solicitud: {str(e)}")
        return redirect('lista_solicitudes')


@login_required
def estadisticas_profesor(request):
    # Verificar si el usuario es profesor
    if request.user.user_type != 'profesor':
        messages.error(request, "Acceso denegado. Solo profesores pueden ver estas estadísticas.")
        return redirect('pagina_principal')  # Cambia esto a tu URL de página principal

    try:
        # Convertir parámetros a tipos apropiados
        año = int(request.GET.get('año', timezone.now().year))
        mes = int(request.GET.get('mes', timezone.now().month))
        asignatura_id = request.GET.get('asignatura')

        # Filtrar solicitudes del profesor
        solicitudes = Solicitud.objects.filter(usuario=request.user)

        # Aplicar filtros
        if año:
            solicitudes = solicitudes.filter(created_at__year=año)
        if mes:
            solicitudes = solicitudes.filter(created_at__month=mes)
        if asignatura_id:
            solicitudes = solicitudes.filter(asignatura_id=asignatura_id)

        # Estadísticas
        total_solicitudes = solicitudes.count()
        solicitudes_aprobadas = solicitudes.filter(estado='aprobada').count()
        solicitudes_pendientes = solicitudes.filter(estado='pendiente').count()
        solicitudes_rechazadas = solicitudes.filter(estado='rechazada').count()

        # Solicitudes por asignatura
        solicitudes_por_asignatura = solicitudes.values('asignatura__nombre') \
            .annotate(total=Count('id')) \
            .order_by('-total')

        # Solicitudes por mes
        solicitudes_por_mes = solicitudes.annotate(mes=TruncMonth('created_at')) \
            .values('mes') \
            .annotate(total=Count('id')) \
            .order_by('mes')

        # Preparar datos para gráficos
        datos_asignaturas = {
            'labels': [item['asignatura__nombre'] for item in solicitudes_por_asignatura] or ['Sin datos'],
            'data': [item['total'] for item in solicitudes_por_asignatura] or [0]
        }

        datos_meses = {
            'labels': [item['mes'].strftime('%B %Y') for item in solicitudes_por_mes] or ['Sin datos'],
            'data': [item['total'] for item in solicitudes_por_mes] or [0]
        }

        # Crear lista de años
        años = list(range(2020, timezone.now().year + 2))

        # Crear lista de meses con nombres
        from calendar import month_name
        meses = [
            {'numero': i, 'nombre': month_name[i]} 
            for i in range(1, 13)
        ]

        # Contexto para la plantilla
        context = {
            'total_solicitudes': total_solicitudes,
            'solicitudes_aprobadas': solicitudes_aprobadas,
            'solicitudes_pendientes': solicitudes_pendientes,
            'solicitudes_rechazadas': solicitudes_rechazadas,
            'datos_asignaturas': datos_asignaturas,
            'datos_meses': datos_meses,
            'asignaturas': request.user.asignaturas.all(),
            'año_actual': año,
            'años': años,
            'meses': meses,
            'mes_actual': mes,
            'asignatura_seleccionada': asignatura_id
        }

        return render(request, 'dashboards/profe/estadisticas_profesor.html', context)

    except Exception as e:
        # Manejo de errores
        messages.error(request, f"Ocurrió un error al generar las estadísticas: {str(e)}")
        return redirect('dashboard_profesor')
    

@login_required
def administrar_herramientas(request):
    herramientas = Herramienta.objects.all()
    
    # Procesar el formulario de filtro
    filtro_form = HerramientaFiltroForm(request.GET or None)
    if filtro_form.is_valid():
        categoria = filtro_form.cleaned_data.get('categoria')
        busqueda = filtro_form.cleaned_data.get('busqueda')

        if categoria:
            herramientas = herramientas.filter(categoria=categoria)
        if busqueda:
            herramientas = herramientas.filter(nombre__icontains=busqueda)

    return render(request, 'dashboards/panol/administrar_herramientas.html', {
        'herramientas': herramientas,
        'filtro_form': filtro_form,
    })

@login_required
def agregar_herramienta(request):
    if request.method == 'POST':
        form = HerramientaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Herramienta agregada exitosamente.')
            return redirect('administrar_herramientas')
    else:
        form = HerramientaForm()
    return render(request, 'dashboards/panol/agregar_herramienta.html', {'form': form})

@login_required
def editar_herramienta(request, pk):
    herramienta = get_object_or_404(Herramienta, pk=pk)
    if request.method == 'POST':
        form = HerramientaForm(request.POST, request.FILES, instance=herramienta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Herramienta actualizada exitosamente.')
            return redirect('administrar_herramientas')
    else:
        form = HerramientaForm(instance=herramienta)
    return render(request, 'dashboards/panol/editar_herramienta.html', {'form': form, 'herramienta': herramienta})

@login_required
def eliminar_herramienta(request, pk):
    herramienta = get_object_or_404(Herramienta, pk=pk)
    if request.method == 'POST':
        herramienta.delete()
        messages.success(request, 'Herramienta eliminada exitosamente.')
        return redirect('administrar_herramientas')
    return render(request, 'dashboards/panol/eliminar_herramienta.html', {'herramienta': herramienta})

@login_required
def administrar_categorias(request):
    categorias = CategoriaHerramienta.objects.all()
    return render(request, 'dashboards/panol/administrar_categorias.html', {'categorias': categorias})

@login_required
def agregar_categoria(request):
    if request.method == 'POST':
        form = CategoriaHerramientaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría agregada exitosamente.')
            return redirect('administrar_categorias')
    else:
        form = CategoriaHerramientaForm()
    return render(request, 'dashboards/panol/agregar_categoria.html', {'form': form})

@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaHerramienta, pk=pk)
    if request.method == 'POST':
        form = CategoriaHerramientaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada exitosamente.')
            return redirect('administrar_categorias')
    else:
        form = CategoriaHerramientaForm(instance=categoria)
    return render(request, 'dashboards/panol/editar_categoria.html', {'form': form, 'categoria': categoria})

@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaHerramienta, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada exitosamente.')
        return redirect('administrar_categorias')
    return render(request, 'dashboards/panol/eliminar_categoria.html', {'categoria': categoria})




@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def lista_solicitudes_panol(request):
    # Obtener todas las solicitudes
    solicitudes = Solicitud.objects.all().order_by('-created_at')
    
    # Inicializar el formulario de filtro
    form = SolicitudFiltroForm(request.GET or None)
    
    # Aplicar filtros si el formulario es válido
    if form.is_valid():
        # Filtro por fecha de inicio
        if form.cleaned_data.get('fecha_inicio'):
            solicitudes = solicitudes.filter(
                created_at__date__gte=form.cleaned_data['fecha_inicio']
            )
        
        # Filtro por fecha de fin
        if form.cleaned_data.get('fecha_fin'):
            solicitudes = solicitudes.filter(
                created_at__date__lte=form.cleaned_data['fecha_fin']
            )
        
        # Filtro por estado
        if form.cleaned_data.get('estado'):
            solicitudes = solicitudes.filter(
                estado=form.cleaned_data['estado']
            )
        
        # Filtro por usuario
        if form.cleaned_data.get('usuario'):
            solicitudes = solicitudes.filter(
                usuario=form.cleaned_data['usuario']
            )
    
    context = {
        'solicitudes': solicitudes,
        'form': form
    }
    
    return render(request, 'dashboards/panol/lista_solicitudes.html', context)


def generar_pdf_solicitud(request, solicitud_id):
    # Obtener la solicitud
    solicitud = Solicitud.objects.get(id=solicitud_id)
    
    # Crear un buffer para el PDF
    buffer = BytesIO()
    
    # Crear el PDF con márgenes
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Lista para almacenar elementos del PDF
    elementos = []
    
    # Título principal
    titulo = Paragraph(f"Detalles de Solicitud #{solicitud.id}", styles['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))  # Espacio entre el título y el contenido
    
    # Información del usuario
    info_usuario = [
        ["Información del Solicitante"],
        ["Nombre:", solicitud.usuario.get_full_name()],
        ["Tipo de usuario:", solicitud.usuario.user_type],
        ["Email:", solicitud.usuario.email],
        ["Asignatura:", solicitud.asignatura.nombre if solicitud.asignatura else "No especificada"],
        ["Correo de alumno:", solicitud.alumno.correo if solicitud.alumno else "No especificada"],
    ]
    tabla_usuario = Table(info_usuario, colWidths=[200, 300])
    tabla_usuario.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla_usuario)
    elementos.append(Spacer(1, 12))
    
    # Información de la solicitud
    info_solicitud = [
        ["Información de la Solicitud"],
        ["Estado:", solicitud.get_estado_display()],
        ["Fecha de Creación:", solicitud.created_at.strftime("%d/%m/%Y %H:%M")],
        ["Fecha de Retiro Solicitada:", 
         solicitud.fecha_retiro_solicitada.strftime("%d/%m/%Y %H:%M") 
         if solicitud.fecha_retiro_solicitada else "No especificada"],
        ["Fecha de Devolución Solicitada:", 
         solicitud.fecha_devolucion_solicitada.strftime("%d/%m/%Y %H:%M") 
         if solicitud.fecha_devolucion_solicitada else "No especificada"],
    ]
    tabla_solicitud = Table(info_solicitud, colWidths=[200, 300])
    tabla_solicitud.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla_solicitud)
    elementos.append(Spacer(1, 12))
    
    # Tabla de herramientas
    # Tabla de herramientas
    # Tabla de herramientas
    datos_herramientas = [["Herramienta/Activo Fijo", "Cantidad", "Código"]]
    for detalle in solicitud.detalles.all():
        if detalle.herramienta:
            nombre_herramienta = detalle.herramienta.nombre
            codigo_herramienta = detalle.herramienta.codigo if detalle.herramienta.codigo else "Sin código"
        elif detalle.activo_fijo:
            nombre_herramienta = detalle.activo_fijo.nombre
            codigo_herramienta = detalle.activo_fijo.codigo
        else:
            nombre_herramienta = "Herramienta/Activo Fijo no especificado"
            codigo_herramienta = "Sin código"
        datos_herramientas.append([
            nombre_herramienta,
            str(detalle.cantidad),
            codigo_herramienta
        ])
    tabla_herramientas = Table(datos_herramientas, colWidths=[300, 100, 150])
    tabla_herramientas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(Paragraph("Detalle de Herramientas", styles['Heading2']))
    elementos.append(tabla_herramientas)
    elementos.append(Spacer(1, 12))
    
    # Observaciones
    if solicitud.observaciones:
        elementos.append(Paragraph("Observaciones:", styles['Heading3']))
        observaciones = Paragraph(solicitud.observaciones, styles['BodyText'])
        elementos.append(observaciones)
        elementos.append(Spacer(1, 12))
    
    # Construir PDF
    doc.build(elementos)
    
    # Preparar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=solicitud_{solicitud.id}.pdf"
    
    return response

def generar_pdf_todas_solicitudes(request):
    # Filtros opcionales desde parámetros GET
    estado = request.GET.get('estado')  # Filtro por estado
    fecha_inicio = request.GET.get('fecha_inicio')  # Filtro por fecha de inicio
    fecha_fin = request.GET.get('fecha_fin')  # Filtro por fecha de fin

    # Obtener las solicitudes
    solicitudes = Solicitud.objects.all()

    # Aplicar filtros
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    if fecha_inicio:
        solicitudes = solicitudes.filter(created_at__gte=fecha_inicio)
    if fecha_fin:
        solicitudes = solicitudes.filter(created_at__lte=fecha_fin)


    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A3),
                        rightMargin=50, leftMargin=50, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Lista para almacenar elementos del PDF
    elementos = []

    # Título principal
    titulo = Paragraph("Reporte Completo de Solicitudes", styles['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    # Agregar información de filtros aplicados
    filtros_usados = []
    if estado:
        filtros_usados.append(f"Estado: {dict(Solicitud.ESTADOS_CHOICES).get(estado, estado)}")
    if fecha_inicio:
        filtros_usados.append(f"Fecha de inicio: {fecha_inicio}")
    if fecha_fin:
        filtros_usados.append(f"Fecha de fin: {fecha_fin}")

    if filtros_usados:
        filtros_texto = " | ".join(filtros_usados)
        elementos.append(Paragraph(f"Filtros aplicados: {filtros_texto}", styles['BodyText']))
        elementos.append(Spacer(1, 12))

    # Encabezado de la tabla
    datos = [["ID", "Solicitante", "Estado", "Tipo de usuario", "Fecha Creación", "Fecha Retiro", "Fecha Devolución"]]

    # Agregar las solicitudes a la tabla
    for solicitud in solicitudes:
        datos.append([
            str(solicitud.id),
            solicitud.usuario.get_full_name(),
            solicitud.get_estado_display(),
            solicitud.usuario.user_type,
            solicitud.created_at.strftime("%d/%m/%Y %H:%M"),
            solicitud.fecha_retiro_solicitada.strftime("%d/%m/%Y %H:%M") if solicitud.fecha_retiro_solicitada else "No especificada",
            solicitud.fecha_devolucion_solicitada.strftime("%d/%m/%Y %H:%M") if solicitud.fecha_devolucion_solicitada else "No especificada",
        ])

    # Crear la tabla
    tabla = Table(datos, colWidths=[50, 200, 90, 100, 110, 110, 110])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))

    # Agregar la tabla al documento
    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # Construir PDF
    doc.build(elementos)

    # Preparar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=todas_solicitudes.pdf"

    return response


@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def gestionar_salas(request):
    # Obtener todas las salas
    salas = SalaComputacion.objects.all()
    
    # Formulario para ocupar sala
    form_ocupar = OcuparSalaForm()
    
    # Formulario para liberar sala
    form_liberar = LiberarSalaForm()
    
    # Procesar formulario de ocupar sala
    if request.method == 'POST' and 'ocupar_sala' in request.POST:
        form_ocupar = OcuparSalaForm(request.POST)
        if form_ocupar.is_valid():
            sala = form_ocupar.cleaned_data['sala']
            alumnos = form_ocupar.cleaned_data['alumnos']
            duracion = form_ocupar.cleaned_data['duracion']
            
            # Verificar disponibilidad de la sala
            if sala.estado == 'libre':
                # Cambiar estado de la sala
                sala.estado = 'ocupada'
                sala.hora_inicio = timezone.now()
                sala.hora_fin_prevista = timezone.now() + timezone.timedelta(hours=duracion)
                sala.save()
            
            # Crear registros de uso para cada alumno
            registros = []
            for alumno in alumnos:
                registro = RegistroUsoSala.objects.create(
                    sala=sala,
                    alumno=alumno
                )
                registros.append(registro)
            
            messages.success(request, f'Sala {sala.nombre} ocupada por {len(alumnos)} alumno(s).')
            return redirect('gestionar_salas')
        else:
            # Si hay errores en el formulario, mostrarlos
            for error in form_ocupar.errors.values():
                messages.error(request, error)
    
    # Procesar formulario de liberar sala
    if request.method == 'POST' and 'liberar_sala' in request.POST:
        form_liberar = LiberarSalaForm(request.POST)
        if form_liberar.is_valid():
            sala = form_liberar.cleaned_data['sala']
            
            # Buscar registros de uso sin finalizar
            registros = RegistroUsoSala.objects.filter(
                sala=sala,
                hora_fin__isnull=True
            )
            
            # Finalizar registros
            for registro in registros:
                registro.hora_fin = timezone.now()
                registro.save()
            
            # Liberar sala
            sala.estado = 'libre'
            sala.alumno_actual = None
            sala.hora_inicio = None
            sala.hora_fin_prevista = None
            sala.save()
            
            messages.success(request, f'Sala {sala.nombre} liberada exitosamente.')
            return redirect('gestionar_salas')
    
    context = {
        'salas': salas,
        'form_ocupar': form_ocupar,
        'form_liberar': form_liberar,
    }
    
    return render(request, 'dashboards/panol/gestionar_salas.html', context)

# Vista para listar historial de uso de salas
@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def historial_salas(request):
    # Obtener registros de uso de salas
    registros = RegistroUsoSala.objects.all().order_by('-hora_inicio')
    
    context = {
        'registros': registros,
    }
    
    return render(request, 'dashboards/panol/historial_salas.html', context)

# Vista para mostrar detalles de una sala específica
@login_required
@user_passes_test(lambda u: u.user_type in ['pañolero', 'admin'])
def detalle_sala(request, sala_id):
    """
    Vista para mostrar detalles de una sala específica
    """
    sala = get_object_or_404(SalaComputacion, id=sala_id)
    
    # Obtener registros recientes de uso de la sala
    registros_recientes = RegistroUsoSala.objects.filter(
        sala=sala
    ).order_by('-hora_inicio')[:10]
    
    # Obtener alumnos actuales en la sala
    alumnos_actuales = [registro.alumno for registro in registros_recientes if registro.hora_fin is None]
    
    context = {
        'sala': sala,
        'registros_recientes': registros_recientes,
        'alumnos_actuales': alumnos_actuales
    }
    
    return render(request, 'dashboards/panol/detalle_sala.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def crear_sala(request):
    """
    Vista para crear una nueva sala de computación
    """
    if request.method == 'POST':
        form = SalaComputacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala creada exitosamente.')
            return redirect('gestionar_salas')
    else:
        form = SalaComputacionForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Nueva Sala'
    }
    
    return render(request, 'dashboards/panol/form_sala.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def editar_sala(request, sala_id):
    """
    Vista para editar una sala de computación existente
    """
    sala = get_object_or_404(SalaComputacion, id=sala_id)
    
    if request.method == 'POST':
        form = SalaComputacionForm(request.POST, instance=sala)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala actualizada exitosamente.')
            return redirect('gestionar_salas')
    else:
        form = SalaComputacionForm(instance=sala)
    
    context = {
        'form': form,
        'titulo': f'Editar Sala {sala.nombre}',
        'sala': sala
    }
    
    return render(request, 'dashboards/panol/form_sala.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == 'pañolero')
def eliminar_sala(request, sala_id):
    """
    Vista para eliminar una sala de computación
    """
    sala = get_object_or_404(SalaComputacion, id=sala_id)
    
    if request.method == 'POST':
        # Verificar que la sala esté libre antes de eliminar
        if sala.estado == 'libre':
            sala.delete()
            messages.success(request, 'Sala eliminada exitosamente.')
            return redirect('gestionar_salas')
        else:
            messages.error(request, 'No se puede eliminar una sala ocupada.')
    
    context = {
        'sala': sala
    }
    
    return render(request, 'dashboards/panol/confirmar_eliminar.html', context)



from django.shortcuts import get_object_or_404


@login_required
def crear_solicitud_panolero(request):
    # Verificar si el usuario es un 'Pañolero' por el campo 'user_type'
    if request.user.user_type != 'pañolero':
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')  # Redirigir a la página de inicio o la que corresponda

    # Filtro de herramientas y activos fijos
    herramientas = Herramienta.objects.filter(stock_disponible__gt=0)
    activos_fijos = ActivoFijo.objects.filter(stock_disponible__gt=0)

    # Categorías para filtro lateral
    categorias = CategoriaHerramienta.objects.all()
    
    filtro_form = HerramientaFiltroForm(request.GET)
    if filtro_form.is_valid():
        categoria = filtro_form.cleaned_data['categoria']
        busqueda = filtro_form.cleaned_data['busqueda']

        if categoria:
            activos_fijos = activos_fijos.filter(categoria=categoria)
            herramientas = herramientas.filter(categoria=categoria)
        
        if busqueda:
            activos_fijos = activos_fijos.filter(nombre__icontains=busqueda)
            herramientas = herramientas.filter(nombre__icontains=busqueda)

    # Manejo de solicitud
    if request.method == 'POST':
        solicitud_form = SolicitudForm(request.POST, user=request.user)
        detalle_formset = DetalleSolicitudFormSet(request.POST)
        alumno_id = request.POST.get('alumno_id')  # ID del alumno seleccionado
        nuevo_alumno_form = AlumnoForm(request.POST)

        if solicitud_form.is_valid() and detalle_formset.is_valid():
            # Obtener o crear el alumno
            if alumno_id:
                alumno = get_object_or_404(Alumno, id=alumno_id)
            elif nuevo_alumno_form.is_valid():
                alumno = nuevo_alumno_form.save()
            else:
                messages.error(request, 'Debe seleccionar un alumno existente o registrar uno nuevo.')
                return render(request, 'dashboards/panol/crear_solicitud.html', {
                    'solicitud_form': solicitud_form,
                    'detalle_formset': detalle_formset,
                    'herramientas': herramientas,
                    'activos_fijos': activos_fijos,
                    'categorias': categorias,
                    'filtro_form': filtro_form,
                    'nuevo_alumno_form': nuevo_alumno_form,
                    'alumnos': Alumno.objects.all(),
                })

            # Guardar solicitud
            solicitud = solicitud_form.save(commit=False)
            solicitud.usuario = request.user
            solicitud.alumno = alumno  # Asigna el alumno aquí
            solicitud.save()

            # Guardar detalles de solicitud
            try:
                detalles = detalle_formset.save(commit=False)

                # Validar stock de herramientas y activos fijos
                for detalle in detalles:
                    if detalle.herramienta:
                        herramienta = detalle.herramienta
                        if herramienta.stock_disponible < detalle.cantidad:
                            raise ValueError(f'Stock insuficiente para {herramienta.nombre}')
                        herramienta.stock_disponible -= detalle.cantidad
                        herramienta.save()
                    elif detalle.activo_fijo:
                        activo_fijo = detalle.activo_fijo
                        if activo_fijo.stock_disponible < detalle.cantidad:
                            raise ValueError(f'Stock insuficiente para {activo_fijo.nombre}')
                        activo_fijo.stock_disponible -= detalle.cantidad
                        activo_fijo.save()

                    detalle.solicitud = solicitud
                    detalle.save()

                messages.success(request, 'Solicitud creada exitosamente')
                return redirect('solicitudes')  # Ajusta según tu URL

            except ValueError as e:
                solicitud.delete()
                messages.error(request, str(e))
                return render(request, 'dashboards/panol/crear_solicitud.html', {
                    'solicitud_form': solicitud_form,
                    'detalle_formset': detalle_formset,
                    'herramientas': herramientas,
                    'activos_fijos': activos_fijos,
                    'categorias': categorias,
                    'filtro_form': filtro_form,
                    'nuevo_alumno_form': nuevo_alumno_form,
                    'alumnos': Alumno.objects.all(),
                })

    else:
        solicitud_form = SolicitudForm(user=request.user)
        detalle_formset = DetalleSolicitudFormSet()
        nuevo_alumno_form = AlumnoForm()

    context = {
        'solicitud_form': solicitud_form,
        'detalle_formset': detalle_formset,
        'herramientas': herramientas,
        'activos_fijos': activos_fijos,
        'categorias': categorias,
        'filtro_form': filtro_form,
        'nuevo_alumno_form': nuevo_alumno_form,
        'alumnos': Alumno.objects.all(),
    }
    return render(request, 'dashboards/panol/crear_solicitud.html', context)



def crear_alumno(request):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        nombres = request.POST.get('nombre')  # Cambia 'nombre' a 'nombres'
        apellidos = request.POST.get('apellido')  # Cambia 'apellido' a 'apellidos'
        rut = request.POST.get('rut')
        correo = request.POST.get('email')  # Cambia 'email' a 'correo'

        # Validación y creación del alumno
        if nombres and apellidos and rut and correo:
            alumno = Alumno.objects.create(
                nombres=nombres,  # Cambia 'nombre' a 'nombres'
                apellidos=apellidos,  # Cambia 'apellido' a 'apellidos'
                rut=rut,
                correo=correo  # Cambia 'email' a 'correo'
            )
            return JsonResponse({
                'success': True,
                'alumno': {
                    'id': alumno.id,
                    'nombres': alumno.nombres,  # Cambia 'nombre' a 'nombres'
                    'apellidos': alumno.apellidos  # Cambia 'apellido' a 'apellidos'
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Todos los campos son obligatorios.'})

    return JsonResponse({'success': False, 'error': 'Solicitud inválida.'})



def alumno_list(request):
    alumnos = Alumno.objects.all()
    return render(request, 'dashboards/panol/alumnos/alumno_list.html', {'alumnos': alumnos})

def alumno_create(request):
    if request.method == 'POST':
        form = AlumnoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('alumno_list')
    else:
        form = AlumnoForm()
    return render(request, 'dashboards/panol/alumnos/alumno_form.html', {'form': form})

def alumno_update(request, pk):
    alumno = get_object_or_404(Alumno, pk=pk)
    if request.method == 'POST':
        form = AlumnoForm(request.POST, instance=alumno)
        if form.is_valid():
            form.save()
            return redirect('alumno_list')
    else:
        form = AlumnoForm(instance=alumno)
    return render(request, 'dashboards/panol/alumnos/alumno_form.html', {'form': form})

def alumno_delete(request, pk):
    alumno = get_object_or_404(Alumno, pk=pk)
    if request.method == 'POST':
        alumno.delete()
        return redirect('alumno_list')
    return render(request, 'dashboards/panol/alumnos/alumno_confirm_delete.html', {'alumno': alumno})


def buscar_alumno(request):
    if 'rut' in request.GET:
        rut = request.GET['rut']
        alumnos = Alumno.objects.filter(rut__icontains=rut)  # Filtra por RUT
        resultados = [
            {
                'id': alumno.id,
                'nombre': alumno.nombres,  # Usa 'nombre' en lugar de 'nombres'
                'apellido': alumno.apellidos,  # Agrega el campo 'apellido'
                'rut': alumno.rut
            }
            for alumno in alumnos
        ]
        return JsonResponse(resultados, safe=False)
    return JsonResponse([], safe=False)



@login_required
def graficos_view(request):
    """
    Vista para renderizar la página de gráficos
    """
    context = {
        'body_class': 'admin-dashboard',
        'titulo_pagina': 'Gráficos y Estadísticas'
    }
    return render(request, 'dashboards/admin/graficos.html', context)

@login_required
@require_GET
def obtener_datos_grafico(request):
    """
    Vista para obtener datos para los gráficos
    """
    # Parámetros de filtro
    tipo_grafico = request.GET.get('tipo', 'solicitudes_asignatura')
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')
    profesor_id = request.GET.get('profesor')

    # Filtro de profesores
    profesores = CustomUser.objects.filter(user_type='profesor')

    # Filtro de fechas
    queryset = Solicitud.objects.all()
    if fecha_inicio and fecha_fin:
        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            queryset = queryset.filter(
                created_at__date__range=[inicio, fin]
            )
        except ValueError:
            pass

    # Filtro de profesor
    if profesor_id:
        try:
            profesor = CustomUser.objects.get(id=profesor_id, user_type='profesor')
            queryset = queryset.filter(usuario=profesor)
        except CustomUser.DoesNotExist:
            # Manejar caso de profesor no encontrado
            pass

    # Inicializar variables para labels y valores
    labels = []
    valores = []

    # Lógica para diferentes tipos de gráficos
    if tipo_grafico == 'solicitudes_asignatura':
        datos = queryset.values('asignatura__nombre')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:10]
        
        labels = [d['asignatura__nombre'] or 'Sin Asignatura' for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'activos_fijos_asignatura':
        # Filtrar detalles de solicitud con activos fijos
        datos_activos_fijos = DetalleSolicitud.objects.filter(
            solicitud__in=queryset, 
            activo_fijo__isnull=False
        ).values(
            'solicitud__usuario__first_name',  # Nombre del profesor
            'solicitud__usuario__last_name',   # Apellido del profesor
            'solicitud__asignatura__nombre',   # Nombre de la asignatura
            'activo_fijo__nombre'              # Nombre del activo fijo
        ).annotate(
            total_activos_fijos=Sum('cantidad')
        ).order_by('-total_activos_fijos')[:10]

        # Verificar si hay datos
        if datos_activos_fijos:
            labels = [
                f"{d['solicitud__usuario__first_name']} {d['solicitud__usuario__last_name']} - {d['solicitud__asignatura__nombre']} - {d['activo_fijo__nombre'] or 'Sin Nombre'}"
                for d in datos_activos_fijos
            ]
            valores = [
                d['total_activos_fijos'] 
                for d in datos_activos_fijos
            ]
        else:
            labels = ['Sin datos']
            valores = [0]

    elif tipo_grafico == 'herramientas_solicitadas':
        datos_herramientas = DetalleSolicitud.objects.filter(solicitud__in=queryset, herramienta__isnull=False)\
            .values('herramienta__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total')[:10]
        
        datos_activos_fijos = DetalleSolicitud.objects.filter(solicitud__in=queryset, activo_fijo__isnull=False)\
            .values('activo_fijo__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total')[:10]

        labels = [d['herramienta__nombre'] or 'Sin Herramienta' for d in datos_herramientas] + \
                [d['activo_fijo__nombre'] or 'Sin Activo Fijo' for d in datos_activos_fijos]
        valores = [d['total'] for d in datos_herramientas] + \
                [d['total'] for d in datos_activos_fijos]
        
    elif tipo_grafico == 'estados_solicitud':
        datos = queryset.values('estado')\
            .annotate(total=Count('id'))\
            .order_by('-total')
        
        labels = [d['estado'] for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'solicitudes_profesor':
        datos = queryset.values('usuario__first_name', 'usuario__last_name')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:10]
        
        labels = [f"{d['usuario__first_name']} {d['usuario__last_name']}" for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'solicitudes_mes':
        datos = queryset.annotate(mes=TruncMonth('created_at'))\
            .values('mes')\
            .annotate(total=Count('id'))\
            .order_by('mes')
        
        labels = [d['mes'].strftime('%B %Y') for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'categorias_herramientas':
        datos = DetalleSolicitud.objects.filter(solicitud__in=queryset)\
            .values('herramienta__categoria__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total')[:10]
        
        labels = [d['herramienta__categoria__nombre'] or 'Sin Categoría' for d in datos]
        valores = [d['total'] for d in datos]

    return JsonResponse({
        'labels': labels,
        'valores': valores,
        'profesores': list(profesores.values('id', 'first_name', 'last_name', 'email'))
    })

@login_required
def obtener_profesores(request):
    """
    Vista para obtener la lista de profesores
    """
    profesores = CustomUser.objects.filter(user_type='profesor').values('id', 'first_name', 'last_name')
    return JsonResponse({
        'profesores': list(profesores)
    })



@login_required
def estadisticas_resumen(request):
    # Rango de tiempo para comparaciones (últimos 30 días)
    fecha_limite = timezone.now() - timedelta(days=30)

    # Resumen de Solicitudes
    resumen_solicitudes = {
        'total_solicitudes': Solicitud.objects.count(),
        'solicitudes_ultimos_30_dias': Solicitud.objects.filter(
            created_at__gte=fecha_limite
        ).count(),
        'estados_solicitudes': list(
            Solicitud.objects.values('estado')
            .annotate(total=Count('id'))
            .order_by('-total')
        ),
        'promedio_solicitudes_diarias': Solicitud.objects.filter(
            created_at__gte=fecha_limite
        ).count() / 30
    }

   # Resumen de Herramientas y Activos Fijos
    resumen_herramientas = {
        'total_herramientas': Herramienta.objects.count(),
        'herramientas_mas_solicitadas': list(
            DetalleSolicitud.objects.filter(herramienta__isnull=False)
            .values('herramienta__nombre')
            .annotate(total_solicitudes=Sum('cantidad'))
            .order_by('-total_solicitudes')[:5]
        ),
        'total_activos_fijos': ActivoFijo.objects.count(),
        'activos_fijos_mas_solicitados': list(
            DetalleSolicitud.objects.filter(activo_fijo__isnull=False)
            .values('activo_fijo__nombre')
            .annotate(total_solicitudes=Sum('cantidad'))
            .order_by('-total_solicitudes')[:5]
        ),
        'herramientas_disponibles': Herramienta.objects.filter(stock_disponible__gt=0).count(),
        'herramientas_agotadas': Herramienta.objects.filter(stock_disponible=0).count(),
    }


    # Resumen de Usuarios
    resumen_usuarios = {
        'total_usuarios': CustomUser.objects.count(),
        'usuarios_por_tipo': list(
            CustomUser.objects.values('user_type')
            .annotate(total=Count('id'))
            .order_by('-total')
        ),
        'usuarios_mas_activos': list(
            Solicitud.objects.values('usuario__email', 'usuario__first_name', 'usuario__last_name')
            .annotate(total_solicitudes=Count('id'))
            .order_by('-total_solicitudes')[:5]
        )
    }

    # Resumen de Asignaturas
    resumen_asignaturas = {
        'total_asignaturas': Asignatura.objects.count(),
        'asignaturas_mas_solicitadas': list(
            Solicitud.objects.values('asignatura__nombre')
            .annotate(total_solicitudes=Count('id'))
            .order_by('-total_solicitudes')[:5]
        ),
        'distribucion_diurno_nocturno': list(
            Asignatura.objects.values('diurno_nocturno')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
    }

    # Resumen Temporal
    resumen_temporal = {
        'solicitudes_por_mes': list(
            Solicitud.objects.annotate(
                mes=TruncMonth('created_at')
            ).values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        ),
        'tendencia_solicitudes': calcular_tendencia_solicitudes()
    }

    # Resumen de Categorías de Herramientas
    resumen_categorias = {
        'total_categorias': CategoriaHerramienta.objects.count(),
        'categorias_mas_solicitadas': list(
            DetalleSolicitud.objects.values('herramienta__categoria__nombre')
            .annotate(total_solicitudes=Sum('cantidad'))
            .order_by('-total_solicitudes')[:5]
        )
    }

    # Resumen de Estado y Salud del Sistema
    resumen_sistema = {
        'solicitudes_pendientes': Solicitud.objects.filter(estado='pendiente').count(),
        'solicitudes_vencidas': Solicitud.objects.filter(
            estado='pendiente', 
            fecha_devolucion_solicitada__lt=timezone.now()
        ).count(),
        'herramientas_rotas': Herramienta.objects.filter(rota=True).count(),
    }

    return JsonResponse({
        'solicitudes': resumen_solicitudes,
        'herramientas': resumen_herramientas,
        'usuarios': resumen_usuarios,
        'asignaturas': resumen_asignaturas,
        'temporal': resumen_temporal,
        'categorias': resumen_categorias,
        'sistema': resumen_sistema
    })

def calcular_tendencia_solicitudes():
    """
    Calcula la tendencia de solicitudes comparando periodos
    """
    # Periodos de comparación
    periodo_actual = timezone.now() - timedelta(days=30)
    periodo_anterior = periodo_actual - timedelta(days=30)

    # Contar solicitudes en cada periodo
    solicitudes_periodo_actual = Solicitud.objects.filter(
        created_at__gte=periodo_actual
    ).count()

    solicitudes_periodo_anterior = Solicitud.objects.filter(
        created_at__gte=periodo_anterior,
        created_at__lt=periodo_actual
    ).count()

    # Calcular porcentaje de cambio
    if solicitudes_periodo_anterior > 0:
        porcentaje_cambio = (
            (solicitudes_periodo_actual - solicitudes_periodo_anterior) 
            / solicitudes_periodo_anterior 
            * 100
        )
    else:
        porcentaje_cambio = 0

    return {
        'actual': solicitudes_periodo_actual,
        'anterior': solicitudes_periodo_anterior,
        'porcentaje_cambio': porcentaje_cambio
    }


def obtener_datos_completos(request):
    # Recuperar datos de resumen
    datos_completos = {
        'solicitudes': {
            'Total de Solicitudes': Solicitud.objects.count(),
            'Solicitudes Últimos 30 Días': Solicitud.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'Estados de Solicitudes': list(
                Solicitud.objects.values('estado')
                .annotate(cantidad=Count('id'))
                .values_list('estado', 'cantidad')
            )
        },
        'herramientas': {
            'Total de Herramientas': Herramienta.objects.count(),
            'Herramientas Disponibles': Herramienta.objects.filter(stock_disponible__gt=0).count(),
            'Herramientas Agotadas': Herramienta.objects.filter(stock_disponible=0).count(),
            'Herramientas por Categoría': list(
                Herramienta.objects.values('categoria__nombre')
                .annotate(cantidad=Count('id'))
                .values_list('categoria__nombre', 'cantidad')
            )
        },
        'usuarios': {
            'Total de Usuarios': CustomUser.objects.count(),
            'Usuarios Activos': CustomUser.objects.filter(is_active=True).count(),
            'Usuarios Inactivos': CustomUser.objects.filter(is_active=False).count(),
            'Usuarios por Rol': list(
                CustomUser.objects.values('rol')
                .annotate(cantidad=Count('id'))
                .values_list('rol', 'cantidad')
            )
        },
        'sistema': {
            'Total de Solicitudes Pendientes': Solicitud.objects.filter(estado='pendiente').count(),
            'Total de Solicitudes Aprobadas': Solicitud.objects.filter(estado='aprobada').count(),
            'Total de Solicitudes Rechazadas': Solicitud.objects.filter(estado='rechazada').count(),
        }
    }
    return JsonResponse(datos_completos)



@login_required
def graficos_view_panol(request):
    """
    Vista para renderizar la página de gráficos
    """
    context = {
        'body_class': 'panol-dashboard',
        'titulo_pagina': 'Gráficos y Estadísticas'
    }
    return render(request, 'dashboards/panol/graficos.html', context)

@login_required
@require_GET
def obtener_datos_grafico_panol(request):
    """
    Vista para obtener datos para los gráficos
    """
    # Parámetros de filtro
    tipo_grafico = request.GET.get('tipo', 'solicitudes_asignatura')
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')

    # Filtro de fechas
    queryset = Solicitud.objects.all()
    if fecha_inicio and fecha_fin:
        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            queryset = queryset.filter(
                created_at__date__range=[inicio, fin]
            )
        except ValueError:
            pass

    # Lógica para diferentes tipos de gráficos
    if tipo_grafico == 'solicitudes_asignatura':
        datos = queryset.values('asignatura__nombre')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:10]
        
        labels = [d['asignatura__nombre'] or 'Sin Asignatura' for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'herramientas_solicitadas':
        datos = DetalleSolicitud.objects.filter(solicitud__in=queryset)\
            .values('herramienta__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total')[:10]
        
        labels = [d['herramienta__nombre'] or 'Sin Herramienta' for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'estados_solicitud':
        datos = queryset.values('estado')\
            .annotate(total=Count('id'))\
            .order_by('-total')
        
        labels = [d['estado'] for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'solicitudes_profesor':
        datos = queryset.values('usuario__first_name', 'usuario__last_name')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:10]
        
        labels = [f"{d['usuario__first_name']} {d['usuario__last_name']}" for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'solicitudes_mes':
        datos = queryset.annotate(mes=TruncMonth('created_at'))\
            .values('mes')\
            .annotate(total=Count('id'))\
            .order_by('mes')
        
        labels = [d['mes'].strftime('%B %Y') for d in datos]
        valores = [d['total'] for d in datos]

    elif tipo_grafico == 'categorias_herramientas':
        datos = DetalleSolicitud.objects.filter(solicitud__in=queryset)\
            .values('herramienta__categoria__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total')[:10]
        
        labels = [d['herramienta__categoria__nombre'] or 'Sin Categoría' for d in datos]
        valores = [d['total'] for d in datos]

    return JsonResponse({
        'labels': labels,
        'valores': valores
    })

@login_required
def estadisticas_resumen_panol(request):
    # Rango de tiempo para comparaciones (últimos 30 días)
    fecha_limite = timezone.now() - timedelta(days=30)

    # Resumen de Solicitudes
    resumen_solicitudes = {
        'total_solicitudes': Solicitud.objects.count(),
        'solicitudes_ultimos_30_dias': Solicitud.objects.filter(
            created_at__gte=fecha_limite
        ).count(),
        'estados_solicitudes': list(
            Solicitud.objects.values('estado')
            .annotate(total=Count('id'))
            .order_by('-total')
        ),
        'promedio_solicitudes_diarias': Solicitud.objects.filter(
            created_at__gte=fecha_limite
        ).count() / 30
    }

    # Resumen de Herramientas
    resumen_herramientas = {
        'total_herramientas': Herramienta.objects.count(),
        'herramientas_mas_solicitadas': list(
            DetalleSolicitud.objects.values('herramienta__nombre')
            .annotate(total_solicitudes=Sum('cantidad'))
            .order_by('-total_solicitudes')[:5]
        ),
        'herramientas_disponibles': Herramienta.objects.filter(stock_disponible__gt=0).count(),
        'herramientas_agotadas': Herramienta.objects.filter(stock_disponible=0).count(),
    }

    # Resumen de Usuarios
    resumen_usuarios = {
        'total_usuarios': CustomUser.objects.count(),
        'usuarios_por_tipo': list(
            CustomUser.objects.values('user_type')
            .annotate(total=Count('id'))
            .order_by('-total')
        ),
        'usuarios_mas_activos': list(
            Solicitud.objects.values('usuario__email', 'usuario__first_name', 'usuario__last_name')
            .annotate(total_solicitudes=Count('id'))
            .order_by('-total_solicitudes')[:5]
        )
    }

    # Resumen de Asignaturas
    resumen_asignaturas = {
        'total_asignaturas': Asignatura.objects.count(),
        'asignaturas_mas_solicitadas': list(
            Solicitud.objects.values('asignatura__nombre')
            .annotate(total_solicitudes=Count('id'))
            .order_by('-total_solicitudes')[:5]
        ),
        'distribucion_diurno_nocturno': list(
            Asignatura.objects.values('diurno_nocturno')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
    }

    # Resumen Temporal
    resumen_temporal = {
        'solicitudes_por_mes': list(
            Solicitud.objects.annotate(
                mes=TruncMonth('created_at')
            ).values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        ),
        'tendencia_solicitudes': calcular_tendencia_solicitudes()
    }

    # Resumen de Categorías de Herramientas
    resumen_categorias = {
        'total_categorias': CategoriaHerramienta.objects.count(),
        'categorias_mas_solicitadas': list(
            DetalleSolicitud.objects.values('herramienta__categoria__nombre')
            .annotate(total_solicitudes=Sum('cantidad'))
            .order_by('-total_solicitudes')[:5]
        )
    }

    # Resumen de Estado y Salud del Sistema
    resumen_sistema = {
        'solicitudes_pendientes': Solicitud.objects.filter(estado='pendiente').count(),
        'solicitudes_vencidas': Solicitud.objects.filter(
            estado='pendiente', 
            fecha_devolucion_solicitada__lt=timezone.now()
        ).count(),
        'herramientas_rotas': Herramienta.objects.filter(rota=True).count(),
    }

    return JsonResponse({
        'solicitudes': resumen_solicitudes,
        'herramientas': resumen_herramientas,
        'usuarios': resumen_usuarios,
        'asignaturas': resumen_asignaturas,
        'temporal': resumen_temporal,
        'categorias': resumen_categorias,
        'sistema': resumen_sistema
    })

def calcular_tendencia_solicitudes_panol():
    """
    Calcula la tendencia de solicitudes comparando periodos
    """
    # Periodos de comparación
    periodo_actual = timezone.now() - timedelta(days=30)
    periodo_anterior = periodo_actual - timedelta(days=30)

    # Contar solicitudes en cada periodo
    solicitudes_periodo_actual = Solicitud.objects.filter(
        created_at__gte=periodo_actual
    ).count()

    solicitudes_periodo_anterior = Solicitud.objects.filter(
        created_at__gte=periodo_anterior,
        created_at__lt=periodo_actual
    ).count()

    # Calcular porcentaje de cambio
    if solicitudes_periodo_anterior > 0:
        porcentaje_cambio = (
            (solicitudes_periodo_actual - solicitudes_periodo_anterior) 
            / solicitudes_periodo_anterior 
            * 100
        )
    else:
        porcentaje_cambio = 0

    return {
        'actual': solicitudes_periodo_actual,
        'anterior': solicitudes_periodo_anterior,
        'porcentaje_cambio': porcentaje_cambio
    }


def obtener_datos_completos_panol(request):
    # Recuperar datos de resumen
    datos_completos = {
        'solicitudes': {
            'Total de Solicitudes': Solicitud.objects.count(),
            'Solicitudes Últimos 30 Días': Solicitud.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'Estados de Solicitudes': list(
                Solicitud.objects.values('estado')
                .annotate(cantidad=Count('id'))
                .values_list('estado', 'cantidad')
            )
        },
        'herramientas': {
            'Total de Herramientas': Herramienta.objects.count(),
            'Herramientas Disponibles': Herramienta.objects.filter(stock_disponible__gt=0).count(),
            'Herramientas Agotadas': Herramienta.objects.filter(stock_disponible=0).count(),
            'Herramientas por Categoría': list(
                Herramienta.objects.values('categoria__nombre')
                .annotate(cantidad=Count('id'))
                .values_list('categoria__nombre', 'cantidad')
            )
        },
        'usuarios': {
            'Total de Usuarios': CustomUser.objects.count(),
            'Usuarios Activos': CustomUser.objects.filter(is_active=True).count(),
            'Usuarios Inactivos': CustomUser.objects.filter(is_active=False).count(),
            'Usuarios por Rol': list(
                CustomUser.objects.values('user_type')
                .annotate(cantidad=Count('id'))
                .values_list('user_type', 'cantidad')
            )
        },
        'sistema': {
            'Total de Solicitudes Pendientes': Solicitud.objects.filter(estado='pendiente').count(),
            'Total de Solicitudes Aprobadas': Solicitud.objects.filter(estado='aprobada').count(),
            'Total de Solicitudes Rechazadas': Solicitud.objects.filter(estado='rechazada').count(),
        }
    }
    return JsonResponse(datos_completos)