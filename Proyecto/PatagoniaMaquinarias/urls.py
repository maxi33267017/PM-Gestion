from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from .views import home_redirect



urlpatterns = [
    # URL raíz - redirigir según estado de autenticación
    path('', home_redirect, name='home'),
    
    path('clientes/', include('clientes.urls')),
    path('crm/', include('crm.urls')),
    path('gestion_de_taller/', include('gestionDeTaller.urls')),
    path('informes/', include('informes.urls')),
    path('recursosHumanos/', include('recursosHumanos.urls')),
    path('centro-soluciones/', include('centroSoluciones.urls')),
    path('operations-center/', include('operationsCenter.urls')),
    path('venta-maquinarias/', include('ventaMaquinarias.urls')),
    path('select2/', include('django_select2.urls')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
