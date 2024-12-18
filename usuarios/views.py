from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import jwt
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserEditForm, AsignaturaForm
from .forms import EmailAuthenticationForm
from django.contrib.auth import logout
from django.http import JsonResponse
from .models import Asignatura, CustomUser
from .forms import ProfesorPerfilForm, CambiarContrasenaForm
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
import sys
from solicitudes.models import Solicitud
from django.contrib.sessions.models import Session
from django.utils.timezone import now
from solicitudes.models import Herramienta, CategoriaHerramienta, ActivoFijo
from solicitudes.forms import HerramientaFiltroForm, HerramientaForm, CategoriaHerramientaForm
from django.http import JsonResponse
from jwt import decode, ExpiredSignatureError, InvalidTokenError

def jwt_required(view_func):
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('Authorization')  # Obtener token del encabezado
        if not token:
            return JsonResponse({'error': 'Token no proporcionado.'}, status=403)

        try:
            payload = decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']  # Asignar el ID del usuario al request
        except ExpiredSignatureError:
            return JsonResponse({'error': 'Token expirado.'}, status=401)
        except InvalidTokenError:
            return JsonResponse({'error': 'Token inválido.'}, status=401)
        
        return view_func(request, *args, **kwargs)
    return wrapper

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@jwt_required
def protected_view(request):
    return JsonResponse({'message': '¡Tienes acceso a esta vista!'})



def home(request):
    return render(request, 'home.html')

def logout_previous_sessions(user):
    sessions = Session.objects.filter(expire_date__gte=now())
    for session in sessions:
        data = session.get_decoded()
        if str(user.id) == data.get('_auth_user_id'):
            session.delete()

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar el usuario, pero sin confirmar el commit (aún no lo guarda en la base de datos)
            user = form.save(commit=False)
            
            # Si el tipo de usuario es profesor, asigna las asignaturas
            if user.user_type == 'profesor':
                asignaturas = form.cleaned_data.get('asignaturas')
                if asignaturas:
                    # Asignamos las asignaturas seleccionadas al usuario
                    user.asignaturas.set(asignaturas)  # Asignamos varias asignaturas al usuario
            
            # Guarda finalmente el usuario en la base de datos
            user.save()
            
            messages.success(request, "Usuario registrado con éxito. ¡Ahora puedes iniciar sesión!")
            return redirect('login')  # Cambia a tu URL de inicio de sesión
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


SECRET_KEY = settings.SECRET_KEY

def generate_jwt_token(user):
    """
    Genera un token JWT para un usuario autenticado.
    """
    payload = {
        'user_id': user.id,
        'email': user.email,
        'user_type': user.user_type,
        'exp': datetime.utcnow() + timedelta(hours=1),  # Expira en 1 hora
        'iat': datetime.utcnow(),  # Fecha de emisión
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', None)

            # Autenticar al usuario
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # Cerrar sesiones previas
                logout_previous_sessions(user)

                # Iniciar sesión
                login(request, user)

                # Configurar duración de la sesión
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 semanas
                else:
                    request.session.set_expiry(0)  # Expira al cerrar el navegador

                # Redirigir según el tipo de usuario
                if is_ajax(request):  # Comprobación de solicitud AJAX
                    return JsonResponse({'success': True, 'redirect_url': 'dashboard_admin' if user.user_type == 'admin' else 'solicitudes'}, status=200)

                if user.user_type == 'admin':
                    return redirect('listar_usuarios')
                elif user.user_type == 'pañolero':
                    return redirect('solicitudes')
                elif user.user_type == 'auxiliarpañol':
                    return redirect('solicitudes_auxiliar')
                elif user.user_type == 'profesor':
                    return redirect('estadisticas_profesor')
            else:
                if is_ajax(request):
                    return JsonResponse({'error': "Correo o contraseña incorrectos."}, status=400)
                messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = EmailAuthenticationForm()

    if is_ajax(request):
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    return render(request, 'login.html', {'form': form})



@login_required
def dashboard_profesor(request):
    return render(request, 'dashboards/dashboard_profesor.html', {'body_class': 'profesor-dashboard'})



@login_required
def dashboard_admin(request):
    return render(request, 'dashboards/dashboard_admin.html', {'body_class': 'admin-dashboard'})

@login_required
def dashboard_auxiliar(request):
    return render(request, 'dashboards/dashboard_auxiliar.html')



def logout_view(request):
    logout(request)
    return redirect('login')




def get_asignaturas(request):
    # Comprobar si es una solicitud GET
    if request.method == 'GET':
        asignaturas = Asignatura.objects.all()
        data = [{"id": asignatura.id, "nombre": asignatura.nombre} for asignatura in asignaturas]
        return JsonResponse({"asignaturas": data})
    return JsonResponse({"error": "Método no permitido"}, status=405)



@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = ProfesorPerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('perfil_profesor')
    else:
        form = ProfesorPerfilForm(instance=request.user)
    
    return render(request, 'dashboards/profe/editar_perfil.html', {'form': form})

@login_required
def cambiar_contrasena_view(request):
    if request.method == 'POST':
        form = CambiarContrasenaForm(request.user, request.POST)
        if form.is_valid():
            try:
                # Usar el método de cambio de contraseña del modelo de usuario
                request.user.cambiar_contrasena(
                    form.cleaned_data['contrasena_actual'],
                    form.cleaned_data['nueva_contrasena']
                )
                messages.success(request, 'Contraseña cambiada exitosamente.')
                return redirect('login')  # Asegúrate de que esta URL exista
            except ValidationError as e:
                # Manejar errores de validación
                messages.error(request, str(e))
                return render(request, 'dashboards/profe/cambiar_contraseña.html', {'form': form})
    else:
        form = CambiarContrasenaForm(request.user)
    
    return render(request, 'dashboards/profe/cambiar_contraseña.html', {'form': form})

@login_required
def cambiar_contrasena_view(request):
    if request.method == 'POST':
        form = CambiarContrasenaForm(request.user, request.POST)
        if form.is_valid():
            try:
                # Usar el método de cambio de contraseña del modelo de usuario
                request.user.cambiar_contrasena(
                    form.cleaned_data['contrasena_actual'],
                    form.cleaned_data['nueva_contrasena']
                )
                messages.success(request, 'Contraseña cambiada exitosamente.')
                return redirect('login')  # Asegúrate de que esta URL exista
            except ValidationError as e:
                # Manejar errores de validación
                messages.error(request, str(e))
                return render(request, 'dashboards/panol/cambiar_contraseña_panol.html', {'form': form})
    else:
        form = CambiarContrasenaForm(request.user)
    
    return render(request, 'dashboards/panol/cambiar_contraseña_panol.html', {'form': form})

@login_required
def cambiar_contrasena_view(request):
    if request.method == 'POST':
        form = CambiarContrasenaForm(request.user, request.POST)
        if form.is_valid():
            try:
                # Usar el método de cambio de contraseña del modelo de usuario
                request.user.cambiar_contrasena(
                    form.cleaned_data['contrasena_actual'],
                    form.cleaned_data['nueva_contrasena']
                )
                messages.success(request, 'Contraseña cambiada exitosamente.')
                return redirect('login')  # Asegúrate de que esta URL exista
            except ValidationError as e:
                # Manejar errores de validación
                messages.error(request, str(e))
                return render(request, 'dashboards/admin/cambiar_contraseña_admin.html', {'form': form})
    else:
        form = CambiarContrasenaForm(request.user)
    
    return render(request, 'dashboards/admin/cambiar_contraseña_admin.html', {'form': form})

@login_required
def ver_perfil(request):
    if request.user.user_type != 'profesor':
        messages.error(request, "Acceso denegado")
        return redirect('home')
    
    
    return render(request, 'dashboards/profe/perfil.html')

def compress_image(uploaded_image):
    """
    Comprime y redimensiona la imagen
    """
    image = Image.open(uploaded_image)
    
    # Convertir imagen a RGB si es PNG con transparencia
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Redimensionar manteniendo proporción
    output_size = (800, 800)
    image.thumbnail(output_size, Image.LANCZOS)
    
    # Crear un buffer en memoria
    image_buffer = BytesIO()
    image.save(image_buffer, format='JPEG', quality=70)
    image_buffer.seek(0)
    
    # Crear InMemoryUploadedFile
    return InMemoryUploadedFile(
        image_buffer, 
        None, 
        f'{uploaded_image.name.split(".")[0]}.jpg', 
        'image/jpeg',
        sys.getsizeof(image_buffer), 
        None
    )


@login_required
def dashboard_panolero(request):

    return render(request, 'dashboards/dashboard_panolero.html', {'body_class': 'panol-dashboard'})



@login_required
def solicitudes(request):
    # Solicitudes pendientes
    solicitudes_pendientes = Solicitud.objects.filter(
        estado='pendiente'
    ).order_by('-created_at')

    # Solicitudes aprobadas (esperando ser procesadas)
    solicitudes_aprobadas = Solicitud.objects.filter(
        estado='aprobada'
    ).order_by('-updated_at')

    # Solicitudes en proceso 
    solicitudes_en_proceso = Solicitud.objects.filter(
        estado='en_proceso'
    ).order_by('-updated_at')

    context = {
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'solicitudes_en_proceso': solicitudes_en_proceso,
        'num_solicitudes_nuevas': solicitudes_pendientes.count()
    }
    return render(request, 'dashboards/panol/solicitudes.html', context)


@login_required
def detalle_solicitud(request, solicitud_id):
    solicitud = Solicitud.objects.get(id=solicitud_id)
    detalles = solicitud.detalles.all()
    
    context = {
        'solicitud': solicitud,
        'detalles': detalles
    }
    return render(request, 'dashboards/panol/detalle_solicitud.html', context)


@transaction.atomic
def procesar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(Solicitud, id=solicitud_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '').strip()
        
        # Usar correo predeterminado en lugar de opcional
        email_destinatario = getattr(settings, 'DEFAULT_NOTIFICATION_EMAIL', 'sepulvedajose148@gmail.com')
        
        try:
            if accion == 'aprobar':
                solicitud.estado = 'aprobada'
                solicitud.observaciones = observaciones
                
                # Atrasar fecha 3 horas 
                fecha_aprobacion = timezone.now() - timedelta(hours=3)
                
                # Envío de correo siempre al correo predeterminado
                asunto = f'Solicitud #{solicitud.id} - Aprobación Confirmada'
                
                # Preparar detalles de artículos
                detalles_articulos = []
                for detalle in solicitud.detalles.all():
                    if detalle.herramienta:
                        detalles_articulos.append({
                            'tipo': 'Herramienta',
                            'nombre': detalle.herramienta.nombre,
                            'cantidad': detalle.cantidad
                        })
                    if detalle.activo_fijo:
                        detalles_articulos.append({
                            'tipo': 'Activo Fijo',
                            'nombre': detalle.activo_fijo.nombre,
                            'cantidad': detalle.cantidad
                        })
                
                # Contenido HTML del correo (igual que antes)
                mensaje_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #2c3e50;">Solicitud #{solicitud.id} - Aprobada</h2>
                        
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                            <tr>
                                <td style="padding: 10px; background-color: #ecf0f1;">
                                    <strong>Número de Solicitud:</strong> {solicitud.id}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;">
                                    <strong>Estado:</strong> Aprobada
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: #ecf0f1;">
                                    <strong>Fecha de Aprobación:</strong> {fecha_aprobacion.strftime('%d/%m/%Y %H:%M')}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;">
                                    <strong>Observaciones:</strong> {observaciones or 'Sin observaciones'}
                                </td>
                            </tr>
                        </table>
                        
                        <h3 style="color: #2c3e50;">Artículos Solicitados</h3>
                        
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #3498db; color: white;">
                                    <th style="padding: 10px;">Tipo</th>
                                    <th style="padding: 10px;">Nombre</th>
                                    <th style="padding: 10px;">Cantidad</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([
                                    f"""
                                    <tr>
                                        <td style="padding: 10px; border: 1px solid #ddd;">{articulo['tipo']}</td>
                                        <td style="padding: 10px; border: 1px solid #ddd;">{articulo['nombre']}</td>
                                        <td style="padding: 10px; border: 1px solid #ddd;">{articulo['cantidad']}</td>
                                    </tr>
                                    """ for articulo in detalles_articulos
                                ])}
                            </tbody>
                        </table>
                    </div>
                </body>
                </html>
                """
                
                try:
                    send_mail(
                        asunto,
                        'Este es un correo HTML',  # Texto plano para clientes sin soporte HTML
                        settings.DEFAULT_FROM_EMAIL,
                        [email_destinatario],
                        html_message=mensaje_html,
                        fail_silently=False,
                    )
                    messages.success(request, f'Correo de aprobación enviado a {email_destinatario}')
                except Exception as email_error:
                    messages.warning(request, f'Solicitud aprobada, pero no se pudo enviar el correo: {str(email_error)}')
                
                messages.success(request, f'La solicitud #{solicitud.id} ha sido aprobada exitosamente.')
            
            elif accion == 'rechazar':
                solicitud.estado = 'rechazada'
                solicitud.observaciones = observaciones
                # Devolver herramientas al stock
                # Devolver herramientas y activos fijos al stock
                for detalle in solicitud.detalles.all():
                    if detalle.herramienta:
                        herramienta = detalle.herramienta
                        herramienta.devolver_al_stock(detalle.cantidad)
                    if detalle.activo_fijo:
                        activo_fijo = detalle.activo_fijo
                        activo_fijo.devolver_al_stock(detalle.cantidad)  # Asegúrate de que este método exista en el modelo ActivoFijo

            messages.warning(request, f'La solicitud #{solicitud.id} ha sido rechazada y las herramientas y activos fijos devueltos al stock.')
            
            elif accion == 'en_proceso':
                solicitud.estado = 'en_proceso'
                solicitud.observaciones = observaciones
                messages.info(request, f'La solicitud #{solicitud.id} está ahora en proceso.')
            
            elif accion == 'completar':
                solicitud.estado = 'completada'
                solicitud.observaciones = observaciones
                
                # Devolver herramientas al stock
                for detalle in solicitud.detalles.all():
                    if detalle.herramienta:
                        herramienta = detalle.herramienta
                        herramienta.devolver_al_stock(detalle.cantidad)
                    
                    # Devolver activos fijos al stock
                    if detalle.activo_fijo:
                        activo_fijo = detalle.activo_fijo
                        activo_fijo.devolver_al_stock(detalle.cantidad)
                
                messages.success(request, f'La solicitud #{solicitud.id} ha sido completada y las herramientas y activos fijos devueltos al stock.')
            
            solicitud.updated_at = timezone.now()
            solicitud.save()
            
            return redirect('solicitudes')
        
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
    
    return render(request, 'dashboards/panol/procesar_solicitud.html', {'solicitud': solicitud})


def listar_usuarios(request):
    usuarios = CustomUser.objects.exclude(id=request.user.id).order_by('-date_joined')
    return render(request, 'dashboards/admin/listar_usuarios.html', {'usuarios': usuarios})

def crear_usuario(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            usuario = form.save(commit=False)  # No guardar aún en la base de datos
            usuario.save()  # Guardar el usuario para asignar un ID

            # Solo asignar asignaturas si el usuario es un profesor
            if usuario.user_type == 'profesor':
                # Asignar las asignaturas seleccionadas
                usuario.asignaturas.set(form.cleaned_data['asignaturas'])
            else:
                # Limpiar asignaturas si no es profesor
                usuario.asignaturas.clear()  # Esto ahora no causará un error

            messages.success(request, "Usuario creado exitosamente.")
            return redirect('listar_usuarios')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()  # Si no es POST, crea un formulario vacío
    
    # Renderiza el formulario, sea con errores o vacío
    return render(request, 'dashboards/admin/crear_usuarios.html', {'form': form})

def editar_usuario(request, pk):
    usuario = get_object_or_404(CustomUser , pk=pk)
    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Solo asignar asignaturas si el usuario es un profesor
            if usuario.user_type != 'profesor':
                usuario.asignaturas.clear()  # Limpiar asignaturas si no es profesor
            usuario.save()
            messages.success(request, "Usuario actualizado exitosamente.")
            return redirect('listar_usuarios')
    else:
        form = CustomUserEditForm(instance=usuario)
    return render(request, 'dashboards/admin/editar_usuarios.html', {'form': form, 'usuario': usuario})

def eliminar_usuario(request, pk):
    usuario = get_object_or_404(CustomUser , pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('listar_usuarios')
    return render(request, 'dashboards/admin/eliminar_usuarios.html', {'usuario': usuario})




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

    return render(request, 'dashboards/admin/administrar_herramientas_admin.html', {
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
            return redirect('administrar_herramientas_admin')
    else:
        form = HerramientaForm()
    return render(request, 'dashboards/admin/agregar_herramienta_admin.html', {'form': form})

@login_required
def editar_herramienta(request, pk):
    herramienta = get_object_or_404(Herramienta, pk=pk)
    if request.method == 'POST':
        form = HerramientaForm(request.POST, request.FILES, instance=herramienta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Herramienta actualizada exitosamente.')
            return redirect('administrar_herramientas_admin')
    else:
        form = HerramientaForm(instance=herramienta)
    return render(request, 'dashboards/admin/editar_herramienta_admin.html', {'form': form, 'herramienta': herramienta})

@login_required
def eliminar_herramienta(request, pk):
    herramienta = get_object_or_404(Herramienta, pk=pk)
    if request.method == 'POST':
        herramienta.delete()
        messages.success(request, 'Herramienta eliminada exitosamente.')
        return redirect('administrar_herramientas_admin')
    return render(request, 'dashboards/admin/eliminar_herramienta_admin.html', {'herramienta': herramienta})

@login_required
def administrar_categorias(request):
    categorias = CategoriaHerramienta.objects.all()
    return render(request, 'dashboards/admin/administrar_categorias_admin.html', {'categorias': categorias})

@login_required
def agregar_categoria(request):
    if request.method == 'POST':
        form = CategoriaHerramientaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría agregada exitosamente.')
            return redirect('administrar_categorias_admin')
    else:
        form = CategoriaHerramientaForm()
    return render(request, 'dashboards/admin/agregar_categoria_admin.html', {'form': form})

@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaHerramienta, pk=pk)
    if request.method == 'POST':
        form = CategoriaHerramientaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada exitosamente.')
            return redirect('administrar_categorias_admin')
    else:
        form = CategoriaHerramientaForm(instance=categoria)
    return render(request, 'dashboards/admin/editar_categoria_admin.html', {'form': form, 'categoria': categoria})

@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaHerramienta, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada exitosamente.')
        return redirect('administrar_categorias_admin')
    return render(request, 'dashboards/admin/eliminar_categoria_admin.html', {'categoria': categoria})


def obtener_numero_solicitudes(request):
    if request.user.is_authenticated:
        num_solicitudes_nuevas = Solicitud.objects.filter(estado="pendiente").count()  # Ajusta según tu lógica
        return JsonResponse({'num_solicitudes_nuevas': num_solicitudes_nuevas})
    return JsonResponse({'error': 'Usuario no autenticado'}, status=401)



def obtener_numero_activos(request):
    if request.user.is_authenticated:
        # Filtramos los activos cuya fecha de próximo mantenimiento es menor o igual a la fecha actual
        num_activos_necesitan_mantenimiento = ActivoFijo.objects.filter(fecha_proximo_mantenimiento__lte=datetime.today()).count()
        return JsonResponse({'num_activos_necesitan_mantenimiento': num_activos_necesitan_mantenimiento})
    return JsonResponse({'error': 'Usuario no autenticado'}, status=401)



@login_required
def solicitudes_auxiliar(request):
    # Solicitudes pendientes
    solicitudes_pendientes = Solicitud.objects.filter(
        estado='pendiente'
    ).order_by('-created_at')

    # Solicitudes aprobadas (esperando ser procesadas)
    solicitudes_aprobadas = Solicitud.objects.filter(
        estado='aprobada'
    ).order_by('-updated_at')

    # Solicitudes en proceso 
    solicitudes_en_proceso = Solicitud.objects.filter(
        estado='en_proceso'
    ).order_by('-updated_at')

    context = {
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'solicitudes_en_proceso': solicitudes_en_proceso,
        'num_solicitudes_nuevas': solicitudes_pendientes.count()
    }
    return render(request, 'dashboards/auxiliar/solicitudes.html', context)


@login_required
def detalle_solicitud_auxiliar(request, solicitud_id):
    solicitud = Solicitud.objects.get(id=solicitud_id)
    detalles = solicitud.detalles.all()
    
    context = {
        'solicitud': solicitud,
        'detalles': detalles
    }
    return render(request, 'dashboards/auxiliar/detalle_solicitud.html', context)


@transaction.atomic
def procesar_solicitud_auxiliar(request, solicitud_id):
    solicitud = get_object_or_404(Solicitud, id=solicitud_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '').strip()
        
        try:
            if accion == 'aprobar':
                solicitud.estado = 'aprobada'
                solicitud.observaciones = observaciones
                messages.success(request, f'La solicitud #{solicitud.id} ha sido aprobada exitosamente.')
            
            elif accion == 'rechazar':
                solicitud.estado = 'rechazada'
                solicitud.observaciones = observaciones
                # Devolver herramientas al stock
                for detalle in solicitud.detalles.all():
                    herramienta = detalle.herramienta
                    herramienta.devolver_al_stock(detalle.cantidad)
                messages.warning(request, f'La solicitud #{solicitud.id} ha sido rechazada y las herramientas devueltas al stock.')
            
            elif accion == 'en_proceso':
                solicitud.estado = 'en_proceso'
                solicitud.observaciones = observaciones
                messages.info(request, f'La solicitud #{solicitud.id} está ahora en proceso.')
            
            elif accion == 'completar':
                solicitud.estado = 'completada'
                solicitud.observaciones = observaciones
                # Devolver herramientas al stock
                for detalle in solicitud.detalles.all():
                    herramienta = detalle.herramienta
                    herramienta.devolver_al_stock(detalle.cantidad)
                messages.success(request, f'La solicitud #{solicitud.id} ha sido completada y las herramientas devueltas al stock.')
            
            solicitud.updated_at = timezone.now()
            solicitud.save()
            
            return redirect('solicitudes')
        
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
    
    return render(request, 'dashboards/auxiliar/procesar_solicitud.html', {'solicitud': solicitud})


def obtener_numero_solicitudes_auxiliar(request):
    if request.user.is_authenticated:
        num_solicitudes_nuevas = Solicitud.objects.filter(estado="pendiente").count()  # Ajusta según tu lógica
        return JsonResponse({'num_solicitudes_nuevas': num_solicitudes_nuevas})
    return JsonResponse({'error': 'Usuario no autenticado'}, status=401)




def listar_usuarios_panolero(request):
    # Mostrar solo usuarios de tipo profesor o auxiliar, excluyendo al usuario actual
    usuarios = CustomUser.objects.filter(user_type__in=['profesor', 'auxiliarpañol']).exclude(id=request.user.id).order_by('-date_joined')
    return render(request, 'dashboards/panol/listar_usuarios.html', {'usuarios': usuarios})

def crear_usuario_panolero(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Asegurar que solo pueda crear profesores o auxiliares
            if usuario.user_type in ['profesor', 'auxiliarpañol']:
                usuario.save()  # Guardar el usuario
                # Solo asignar asignaturas si el usuario es un profesor
                if usuario.user_type == 'profesor':
                    usuario.asignaturas.set(form.cleaned_data['asignaturas'])
                messages.success(request, "Usuario creado exitosamente.")
                return redirect('listar_usuarios_panolero')
            else:
                messages.error(request, "Solo puedes crear usuarios de tipo profesor o auxiliar.")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()  # Si no es POST, crea un formulario vacío
    
    return render(request, 'dashboards/panol/crear_usuarios.html', {'form': form})

def editar_usuario_panolero(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario.user_type not in ['profesor', 'auxiliarpañol']:
        messages.error(request, "No tienes permiso para editar este usuario.")
        return redirect('listar_usuarios_panolero')

    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Solo asignar asignaturas si el usuario es un profesor
            if usuario.user_type != 'profesor':
                usuario.asignaturas.clear()
            usuario.save()
            messages.success(request, "Usuario actualizado exitosamente.")
            return redirect('listar_usuarios_panolero')
    else:
        form = CustomUserEditForm(instance=usuario)
    return render(request, 'dashboards/panol/editar_usuarios.html', {'form': form, 'usuario': usuario})

def eliminar_usuario_panolero(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario.user_type not in ['profesor', 'auxiliarpañol']:
        messages.error(request, "No tienes permiso para eliminar este usuario.")
        return redirect('listar_usuarios_panolero')
    
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('listar_usuarios_panolero')
    return render(request, 'dashboards/panol/eliminar_usuarios.html', {'usuario': usuario})



def listar_asignaturas(request):
    asignaturas = Asignatura.objects.all()
    form = AsignaturaForm()
    return render(request, 'dashboards/admin/listar_asignaturas.html', {
        'asignaturas': asignaturas, 
        'form': form
    })

def crear_asignatura(request):
    if request.method == 'POST':
        form = AsignaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asignatura creada exitosamente.')
        else:
            messages.error(request, 'Error al crear la asignatura.')
    return HttpResponseRedirect(reverse('listar_asignaturas'))

def editar_asignatura(request, pk):
    asignatura = get_object_or_404(Asignatura, pk=pk)
    if request.method == 'POST':
        form = AsignaturaForm(request.POST, instance=asignatura)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asignatura actualizada exitosamente.')
        else:
            messages.error(request, 'Error al actualizar la asignatura.')
    return HttpResponseRedirect(reverse('listar_asignaturas'))

def eliminar_asignatura(request, pk):
    asignatura = get_object_or_404(Asignatura, pk=pk)
    if request.method == 'POST':
        try:
            asignatura.delete()
            messages.success(request, 'Asignatura eliminada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la asignatura: {str(e)}')
    return HttpResponseRedirect(reverse('listar_asignaturas'))



def listar_usuarios_panolero(request):
    # Mostrar solo usuarios de tipo profesor o auxiliar, excluyendo al usuario actual
    usuarios = CustomUser.objects.filter(user_type__in=['profesor', 'auxiliarpañol']).exclude(id=request.user.id).order_by('-date_joined')
    return render(request, 'dashboards/panol/listar_usuarios.html', {'usuarios': usuarios})

def crear_usuario_panolero(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Asegurar que solo pueda crear profesores o auxiliares
            if usuario.user_type in ['profesor', 'auxiliarpañol']:
                usuario.save()  # Guardar el usuario
                # Solo asignar asignaturas si el usuario es un profesor
                if usuario.user_type == 'profesor':
                    usuario.asignaturas.set(form.cleaned_data['asignaturas'])
                messages.success(request, "Usuario creado exitosamente.")
                return redirect('listar_usuarios_panolero')
            else:
                messages.error(request, "Solo puedes crear usuarios de tipo profesor o auxiliar.")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()  # Si no es POST, crea un formulario vacío
    
    return render(request, 'dashboards/panol/crear_usuarios.html', {'form': form})

def editar_usuario_panolero(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario.user_type not in ['profesor', 'auxiliarpañol']:
        messages.error(request, "No tienes permiso para editar este usuario.")
        return redirect('listar_usuarios_panolero')

    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Solo asignar asignaturas si el usuario es un profesor
            if usuario.user_type != 'profesor':
                usuario.asignaturas.clear()
            usuario.save()
            messages.success(request, "Usuario actualizado exitosamente.")
            return redirect('listar_usuarios_panolero')
    else:
        form = CustomUserEditForm(instance=usuario)
    return render(request, 'dashboards/panol/editar_usuarios.html', {'form': form, 'usuario': usuario})

def eliminar_usuario_panolero(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario.user_type not in ['profesor', 'auxiliarpañol']:
        messages.error(request, "No tienes permiso para eliminar este usuario.")
        return redirect('listar_usuarios_panolero')
    
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('listar_usuarios_panolero')
    return render(request, 'dashboards/panol/eliminar_usuarios.html', {'usuario': usuario})
