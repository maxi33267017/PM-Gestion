from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


from . import views

app_name = 'recursosHumanos'

urlpatterns = [
    path('cronometro/', views.cronometro, name='cronometro'),
    path('cronometro/iniciar/', views.iniciar_cronometro, name='iniciar_cronometro'),
    path('cronometro/detener/', views.detener_cronometro, name='detener_cronometro'),
    path('cronometro/estado/', views.estado_cronometro, name='estado_cronometro'),
    path('cronometro/finalizar-automaticas/', views.finalizar_sesiones_automaticas, name='finalizar_sesiones_automaticas'),
    path('cronometro/verificar-alertas/', views.verificar_alertas_cronometro, name='verificar_alertas_cronometro'),
    path('cronometro/dashboard-alertas/', views.dashboard_alertas_cronometro, name='dashboard_alertas_cronometro'),
    
    # =============================================================================
    # URLs PARA SISTEMA DE PERMISOS Y AUSENCIAS
    # =============================================================================
    
    # URLs para usuarios generales
    path('permisos/', views.lista_permisos, name='lista_permisos'),
    path('permisos/solicitar/', views.solicitar_permiso, name='solicitar_permiso'),
    path('permisos/<int:permiso_id>/', views.detalle_permiso, name='detalle_permiso'),
    path('permisos/<int:permiso_id>/editar/', views.editar_permiso, name='editar_permiso'),
    path('permisos/<int:permiso_id>/cancelar/', views.cancelar_permiso, name='cancelar_permiso'),
    
    # URLs para gerentes
    path('permisos/gerente/', views.lista_permisos_gerente, name='lista_permisos_gerente'),
    path('permisos/<int:permiso_id>/aprobar/', views.aprobar_permiso, name='aprobar_permiso'),
    path('permisos/<int:permiso_id>/rechazar/', views.rechazar_permiso, name='rechazar_permiso'),
    path('permisos/dashboard/', views.dashboard_permisos, name='dashboard_permisos'),
    
    # =============================================================================
    # URLs PARA SISTEMA DE ESPECIALIZACIONES ADMINISTRATIVAS
    # =============================================================================
    
    # Dashboard general administrativo
    path('administrativo/dashboard/', views.dashboard_administrativo_general, name='dashboard_administrativo_general'),
    
    # Dashboards específicos por especialización
    path('administrativo/rrhh/dashboard/', views.dashboard_administrativo_rrhh, name='dashboard_administrativo_rrhh'),
    path('administrativo/contable/dashboard/', views.dashboard_administrativo_contable, name='dashboard_administrativo_contable'),
    path('administrativo/cajero/dashboard/', views.dashboard_administrativo_cajero, name='dashboard_administrativo_cajero'),
    path('administrativo/servicios/dashboard/', views.dashboard_administrativo_servicios, name='dashboard_administrativo_servicios'),
    path('administrativo/repuestos/dashboard/', views.dashboard_administrativo_repuestos, name='dashboard_administrativo_repuestos'),
    
    # Gestión avanzada (solo RRHH o generales)
    path('administrativo/permisos-avanzada/', views.gestion_permisos_avanzada, name='gestion_permisos_avanzada'),
    
    # Perfil de especialización
    path('perfil-especializacion/', views.perfil_especializacion, name='perfil_especializacion'),
]