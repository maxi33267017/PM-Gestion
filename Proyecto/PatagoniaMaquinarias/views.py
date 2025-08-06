from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin

def home_redirect(request):
    """
    Vista para redirigir desde la URL raíz
    - Si el usuario está logueado: redirigir según su rol y especialización
    - Si no está logueado: redirigir a /login/
    """
    if request.user.is_authenticated:
        # Redirigir técnicos al dashboard de técnicos
        if request.user.rol == 'TECNICO':
            return redirect('gestionDeTaller:dashboard_tecnico')
        # Redirigir administrativos RRHH al dashboard administrativo RRHH
        elif request.user.rol == 'ADMINISTRATIVO' and getattr(request.user, 'especializacion_admin', None) == 'RRHH':
            return redirect('recursosHumanos:dashboard_administrativo_rrhh')
        # Redirigir gerentes al dashboard de gerentes
        elif request.user.rol == 'GERENTE':
            return redirect('gestionDeTaller:dashboard_gerente')
        # Para otros roles, ir a gestión de taller
        else:
            return redirect('gestionDeTaller:gestion_de_taller')
    else:
        return redirect('login')

class HomeRedirectView(RedirectView):
    """
    Vista basada en clase para redirigir desde la URL raíz
    """
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return '/gestion_de_taller/'
        else:
            return '/login/' 