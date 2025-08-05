def especializacion_admin(request):
    """
    Context processor que agrega información sobre la especialización administrativa
    del usuario a todos los templates
    """
    context = {
        'user_es_administrativo': False,
        'user_tiene_especializacion': False,
        'user_especializacion': None,
        'user_especializacion_display': None,
        'user_modulos_disponibles': [],
        'user_puede_acceder_rrhh': False,
        'user_puede_acceder_contable': False,
        'user_puede_acceder_cajero': False,
        'user_puede_acceder_servicios': False,
        'user_puede_acceder_repuestos': False,
    }
    
    if request.user.is_authenticated:
        user = request.user
        
        # Información básica
        context['user_es_administrativo'] = user.es_administrativo()
        context['user_tiene_especializacion'] = user.tiene_especializacion()
        context['user_especializacion'] = user.especializacion_admin
        context['user_especializacion_display'] = user.get_especializacion_display()
        context['user_modulos_disponibles'] = user.get_modulos_disponibles()
        
        # Permisos específicos por módulo
        context['user_puede_acceder_rrhh'] = user.puede_acceder_modulo('rrhh')
        context['user_puede_acceder_contable'] = user.puede_acceder_modulo('contable')
        context['user_puede_acceder_cajero'] = user.puede_acceder_modulo('cajero')
        context['user_puede_acceder_servicios'] = user.puede_acceder_modulo('servicios')
        context['user_puede_acceder_repuestos'] = user.puede_acceder_modulo('repuestos')
    
    return context 