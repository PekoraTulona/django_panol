
from django.urls import path
from . import  views 
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('', views.login_view, name="login"),
    path('register/', views.register, name='register'),
    path('dashboard-profesor/', views.dashboard_profesor, name='dashboard_profesor'),
    path('dashboard-panolero/', views.dashboard_panolero, name='dashboard_panolero'),
    path('dashboard-admin/', views.dashboard_admin, name='dashboard_admin'),
    path('logout/', views.logout_view, name='logout'),
    path('get-asignaturas/', views.get_asignaturas, name='get_asignaturas'),
    path('lista_usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('perfil/', views.ver_perfil, name='perfil_profesor'),
    
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/cambiar-contrasena/', views.cambiar_contrasena_view, name='cambiar_contraseña'),

    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/<int:solicitud_id>/', views.detalle_solicitud, name='detalle_solicitud2'),
    path('solicitudes/procesar/<int:solicitud_id>/', views.procesar_solicitud, name='procesar_solicitud'),

    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:pk>/', views.eliminar_usuario, name='eliminar_usuario'),


    path('administrar-herramientas/', views.administrar_herramientas, name='administrar_herramientas_admin'),
    path('agregar-herramienta/', views.agregar_herramienta, name='agregar_herramienta_admin'),
    path('editar-herramienta/<int:pk>/', views.editar_herramienta, name='editar_herramienta_admin'),
    path('eliminar-herr -herramienta/<int:pk>/', views.eliminar_herramienta, name='eliminar_herramienta_admin'),
    path('administrar-categorias/', views.administrar_categorias, name='administrar_categorias_admin'),
    path('agregar-categoria/', views.agregar_categoria, name='agregar_categoria_admin'),
    path('editar-categoria/<int:pk>/', views.editar_categoria, name='editar_categoria_admin'),
    path('eliminar-categoria/<int:pk>/', views.eliminar_categoria, name='eliminar_categoria_admin'),

    path('api/solicitudes/notificaciones/', views.obtener_numero_solicitudes, name='api_numero_solicitudes'),
    path('api/obtener_notificaciones_mantenimiento/', views.obtener_numero_activos, name='api_obtener_notificaciones_mantenimiento'),

    path('solicitudes/auxiliar/', views.solicitudes_auxiliar, name='solicitudes_auxiliar'),
    path('solicitudes/auxiliar/<int:solicitud_id>/', views.detalle_solicitud_auxiliar, name='detalle_solicitud_auxiliar'),
    path('solicitudes/auxiliar/procesar/<int:solicitud_id>/', views.procesar_solicitud_auxiliar, name='procesar_solicitud_auxiliar'),
    path('api/solicitudes/notificaciones/', views.obtener_numero_solicitudes_auxiliar, name='api_numero_solicitudes_auxiliar'),

    path('usuarios_panolero/', views.listar_usuarios_panolero, name='listar_usuarios_panolero'),
    path('usuarios_panolero/crear/', views.crear_usuario_panolero, name='crear_usuario_panolero'),
    path('usuarios_panolero/editar/<int:pk>/', views.editar_usuario_panolero, name='editar_usuario_panolero'),
    path('usuarios_panolero/eliminar/<int:pk>/', views.eliminar_usuario_panolero, name='eliminar_usuario_panolero'),

    path('asignaturas/', views.listar_asignaturas, name='listar_asignaturas'),
    path('asignaturas/crear/', views.crear_asignatura, name='crear_asignatura'),
    path('asignaturas/editar/<int:pk>/', views.editar_asignatura, name='editar_asignatura'),
    path('asignaturas/eliminar/<int:pk>/', views.eliminar_asignatura, name='eliminar_asignatura'),

    
    path('usuarios_panolero/', views.listar_usuarios_panolero, name='listar_usuarios_panolero'),
    path('usuarios_panolero/crear/', views.crear_usuario_panolero, name='crear_usuario_panolero'),
    path('usuarios_panolero/editar/<int:pk>/', views.editar_usuario_panolero, name='editar_usuario_panolero'),
    path('usuarios_panolero/eliminar/<int:pk>/', views.eliminar_usuario_panolero, name='eliminar_usuario_panolero'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)