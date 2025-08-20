from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


from . import views

app_name = 'crm'

urlpatterns = [

    path('crm/', views.crm, name='crm'),
    path('crm/segmentacion/', views.segmentacion_clientes, name='segmentacion_clientes'),
    path('crm/portfolio/', views.portfolio_paquetes, name='portfolio_paquetes'),
    path('crm/portfolio/crear/', views.crear_paquete, name='crear_paquete'),
    path('crm/portfolio/editar/<int:paquete_id>/', views.editar_paquete, name='editar_paquete'),
    path('crm/portfolio/asignar/', views.asignar_paquete_cliente, name='asignar_paquete_cliente'),
    path('crm/portfolio/<int:paquete_id>/clientes/', views.clientes_por_paquete, name='clientes_por_paquete'),
    path('crm/campanias/', views.campanias_marketing, name='campanias_marketing'),
    path('crm/campanias/crear/', views.crear_campania, name='crear_campania'),
    path('crm/campanias/obtener-modelos/', views.obtener_modelos_por_tipo, name='obtener_modelos_por_tipo'),
    path('crm/embudos/crear-pops/', views.crear_embudo_pops, name='crear_embudo_pops'),
    path('crm/campanias/editar/<int:campania_id>/', views.editar_campania, name='editar_campania'),
    path('crm/campanias/<int:campania_id>/contactos/', views.gestionar_contactos, name='gestionar_contactos'),
    path('crm/campanias/<int:campania_id>/dashboard/', views.dashboard_campania, name='dashboard_campania'),
    path('crm/analisis/', views.analisis_clientes, name='analisis_clientes'),
    path('crm/analisis/cliente/<int:cliente_id>/', views.dashboard_cliente, name='dashboard_cliente'),
    path('crm/oportunidades/', views.oportunidades_venta, name='oportunidades_venta'),
    # URLs para Panel Admin
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('buzon-sugerencias/', views.buzon_sugerencias, name='buzon_sugerencias'),
    path('gestionar-sugerencias/', views.gestionar_sugerencias, name='gestionar_sugerencias'),
    path('revisar-sugerencia/<int:sugerencia_id>/', views.revisar_sugerencia, name='revisar_sugerencia'),
    # URLs para Embudo de Ventas
    path('embudo-ventas/', views.embudo_ventas, name='embudo_ventas'),
    path('embudo-ventas/crear/', views.crear_embudo, name='crear_embudo'),
    path('embudo-ventas/<int:embudo_id>/', views.detalle_embudo, name='detalle_embudo'),
    # Nuevas URLs para embudo de ventas con gráficos
    path('embudo-ventas-dashboard/', views.embudo_ventas_dashboard, name='embudo_ventas_dashboard'),
    path('embudo-ventas-campana/<int:campana_id>/', views.embudo_ventas_campana, name='embudo_ventas_campana'),
    path('embudo-ventas-campana/', views.embudo_ventas_campana, name='embudo_ventas_campana_sin_campana'),
    path('embudo-ventas-origen/<str:origen>/', views.embudo_ventas_origen, name='embudo_ventas_origen'),
    path('embudo-ventas-detalle/<int:embudo_id>/', views.embudo_ventas_detalle, name='embudo_ventas_detalle'),
    path('crear-contacto/', views.crear_contacto, name='crear_contacto'),
    # URLs para Embudo de Checklist Adicionales
    path('embudo-checklist/', views.embudo_checklist_dashboard, name='embudo_checklist_dashboard'),
    path('embudo-checklist/crear/', views.crear_checklist_adicional, name='crear_checklist_adicional'),
    path('embudo-checklist/<int:checklist_id>/', views.detalle_checklist, name='detalle_checklist'),
    path('embudo-checklist/etapa/<str:etapa>/', views.checklist_por_etapa, name='checklist_por_etapa'),
    path('embudo-checklist/prioridad/<str:prioridad>/', views.checklist_por_prioridad, name='checklist_por_prioridad'),
    # URLs para Reportes de Facturación
    path('reporte-facturacion/', views.reporte_facturacion, name='reporte_facturacion'),
    path('exportar-reporte-excel/', views.exportar_reporte_excel, name='exportar_reporte_excel'),
]