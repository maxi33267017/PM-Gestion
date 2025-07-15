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
]