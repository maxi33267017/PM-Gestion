from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    # Dashboard principal de reportes
    path('', views.dashboard_reportes, name='dashboard_reportes'),
    
    # Reportes de Facturación
    path('facturacion/', views.reportes_facturacion, name='facturacion'),
    path('facturacion/tecnico/', views.facturacion_por_tecnico, name='facturacion_tecnico'),
    path('facturacion/sucursal/', views.facturacion_por_sucursal, name='facturacion_sucursal'),
    path('facturacion/mensual/', views.facturacion_mensual, name='facturacion_mensual'),
    path('facturacion/trimestral/', views.facturacion_trimestral, name='facturacion_trimestral'),
    path('facturacion/semestral/', views.facturacion_semestral, name='facturacion_semestral'),
    path('facturacion/anual/', views.facturacion_anual, name='facturacion_anual'),
    
    # Reportes de Registro de Horas
    path('horas/', views.reportes_horas, name='horas'),
    path('horas/sucursal/', views.horas_por_sucursal, name='horas_sucursal'),
    path('horas/tecnico/', views.horas_por_tecnico, name='horas_tecnico'),
    path('horas/productividad/', views.productividad_tecnicos, name='productividad'),
    path('horas/eficiencia/', views.eficiencia_tecnicos, name='eficiencia'),
    path('horas/desempeno/', views.desempeno_tecnicos, name='desempeno'),
    
    # Reportes de Servicios
    path('servicios/', views.reportes_servicios, name='servicios'),
    path('servicios/preordenes/', views.preordenes_estadisticas, name='preordenes'),
    path('servicios/programados/', views.servicios_programados, name='servicios_programados'),
    path('servicios/en-proceso/', views.servicios_en_proceso, name='servicios_en_proceso'),
    path('servicios/completados/', views.servicios_completados, name='servicios_completados'),
    path('servicios/tiempo-promedio/', views.tiempo_promedio_servicios, name='tiempo_promedio'),
    path('servicios/sucursal/', views.servicios_por_sucursal, name='servicios_sucursal'),
    path('servicios/tecnico/', views.servicios_por_tecnico, name='servicios_tecnico'),
    path('servicios/sin-ingresos/', views.servicios_sin_ingresos, name='servicios_sin_ingresos'),
    
    # Reportes de Preórdenes Sin Servicio
    path('preordenes/sin-servicio/', views.preordenes_sin_servicio, name='preordenes_sin_servicio'),
    path('preordenes/metricas-conversion/', views.metricas_conversion_preordenes, name='metricas_conversion_preordenes'),
    
    # Reportes de Embudos
    path('embudos/', views.reportes_embudos, name='embudos'),
    path('embudos/cantidad/', views.embudos_cantidad, name='embudos_cantidad'),
    path('embudos/abiertos-cerrados/', views.embudos_abiertos_cerrados, name='embudos_abiertos_cerrados'),
    path('embudos/tipo/', views.embudos_por_tipo, name='embudos_tipo'),
    path('embudos/sucursal/', views.embudos_por_sucursal, name='embudos_sucursal'),
    path('embudos/estadisticas/', views.embudos_estadisticas, name='embudos_estadisticas'),
    
    # Reportes de CSC
    path('csc/', views.reportes_csc, name='csc'),
    path('csc/leads/', views.csc_leads, name='csc_leads'),
    path('csc/alertas/', views.csc_alertas, name='csc_alertas'),
    path('csc/asignadas/', views.csc_asignadas, name='csc_asignadas'),
    path('csc/procesadas/', views.csc_procesadas, name='csc_procesadas'),
    path('csc/tecnico/', views.csc_por_tecnico, name='csc_tecnico'),
    path('csc/sucursal/', views.csc_por_sucursal, name='csc_sucursal'),
    
    # Reportes de Encuestas
    path('encuestas/', views.reportes_encuestas, name='encuestas'),
    path('encuestas/enviadas/', views.encuestas_enviadas, name='encuestas_enviadas'),
    path('encuestas/respuestas/', views.encuestas_respuestas, name='encuestas_respuestas'),
    path('encuestas/porcentajes/', views.encuestas_porcentajes, name='encuestas_porcentajes'),
    
    # Exportación de reportes
    path('exportar/<str:tipo>/<str:formato>/', views.exportar_reporte, name='exportar_reporte'),
] 