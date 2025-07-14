from django.urls import path
from . import views

app_name = 'operationsCenter'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_operations_center, name='dashboard_operations_center'),
    
    # Máquinas
    path('maquinas/', views.lista_maquinas, name='lista_maquinas'),
    path('maquinas/<int:machine_id>/', views.detalle_maquina, name='detalle_maquina'),
    path('maquinas/<int:machine_id>/sincronizar/', views.sincronizar_maquina, name='sincronizar_maquina'),
    
    # Alertas
    path('alertas/', views.lista_alertas, name='lista_alertas'),
    path('alertas/<int:alert_id>/', views.detalle_alerta, name='detalle_alerta'),
    
    # Sincronización
    path('sincronizar/', views.sincronizar_datos, name='sincronizar_datos'),
    
    # Configuración y OAuth
    path('configuracion/', views.configuracion_oc, name='configuracion_oc'),
    path('api/test-connection/', views.api_test_connection, name='api_test_connection'),
    path('oauth/iniciar/', views.iniciar_oauth, name='iniciar_oauth'),
    path('oauth/debug/', views.debug_oauth_config, name='debug_oauth_config'),
    path('oauth/habilitar-conexiones/', views.habilitar_conexiones_organizaciones, name='habilitar_conexiones_organizaciones'),
    path('oauth/estado-conexiones/', views.verificar_estado_conexiones, name='verificar_estado_conexiones'),
    path('callback/', views.oauth_callback, name='oauth_callback'),
    
    # Reportes de telemetría
    path('reportes/', views.lista_reportes_telemetria, name='lista_reportes_telemetria'),
    path('reportes/crear/', views.crear_reporte_telemetria, name='crear_reporte_telemetria'),
    path('reportes/<int:report_id>/', views.detalle_reporte_telemetria, name='detalle_reporte_telemetria'),
    
    # APIs
    path('api/machines-by-client/<int:client_id>/', views.api_machines_by_client, name='api_machines_by_client'),
] 