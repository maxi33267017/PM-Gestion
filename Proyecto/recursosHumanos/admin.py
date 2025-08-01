from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Provincia, Ciudad, Sucursal, TarifaManoObra, RegistroHorasTecnico, Competencia, CompetenciaTecnico, CertificacionJD, CertificacionTecnico, EvaluacionSistema, RevisionHerramientas, HerramientaEspecial, PrestamoHerramienta, SesionCronometro, AlertaCronometro, PermisoAusencia


@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    model = Usuario
    list_display = ('id','email', 'nombre', 'apellido', 'sucursal', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {
            'fields': ('nombre', 'apellido', 'sucursal', 'sucursales_adicionales', 'rol')
        }),
        ('Permisos', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'nombre', 'apellido', 'sucursal', 'sucursales_adicionales', 'rol', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'nombre', 'apellido')
    ordering = ('email',)
    filter_horizontal = ('sucursales_adicionales',)


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    model = Provincia
    list_display = ('nombre',)

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    model = Ciudad
    list_display = ('nombre',)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    model = Sucursal
    list_display = ('nombre', 'direccion', 'ciudad', 'provincia')

@admin.register(TarifaManoObra)
class TarifaManoObraAdmin(admin.ModelAdmin):
    model = TarifaManoObra
    list_display = ('tipo', 'tipo_servicio', 'valor_hora', 'fecha_vigencia')



@admin.register(RegistroHorasTecnico)
class RegistroHorasTecnicoAdmin(admin.ModelAdmin):
    model = RegistroHorasTecnico
    list_display = ('tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'tipo_hora', 'servicio', 'descripcion', 'aprobado')

@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    model = Competencia
    list_display = ('nombre',)

@admin.register(CertificacionJD)
class CertificacionJDAdmin(admin.ModelAdmin):
    model = CertificacionJD
    list_display = ('nombre', 'codigo_curso', 'level')

@admin.register(CertificacionTecnico)
class CertificacionTecnicoAdmin(admin.ModelAdmin):
    model = CertificacionTecnico
    list_display = ('tecnico', 'certificacion')

@admin.register(CompetenciaTecnico)
class CompetenciaTecnicoAdmin(admin.ModelAdmin):
    model = CompetenciaTecnico
    list_display = ('tecnico', 'competencia', 'nivel', 'fecha_evaluacion', 'evaluador')


@admin.register(EvaluacionSistema)
class EvaluacionSistemaAdmin(admin.ModelAdmin):
    model = EvaluacionSistema
    list_display = ('usuario', 'fecha_evaluacion')

@admin.register(RevisionHerramientas)
class RevisionHerramientasAdmin(admin.ModelAdmin):
    model = RevisionHerramientas
    list_display = ('tecnico', 'fecha_revision')

@admin.register(HerramientaEspecial)
class HerramientaEspecialAdmin(admin.ModelAdmin):
    model = HerramientaEspecial
    list_display = ('codigo', 'nombre', 'ubicacion', 'disponible')

@admin.register(PrestamoHerramienta)
class PrestamoHerramientaAdmin(admin.ModelAdmin):
    model = PrestamoHerramienta
    list_display = ('herramienta', 'usuario')

from django.contrib import admin
from recursosHumanos.models import ActividadTrabajo

@admin.register(ActividadTrabajo)
class ActividadTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'disponibilidad', 'genera_ingreso', 'requiere_servicio')
    list_filter = ('disponibilidad', 'genera_ingreso', 'requiere_servicio')
    search_fields = ('nombre',)
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('disponibilidad', 'genera_ingreso', 'categoria_facturacion', 'requiere_servicio')
        }),
    )


@admin.register(SesionCronometro)
class SesionCronometroAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'actividad', 'servicio', 'hora_inicio', 'hora_fin', 'activa', 'get_duracion_display')
    list_filter = ('activa', 'actividad', 'tecnico', 'hora_inicio')
    search_fields = ('tecnico__nombre', 'tecnico__apellido', 'actividad__nombre', 'servicio__id')
    readonly_fields = ('hora_inicio', 'fecha_creacion', 'fecha_modificacion')
    
    def get_duracion_display(self, obj):
        if obj.activa:
            return "En curso"
        elif obj.hora_fin:
            duracion = obj.get_duracion()
            horas = int(duracion.total_seconds() // 3600)
            minutos = int((duracion.total_seconds() % 3600) // 60)
            return f"{horas}h {minutos}m"
        return "N/A"
    get_duracion_display.short_description = "Duración"


@admin.register(AlertaCronometro)
class AlertaCronometroAdmin(admin.ModelAdmin):
    list_display = ('tipo_alerta', 'sesion', 'estado', 'fecha_envio', 'get_destinatarios_count')
    list_filter = ('tipo_alerta', 'estado', 'fecha_envio')
    search_fields = ('sesion__tecnico__nombre', 'sesion__tecnico__apellido', 'asunto')
    readonly_fields = ('fecha_envio', 'fecha_creacion')
    
    def get_destinatarios_count(self, obj):
        return len(obj.destinatarios) if obj.destinatarios else 0
    get_destinatarios_count.short_description = "Destinatarios"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sesion__tecnico', 'sesion__actividad')


@admin.register(PermisoAusencia)
class PermisoAusenciaAdmin(admin.ModelAdmin):
    list_display = [
        'usuario', 'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'estado', 'aprobado_por', 'fecha_aprobacion'
    ]
    list_filter = ['estado', 'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'usuario__sucursal']
    search_fields = ['usuario__nombre', 'usuario__apellido', 'motivo', 'aprobado_por__nombre', 'aprobado_por__apellido']
    date_hierarchy = 'fecha_inicio'
    readonly_fields = ['fecha_solicitud', 'fecha_aprobacion', 'usuario', 'aprobado_por']
    ordering = ['-fecha_solicitud']
    fieldsets = (
        ('Información del Permiso', {
            'fields': ('usuario', 'tipo_permiso', 'motivo', 'fecha_inicio', 'fecha_fin', 'justificativo', 'descripcion_justificativo')
        }),
        ('Estado y Aprobación', {
            'fields': ('estado', 'aprobado_por', 'fecha_aprobacion', 'observaciones_aprobacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_solicitud',),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25
    
    def has_add_permission(self, request):
        # Solo agregar desde el frontend, no desde el admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Solo gerentes y admin pueden cambiar
        return request.user.is_superuser or getattr(request.user, 'rol', None) in ['GERENTE', 'ADMINISTRATIVO']
    
    def has_delete_permission(self, request, obj=None):
        # Solo superuser puede borrar
        return request.user.is_superuser



