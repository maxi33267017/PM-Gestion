from django.urls import path
from . import views

app_name = 'centroSoluciones'

urlpatterns = [
    path('', views.dashboard, name='centro_soluciones_dashboard'),
    path('alertas/', views.alertas_list, name='alertas_list'),
    path('alertas/<int:alerta_id>/', views.alerta_detail, name='alerta_detail'),
    path('alertas/<int:alerta_id>/procesar/', views.procesar_alerta, name='procesar_alerta'),
    path('leads/', views.leads_list, name='leads_list'),
    # Nuevas URLs para formularios modales
    path('crear-alerta/', views.crear_alerta, name='crear_alerta'),
    path('crear-lead/', views.crear_lead, name='crear_lead'),
    path('obtener-equipos-cliente/', views.obtener_equipos_cliente, name='obtener_equipos_cliente'),
    path('obtener-pins-equipos-cliente/', views.obtener_pins_equipos_cliente, name='obtener_pins_equipos_cliente'),
    path('obtener-tecnicos/', views.obtener_tecnicos, name='obtener_tecnicos'),
    path('obtener-clientes/', views.obtener_clientes, name='obtener_clientes'),
] 