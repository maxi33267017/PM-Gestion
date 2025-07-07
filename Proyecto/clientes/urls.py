from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('clientes/', views.clientes, name='clientes'),
    path('parque/', views.parque, name='parque'),
    path('guardar_cliente/', views.guardar_cliente, name='guardar_cliente'),
    path('clientes/<int:cliente_id>/', views.detalle_cliente, name='detalle_cliente'),
    path('clientes/<int:cliente_id>/detalle_equipo/<int:equipo_id>/', views.detalle_equipo, name='detalle_equipo'),

    
]


