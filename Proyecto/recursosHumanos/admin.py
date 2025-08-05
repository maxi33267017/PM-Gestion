from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from .models import (
    Usuario, Sucursal, Provincia, Ciudad, ActividadTrabajo, 
    RegistroHorasTecnico, PermisoAusencia, Competencia, 
    CertificacionJD, CertificacionTecnico, CompetenciaTecnico,
    EvaluacionSistema, RevisionHerramientas, HerramientaEspecial,
    PrestamoHerramienta, SesionCronometro, AlertaCronometro
)

class EspecializacionAdminFilter(SimpleListFilter):
    title = 'Especialización Administrativa'
    parameter_name = 'especializacion_admin'

    def lookups(self, request, model_admin):
        return [
            ('especializado', 'Especializado'),
            ('general', 'General (Sin especialización)'),
            ('no_aplica', 'No aplica (No es administrativo)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'especializado':
            return queryset.filter(rol='ADMINISTRATIVO', es_administrativo_especializado=True)
        elif self.value() == 'general':
            return queryset.filter(rol='ADMINISTRATIVO', es_administrativo_especializado=False)
        elif self.value() == 'no_aplica':
            return queryset.exclude(rol='ADMINISTRATIVO')

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = [
        'email', 'nombre', 'apellido', 'rol', 'sucursal', 
        'especializacion_display', 'is_active', 'fecha_creacion'
    ]
    list_filter = [
        'rol', 'sucursal', EspecializacionAdminFilter,
        'especializacion_admin', 'is_active', 'fecha_creacion'
    ]
    search_fields = ['email', 'nombre', 'apellido']
    ordering = ['apellido', 'nombre']
    
    # Campos para crear/editar usuario
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {
            'fields': ('nombre', 'apellido', 'sucursal', 'sucursales_adicionales')
        }),
        ('Rol y Especialización', {
            'fields': ('rol', 'es_administrativo_especializado', 'especializacion_admin'),
            'description': 'Configurar el rol del usuario y su especialización administrativa si aplica.'
        }),
        ('Configuración Técnica', {
            'fields': ('tarifa_individual',),
            'classes': ('collapse',),
            'description': 'Configuración específica para técnicos.'
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellido', 'sucursal', 'rol', 'password1', 'password2'),
        }),
    )
    
    def especializacion_display(self, obj):
        """Mostrar la especialización de forma más clara"""
        if obj.es_administrativo():
            if obj.tiene_especializacion():
                return format_html(
                    '<span style="color: #28a745; font-weight: bold;">{}</span>',
                    obj.get_especializacion_display()
                )
            else:
                return format_html(
                    '<span style="color: #007bff; font-weight: bold;">General (Sin especialización)</span>'
                )
        else:
            return format_html(
                '<span style="color: #6c757d;">No aplica</span>'
            )
    
    especializacion_display.short_description = 'Especialización'
    especializacion_display.admin_order_field = 'especializacion_admin'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related('sucursal')
    
    def get_form(self, request, obj=None, **kwargs):
        """Personalizar el formulario según el rol"""
        form = super().get_form(request, obj, **kwargs)
        
        if obj and obj.rol != 'ADMINISTRATIVO':
            # Deshabilitar campos de especialización para no-administrativos
            form.base_fields['es_administrativo_especializado'].disabled = True
            form.base_fields['especializacion_admin'].disabled = True
        
        return form
    
    def save_model(self, request, obj, form, change):
        """Lógica personalizada al guardar"""
        # Si no está marcado como especializado, limpiar especialización
        if not obj.es_administrativo_especializado:
            obj.especializacion_admin = None
        
        super().save_model(request, obj, form, change)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ciudad', 'provincia', 'activo']
    list_filter = ['activo', 'provincia', 'ciudad']
    search_fields = ['nombre', 'direccion']
    ordering = ['nombre']

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']
    ordering = ['nombre']

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'provincia', 'activo']
    list_filter = ['activo', 'provincia']
    search_fields = ['nombre']
    ordering = ['provincia', 'nombre']

@admin.register(ActividadTrabajo)
class ActividadTrabajoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'disponibilidad', 'genera_ingreso', 'categoria_facturacion', 'activo']
    list_filter = ['disponibilidad', 'genera_ingreso', 'categoria_facturacion', 'activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(RegistroHorasTecnico)
class RegistroHorasTecnicoAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'tipo_hora', 'aprobado']
    list_filter = ['aprobado', 'fecha', 'tipo_hora', 'tecnico']
    search_fields = ['tecnico__nombre', 'tecnico__apellido', 'descripcion']
    ordering = ['-fecha', '-hora_inicio']
    date_hierarchy = 'fecha'

@admin.register(PermisoAusencia)
class PermisoAusenciaAdmin(admin.ModelAdmin):
    list_display = [
        'usuario', 'tipo_permiso', 'fecha_inicio', 'fecha_fin', 
        'estado', 'aprobado_por', 'dias_solicitados'
    ]
    list_filter = ['estado', 'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'usuario__sucursal']
    search_fields = ['usuario__nombre', 'usuario__apellido', 'motivo']
    ordering = ['-fecha_solicitud']
    date_hierarchy = 'fecha_inicio'
    
    def dias_solicitados(self, obj):
        return obj.dias_solicitados
    dias_solicitados.short_description = 'Días'

@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

@admin.register(CertificacionJD)
class CertificacionJDAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo_curso', 'level', 'activo']
    list_filter = ['level', 'activo']
    search_fields = ['nombre', 'codigo_curso', 'descripcion']
    ordering = ['nombre']

@admin.register(CertificacionTecnico)
class CertificacionTecnicoAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'certificacion', 'fecha_obtencion', 'fecha_vencimiento', 'nota_final']
    list_filter = ['certificacion', 'fecha_obtencion', 'fecha_vencimiento']
    search_fields = ['tecnico__nombre', 'tecnico__apellido', 'certificacion__nombre']
    ordering = ['-fecha_obtencion']
    date_hierarchy = 'fecha_obtencion'

@admin.register(CompetenciaTecnico)
class CompetenciaTecnicoAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'competencia', 'nivel', 'fecha_evaluacion', 'evaluador', 'activo']
    list_filter = ['nivel', 'activo', 'fecha_evaluacion', 'competencia']
    search_fields = ['tecnico__nombre', 'tecnico__apellido', 'competencia__nombre']
    ordering = ['tecnico', 'competencia']

@admin.register(EvaluacionSistema)
class EvaluacionSistemaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'evaluador', 'fecha_evaluacion', 'fecha_proxima_revision']
    list_filter = ['fecha_evaluacion', 'fecha_proxima_revision', 'usuario__sucursal']
    search_fields = ['usuario__nombre', 'usuario__apellido', 'evaluador__nombre']
    ordering = ['-fecha_evaluacion']
    date_hierarchy = 'fecha_evaluacion'

@admin.register(RevisionHerramientas)
class RevisionHerramientasAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'revisor', 'fecha_revision', 'fecha_proxima_revision']
    list_filter = ['fecha_revision', 'fecha_proxima_revision', 'tecnico__sucursal']
    search_fields = ['tecnico__nombre', 'tecnico__apellido', 'revisor__nombre']
    ordering = ['-fecha_revision']
    date_hierarchy = 'fecha_revision'

@admin.register(HerramientaEspecial)
class HerramientaEspecialAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'ubicacion', 'disponible']
    list_filter = ['disponible', 'ubicacion']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['codigo']

@admin.register(PrestamoHerramienta)
class PrestamoHerramientaAdmin(admin.ModelAdmin):
    list_display = ['herramienta', 'usuario', 'fecha_retiro', 'fecha_devolucion', 'esta_prestada']
    list_filter = ['fecha_retiro', 'fecha_devolucion', 'herramienta__ubicacion']
    search_fields = ['herramienta__nombre', 'usuario__nombre', 'usuario__apellido']
    ordering = ['-fecha_retiro']
    date_hierarchy = 'fecha_retiro'
    
    def esta_prestada(self, obj):
        return obj.esta_prestada
    esta_prestada.boolean = True
    esta_prestada.short_description = 'Prestada'

@admin.register(SesionCronometro)
class SesionCronometroAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'actividad', 'hora_inicio', 'hora_fin', 'activa', 'get_duracion']
    list_filter = ['activa', 'hora_inicio', 'actividad']
    search_fields = ['tecnico__nombre', 'tecnico__apellido', 'actividad__nombre']
    ordering = ['-hora_inicio']
    date_hierarchy = 'hora_inicio'
    
    def get_duracion(self, obj):
        return obj.get_duracion()
    get_duracion.short_description = 'Duración'

@admin.register(AlertaCronometro)
class AlertaCronometroAdmin(admin.ModelAdmin):
    list_display = ['sesion', 'tipo_alerta', 'estado', 'fecha_envio']
    list_filter = ['tipo_alerta', 'estado', 'fecha_envio']
    search_fields = ['sesion__tecnico__nombre', 'sesion__tecnico__apellido']
    ordering = ['-fecha_envio']
    date_hierarchy = 'fecha_envio'



