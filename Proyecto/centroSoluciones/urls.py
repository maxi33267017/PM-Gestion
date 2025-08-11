from django.urls import path
from . import views

app_name = 'centroSoluciones'

urlpatterns = [
    path('', views.dashboard, name='centro_soluciones_dashboard'),
    path('alertas/', views.alertas_list, name='alertas_list'),
    path('alertas/<int:alerta_id>/', views.alerta_detail, name='alerta_detail'),
    path('alertas/<int:alerta_id>/procesar/', views.procesar_alerta, name='procesar_alerta'),
    path('leads/', views.leads_list, name='leads_list'),
    path('leads/<int:lead_id>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:lead_id>/editar/', views.lead_edit, name='lead_edit'),
    # Gestión de códigos de alerta
    path('codigos-alerta/', views.gestionar_codigos_alerta, name='gestionar_codigos_alerta'),
    path('crear-codigo-alerta/', views.crear_codigo_alerta, name='crear_codigo_alerta'),
    # Nuevas URLs para formularios modales
    path('crear-alerta/', views.crear_alerta, name='crear_alerta'),
    path('crear-lead/', views.crear_lead, name='crear_lead'),
    path('obtener-equipos-cliente/', views.obtener_equipos_cliente, name='obtener_equipos_cliente'),
    path('obtener-pins-equipos-cliente/', views.obtener_pins_equipos_cliente, name='obtener_pins_equipos_cliente'),
    path('obtener-tecnicos/', views.obtener_tecnicos, name='obtener_tecnicos'),
    path('obtener-clientes/', views.obtener_clientes, name='obtener_clientes'),
    # URLs para códigos de alerta
    path('obtener-codigo-alerta/', views.obtener_codigo_alerta, name='obtener_codigo_alerta'),
    path('obtener-lista-codigos-alerta/', views.obtener_lista_codigos_alerta, name='obtener_lista_codigos_alerta'),
    path('obtener-modelos-equipos/', views.obtener_modelos_equipos, name='obtener_modelos_equipos'),

    # URLs para Reportes CSC
    path('reportes-csc/', views.lista_reportes_csc, name='lista_reportes_csc'),
    path('reportes-csc/importar/', views.importar_reporte_csc, name='importar_reporte_csc'),
    path('reportes-csc/<int:reporte_id>/', views.detalle_reporte_csc, name='detalle_reporte_csc'),
    path('reportes-csc/<int:reporte_id>/pdf/', views.generar_pdf_reporte_csc, name='generar_pdf_reporte_csc'),
    path('reportes-csc/<int:reporte_id>/comentarios/', views.actualizar_comentarios_csc, name='actualizar_comentarios_csc'),
] 