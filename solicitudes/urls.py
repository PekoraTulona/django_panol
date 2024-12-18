from django.urls import path
from . import views

urlpatterns = [

    path('activos/', views.listar_activos, name='listar_activos'),
    path('activos/crear/', views.crear_activo, name='crear_activo'),
    path('activos/editar/<int:pk>/', views.editar_activo, name='editar_activo'),
    path('activos/eliminar/<int:pk>/', views.eliminar_activo, name='eliminar_activo'),
    path('activos/<int:activo_id>/actualizar_mantenimiento/', 
         views.actualizar_mantenimiento, 
         name='actualizar_mantenimiento'),

    # URL para crear solicitud
    path('solicitud/crear/', views.crear_solicitud, name='crear_solicitud'),
    
    # URL para listar solicitudes
    path('lista_solicitudes/', views.lista_solicitudes, name='lista_solicitudes'),
    
    # URL para ver detalle de solicitud específica
    path('lista_solicitudes/<int:solicitud_id>/', views.detalle_solicitud, name='detalle_solicitud'),
    path('solicitudes/cancelar/<int:solicitud_id>/', views.cancelar_solicitud, name='cancelar_solicitud'),
    path('estadisticas/', views.estadisticas_profesor, name='estadisticas_profesor'),

    path('administrar-herramientas/', views.administrar_herramientas, name='administrar_herramientas'),
    path('agregar-herramienta/', views.agregar_herramienta, name='agregar_herramienta'),
    path('editar-herramienta/<int:pk>/', views.editar_herramienta, name='editar_herramienta'),
    path('eliminar-herr -herramienta/<int:pk>/', views.eliminar_herramienta, name='eliminar_herramienta'),
    path('administrar-categorias/', views.administrar_categorias, name='administrar_categorias'),
    path('agregar-categoria/', views.agregar_categoria, name='agregar_categoria'),
    path('editar-categoria/<int:pk>/', views.editar_categoria, name='editar_categoria'),
    path('eliminar-categoria/<int:pk>/', views.eliminar_categoria, name='eliminar_categoria'),

    path('estadisticas-panol/', views.estadisticas_panol, name='estadisticas_panol'),
    path('reportar-herramienta/', views.reportar_herramienta, name='reportar_herramienta'),

    path('panol/reportes-herramientas/', views.lista_reportes_herramientas, name='lista_reportes_herramientas'),
    path('panol/reporte-herramienta/<int:reporte_id>/', views.detalle_reporte_herramienta, name='detalle_reporte_herramienta'),
    path('generar-pdf-reportes/', views.generar_pdf_reportes_herramientas, name='generar_pdf_reportes'),

    path('solicitudes/', views.lista_solicitudes_panol, name='lista_solicitudes_panol'),
    path('solicitudes/pdf/<int:solicitud_id>/', views.generar_pdf_solicitud, name='generar_pdf_solicitud'),
    path('generar-pdf-todas-solicitudes/', views.generar_pdf_todas_solicitudes, name='generar_pdf_todas_solicitudes'),

    path('salas/gestionar/', views.gestionar_salas, name='gestionar_salas'),
    path('salas/historial/', views.historial_salas, name='historial_salas'),
    path('salas/detalle/<int:sala_id>/', views.detalle_sala, name='detalle_sala'),
    path('salas/crear/', views.crear_sala, name='crear_sala'),
    path('salas/editar/<int:sala_id>/', views.editar_sala, name='editar_sala'),
    path('salas/eliminar/<int:sala_id>/', views.eliminar_sala, name='eliminar_sala'),

    path('solicitud/crear_panol/', views.crear_solicitud_panolero, name='crear_solicitud_panol'),
    path('crear-alumno/', views.crear_alumno, name='crear_alumno'),

    path('alumnos/', views.alumno_list, name='alumno_list'),
    path('nuevo/', views.alumno_create, name='alumno_create'),
    path('editar/<int:pk>/', views.alumno_update, name='alumno_update'),
    path('eliminar/<int:pk>/', views.alumno_delete, name='alumno_delete'),

    path('buscar-alumno/', views.buscar_alumno, name='buscar_alumno'),

    path('graficos/', views.graficos_view, name='graficos'),
    
    # URL para obtener datos de gráficos
    path('obtener_datos_grafico/', views.obtener_datos_grafico, name='obtener_datos_grafico'),
    
    # URL para estadísticas de resumen
    path('estadisticas_resumen/', views.estadisticas_resumen, name='estadisticas_resumen'),
    path('obtener_datos_completos/', views.obtener_datos_completos, name='obtener_datos_completos'),


    path('graficos_panol/', views.graficos_view_panol, name='graficos_panol'),
    
    # URL para obtener d_panolatos de gráficos
    path('obtener_datos_grafico_panol/', views.obtener_datos_grafico_panol, name='obtener_datos_grafico_panol'),
    
    # URL para estadísticas de resumen
    path('estadisticas_resumen_panol/', views.estadisticas_resumen_panol, name='estadisticas_resumen'),
    path('obtener_datos_completos_panol/', views.obtener_datos_completos_panol, name='obtener_datos_completos_panol'),
    path('obtener_profesores/', views.obtener_profesores, name='obtener_profesores'),
]

