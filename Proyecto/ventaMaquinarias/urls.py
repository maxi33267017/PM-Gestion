from django.urls import path
from . import views

app_name = 'ventaMaquinarias'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_ventas, name='dashboard'),
    
    # Gestión de equipos en stock
    path('equipos-stock/', views.lista_equipos_stock, name='lista_equipos_stock'),
    path('equipos-stock/crear/', views.crear_equipo_stock, name='crear_equipo_stock'),
    path('equipos-stock/<int:equipo_id>/', views.detalle_equipo_stock, name='detalle_equipo_stock'),
    
    # Gestión de ventas
    path('crear-venta/<int:equipo_id>/', views.crear_venta, name='crear_venta'),
    path('crear-venta-directa/', views.crear_venta_directa, name='crear_venta_directa'),
    path('ventas/', views.lista_ventas, name='lista_ventas'),
    path('ventas/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('ventas/<int:venta_id>/checklist/', views.actualizar_checklist_procesos, name='actualizar_checklist_procesos'),
    path('transferir-equipo/<int:venta_id>/', views.transferir_equipo, name='transferir_equipo'),
    
    # Gestión de certificados
    path('certificados/', views.gestion_certificados, name='gestion_certificados'),
    path('certificados/<int:certificado_id>/agregar-stock/', views.agregar_stock_certificado, name='agregar_stock_certificado'),
    
    # API endpoints
    path('api/equipos-stock/', views.api_equipos_stock, name='api_equipos_stock'),
    path('api/certificados-disponibles/', views.api_certificados_disponibles, name='api_certificados_disponibles'),
] 