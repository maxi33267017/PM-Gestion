from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import AlertaEquipo, LeadJohnDeere, AsignacionAlerta, CodigoAlerta

@admin.register(AlertaEquipo)
class AlertaEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 
        'cliente', 
        'pin_equipo', 
        'clasificacion_badge', 
        'estado_badge', 
        'tecnico_asignado', 
        'sar_status_badge',
        'crm_opportunity_badge',
        'fecha', 
        'tiempo_pendiente_display'
    ]
    list_filter = [
        'estado', 
        'clasificacion', 
        'sucursal', 
        'fecha', 
        'tecnico_asignado'
    ]
    search_fields = [
        'cliente__razon_social', 
        'cliente__cuit', 
        'pin_equipo', 
        'codigo', 
        'descripcion'
    ]
    date_hierarchy = 'fecha'
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('cliente', 'pin_equipo', 'codigo', 'descripcion', 'clasificacion', 'sucursal')
        }),
        ('Asignación y Seguimiento', {
            'fields': ('estado', 'tecnico_asignado', 'observaciones_tecnico'),
            'classes': ('collapse',)
        }),
        ('Conexión SAR y CRM', {
            'fields': ('conexion_sar_realizada', 'fecha_conexion_sar', 'resultado_conexion_sar', 'oportunidad_crm_creada'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'fecha_asignacion', 'fecha_resolucion', 'fecha_conexion_sar']
    
    actions = ['asignar_tecnicos', 'marcar_resueltas', 'marcar_canceladas']
    
    def clasificacion_badge(self, obj):
        colors = {
            'CRITICA': 'danger',
            'ALTA': 'warning',
            'MEDIA': 'info',
            'BAJA': 'success',
        }
        color = colors.get(obj.clasificacion, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_clasificacion_display()
        )
    clasificacion_badge.short_description = 'Clasificación'
    
    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': 'danger',
            'ASIGNADA': 'warning',
            'EN_PROCESO': 'info',
            'RESUELTA': 'success',
            'CANCELADA': 'secondary',
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def tiempo_pendiente_display(self, obj):
        if obj.tiempo_pendiente:
            horas = obj.tiempo_pendiente.total_seconds() / 3600
            if horas > 24:
                dias = int(horas // 24)
                return f"{dias} días"
            else:
                return f"{int(horas)} horas"
        return "-"
    tiempo_pendiente_display.short_description = 'Tiempo Pendiente'
    
    def sar_status_badge(self, obj):
        if obj.conexion_sar_realizada:
            return format_html(
                '<span class="badge bg-success" title="{}">SAR ✓</span>',
                obj.fecha_conexion_sar.strftime('%d/%m/%Y %H:%M') if obj.fecha_conexion_sar else 'Conexión SAR realizada'
            )
        return format_html('<span class="badge bg-secondary">SAR ✗</span>')
    sar_status_badge.short_description = 'SAR'
    
    def crm_opportunity_badge(self, obj):
        if obj.oportunidad_crm_creada:
            return format_html('<span class="badge bg-primary">CRM ✓</span>')
        return format_html('<span class="badge bg-secondary">CRM ✗</span>')
    crm_opportunity_badge.short_description = 'CRM'
    
    def asignar_tecnicos(self, request, queryset):
        # Esta acción se puede expandir para asignar técnicos automáticamente
        updated = queryset.update(estado='ASIGNADA')
        self.message_user(request, f'{updated} alertas marcadas como asignadas.')
    asignar_tecnicos.short_description = "Marcar como asignadas"
    
    def marcar_resueltas(self, request, queryset):
        updated = queryset.update(estado='RESUELTA')
        self.message_user(request, f'{updated} alertas marcadas como resueltas.')
    marcar_resueltas.short_description = "Marcar como resueltas"
    
    def marcar_canceladas(self, request, queryset):
        updated = queryset.update(estado='CANCELADA')
        self.message_user(request, f'{updated} alertas marcadas como canceladas.')
    marcar_canceladas.short_description = "Marcar como canceladas"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva alerta
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filtrar por sucursal si el usuario no es superusuario
        if not request.user.is_superuser and hasattr(request.user, 'sucursal'):
            qs = qs.filter(sucursal=request.user.sucursal)
        return qs


@admin.register(LeadJohnDeere)
class LeadJohnDeereAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 
        'equipo', 
        'clasificacion_badge', 
        'estado_badge', 
        'fecha', 
        'valor_estimado_display',
        'tiempo_sin_contactar_display'
    ]
    list_filter = [
        'estado', 
        'clasificacion',
        'sucursal', 
        'fecha'
    ]
    search_fields = [
        'cliente__razon_social', 
        'cliente__cuit', 
        'equipo__numero_serie', 
        'descripcion'
    ]
    date_hierarchy = 'fecha'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Lead', {
            'fields': ('cliente', 'equipo', 'clasificacion', 'descripcion', 'sucursal')
        }),
        ('Seguimiento', {
            'fields': ('estado', 'observaciones_contacto', 'valor_estimado'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'fecha_contacto']
    
    actions = ['marcar_contactados', 'marcar_calificados', 'marcar_convertidos']
    
    def clasificacion_badge(self, obj):
        color = obj.get_clasificacion_color()
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_clasificacion_display()
        )
    clasificacion_badge.short_description = 'Clasificación'
    
    def estado_badge(self, obj):
        colors = {
            'NUEVO': 'danger',
            'CONTACTADO': 'warning',
            'CALIFICADO': 'info',
            'CONVERTIDO': 'success',
            'DESCARTADO': 'secondary',
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def valor_estimado_display(self, obj):
        if obj.valor_estimado:
            return f"${obj.valor_estimado:,.2f}"
        return "-"
    valor_estimado_display.short_description = 'Valor Estimado'
    
    def tiempo_sin_contactar_display(self, obj):
        if obj.tiempo_sin_contactar:
            horas = obj.tiempo_sin_contactar.total_seconds() / 3600
            if horas > 24:
                dias = int(horas // 24)
                return f"{dias} días"
            else:
                return f"{int(horas)} horas"
        return "-"
    tiempo_sin_contactar_display.short_description = 'Tiempo Sin Contactar'
    
    def marcar_contactados(self, request, queryset):
        updated = queryset.update(estado='CONTACTADO')
        self.message_user(request, f'{updated} leads marcados como contactados.')
    marcar_contactados.short_description = "Marcar como contactados"
    
    def marcar_calificados(self, request, queryset):
        updated = queryset.update(estado='CALIFICADO')
        self.message_user(request, f'{updated} leads marcados como calificados.')
    marcar_calificados.short_description = "Marcar como calificados"
    
    def marcar_convertidos(self, request, queryset):
        updated = queryset.update(estado='CONVERTIDO')
        self.message_user(request, f'{updated} leads marcados como convertidos.')
    marcar_convertidos.short_description = "Marcar como convertidos"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo lead
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filtrar por sucursal si el usuario no es superusuario
        if not request.user.is_superuser and hasattr(request.user, 'sucursal'):
            qs = qs.filter(sucursal=request.user.sucursal)
        return qs


@admin.register(AsignacionAlerta)
class AsignacionAlertaAdmin(admin.ModelAdmin):
    list_display = [
        'alerta', 
        'tecnico', 
        'fecha_asignacion', 
        'asignado_por'
    ]
    list_filter = [
        'fecha_asignacion', 
        'tecnico', 
        'asignado_por'
    ]
    search_fields = [
        'alerta__codigo', 
        'tecnico__nombre', 
        'tecnico__apellido'
    ]
    date_hierarchy = 'fecha_asignacion'
    readonly_fields = ['fecha_asignacion']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva asignación
            obj.asignado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(CodigoAlerta)
class CodigoAlertaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 
        'modelo_equipo', 
        'clasificacion_badge', 
        'tiempo_estimado_resolucion',
        'activo_badge',
        'fecha_creacion'
    ]
    list_filter = [
        'clasificacion', 
        'activo', 
        'fecha_creacion',
        'modelo_equipo'
    ]
    search_fields = [
        'codigo', 
        'modelo_equipo', 
        'descripcion',
        'instrucciones_resolucion'
    ]
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Código', {
            'fields': ('codigo', 'modelo_equipo', 'descripcion', 'clasificacion', 'activo')
        }),
        ('Información Técnica', {
            'fields': ('instrucciones_resolucion', 'repuestos_comunes', 'tiempo_estimado_resolucion'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    actions = ['activar_codigos', 'desactivar_codigos']
    
    def clasificacion_badge(self, obj):
        color = obj.get_prioridad_color()
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_clasificacion_display()
        )
    clasificacion_badge.short_description = 'Clasificación'
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html('<span class="badge bg-success">Activo</span>')
        return format_html('<span class="badge bg-secondary">Inactivo</span>')
    activo_badge.short_description = 'Estado'
    
    def activar_codigos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f'{updated} códigos de alerta activados.')
    activar_codigos.short_description = "Activar códigos seleccionados"
    
    def desactivar_codigos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f'{updated} códigos de alerta desactivados.')
    desactivar_codigos.short_description = "Desactivar códigos seleccionados"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo código
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


# Personalización del sitio de administración
admin.site.site_header = "Centro de Soluciones Conectadas - Patagonia Maquinarias"
admin.site.site_title = "Centro de Soluciones"
admin.site.index_title = "Panel de Administración"
