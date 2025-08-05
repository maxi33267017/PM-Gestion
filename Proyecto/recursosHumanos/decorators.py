from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps

def requiere_especializacion_admin(modulo):
    """
    Decorador para verificar que el usuario administrativo tenga la especialización
    requerida para acceder a un módulo específico
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Verificar si el usuario puede acceder al módulo
            if not request.user.puede_acceder_modulo(modulo):
                messages.error(
                    request, 
                    f"No tienes permisos para acceder al módulo de {modulo.title()}. "
                    f"Tu especialización es: {request.user.get_especializacion_display()}"
                )
                return redirect('home')  # O redirigir a una página de acceso denegado
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def requiere_administrativo(view_func):
    """
    Decorador para verificar que el usuario sea administrativo
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.es_administrativo():
            messages.error(
                request, 
                "Esta sección es solo para usuarios administrativos."
            )
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def requiere_especializacion_o_general(modulo):
    """
    Decorador que permite acceso si el usuario tiene la especialización específica
    o si es administrativo general (sin especialización)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Permitir acceso si es administrativo sin especialización (general)
            if request.user.es_administrativo() and not request.user.tiene_especializacion():
                return view_func(request, *args, **kwargs)
            
            # Verificar si tiene la especialización específica
            if request.user.puede_acceder_modulo(modulo):
                return view_func(request, *args, **kwargs)
            
            messages.error(
                request, 
                f"No tienes permisos para acceder al módulo de {modulo.title()}. "
                f"Tu especialización es: {request.user.get_especializacion_display()}"
            )
            return redirect('home')
        
        return _wrapped_view
    return decorator 