from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Campania, Contacto, AnalisisCliente, PaqueteServicio, ClientePaquete,
    Campana, EmbudoVentas, ContactoCliente, SugerenciaMejora, PotencialCompraModelo
)

# ============================================================================
# ADMIN PARA CAMPAÑAS LEGACY
# ============================================================================

@admin.register(Campania)
class CampaniaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'fecha_inicio', 'fecha_fin', 'estado', 'valor_paquete', 'objetivo_paquetes']
    list_filter = ['estado', 'fecha_inicio', 'fecha_fin']
    search_fields = ['nombre', 'descripcion']
    date_hierarchy = 'fecha_inicio'

@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'campania', 'fecha_contacto', 'responsable', 'resultado', 'valor_venta_display']
    list_filter = ['resultado', 'fecha_contacto', 'campania']
    search_fields = ['cliente__razon_social', 'cliente__cuit', 'observaciones']
    date_hierarchy = 'fecha_contacto'
    
    def valor_venta_display(self, obj):
        if obj.valor_venta:
            return f"${obj.valor_venta:,.2f}"
        return "-"
    valor_venta_display.short_description = 'Valor Venta'

# ============================================================================
# ADMIN PARA NUEVAS FUNCIONALIDADES CRM
# ============================================================================

@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sucursal', 'tipo_equipo', 'modelo_equipo', 'fecha_inicio', 'fecha_fin', 'activa', 'presupuesto_display']
    list_filter = ['activa', 'fecha_inicio', 'sucursal', 'tipo_equipo']
    search_fields = ['nombre', 'descripcion']
    date_hierarchy = 'fecha_inicio'
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'sucursal', 'activa')
        }),
        ('Segmentación por Equipos', {
            'fields': ('tipo_equipo', 'modelo_equipo'),
            'description': 'Dejar vacío para incluir todos los equipos'
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Objetivos', {
            'fields': ('presupuesto', 'objetivo_contactos', 'objetivo_ventas')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def presupuesto_display(self, obj):
        if obj.presupuesto:
            return f"${obj.presupuesto:,.2f}"
        return "-"
    presupuesto_display.short_description = 'Presupuesto'

@admin.register(EmbudoVentas)
class EmbudoVentasAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'etapa_badge', 'origen_badge', 'valor_estimado_display', 'fecha_ingreso'
    ]
    list_filter = ['etapa', 'origen', 'fecha_ingreso', 'campana']
    search_fields = [
        'cliente__razon_social', 'cliente__cuit', 'descripcion_negocio', 'observaciones'
    ]
    date_hierarchy = 'fecha_ingreso'
    
    readonly_fields = [
        'fecha_creacion', 'fecha_modificacion', 'fecha_ingreso', 'fecha_ultima_actividad'
    ]
    
    actions = ['mover_a_etapa']
    
    def etapa_badge(self, obj):
        colors = {
            'CONTACTO_INICIAL': 'primary',
            'CALIFICACION': 'info',
            'PROPUESTA': 'warning',
            'NEGOCIACION': 'orange',
            'CIERRE': 'success',
            'PERDIDO': 'danger',
        }
        color = colors.get(obj.etapa, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_etapa_display()
        )
    etapa_badge.short_description = 'Etapa'
    
    def origen_badge(self, obj):
        colors = {
            'ALERTA_EQUIPO': 'success',
            'LEAD_JD': 'primary',
            'REFERENCIA': 'info',
            'MARKETING': 'warning',
            'SERVICIO_EXISTENTE': 'secondary',
            'OTRO': 'dark',
        }
        color = colors.get(obj.origen, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_origen_display()
        )
    origen_badge.short_description = 'Origen'
    
    def valor_estimado_display(self, obj):
        if obj.valor_estimado:
            return f"${obj.valor_estimado:,.2f}"
        return "-"
    valor_estimado_display.short_description = 'Valor Estimado'
    
    def mover_a_etapa(self, request, queryset):
        updated = queryset.update(etapa='CALIFICACION')
        self.message_user(request, f'{updated} embudos movidos a Calificación.')
    mover_a_etapa.short_description = "Mover a Calificación"

@admin.register(ContactoCliente)
class ContactoClienteAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'tipo_contacto_badge', 'fecha_contacto', 'responsable', 
        'resultado_badge'
    ]
    list_filter = [
        'tipo_contacto', 'resultado', 'fecha_contacto', 'responsable'
    ]
    search_fields = [
        'cliente__razon_social', 'cliente__cuit', 'descripcion', 'observaciones'
    ]
    date_hierarchy = 'fecha_contacto'
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def tipo_contacto_badge(self, obj):
        colors = {
            'TELEFONO': 'primary',
            'EMAIL': 'info',
            'WHATSAPP': 'success',
            'VISITA': 'warning',
            'VIDEO_LLAMADA': 'danger',
            'REUNION': 'secondary',
            'PRESENTACION': 'dark',
        }
        color = colors.get(obj.tipo_contacto, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_tipo_contacto_display()
        )
    tipo_contacto_badge.short_description = 'Tipo'
    
    def resultado_badge(self, obj):
        colors = {
            'EXITOSO': 'success',
            'NO_CONTESTA': 'danger',
            'REPROGRAMADO': 'warning',
            'CANCELADO': 'secondary',
            'VENTA': 'primary',
            'OBJECCION': 'info',
        }
        color = colors.get(obj.resultado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_resultado_display()
        )
    resultado_badge.short_description = 'Resultado'

@admin.register(SugerenciaMejora)
class SugerenciaMejoraAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'categoria_badge', 'estado_badge', 'impacto_badge', 
        'prioridad_badge', 'fecha_sugerencia'
    ]
    list_filter = [
        'estado', 'categoria', 'impacto_estimado', 'prioridad', 'fecha_sugerencia'
    ]
    search_fields = [
        'titulo', 'descripcion', 'respuesta_gerencia', 'accion_especifica'
    ]
    date_hierarchy = 'fecha_sugerencia'
    
    readonly_fields = ['fecha_sugerencia']
    
    actions = ['marcar_en_analisis', 'aprobar_sugerencia', 'implementar_sugerencia']
    
    def categoria_badge(self, obj):
        colors = {
            'PROCESOS': 'primary',
            'EQUIPOS': 'info',
            'SEGURIDAD': 'danger',
            'CALIDAD': 'success',
            'MANTENIMIENTO': 'warning',
            'ATENCION_CLIENTE': 'secondary',
            'FORMACION': 'dark',
            'TECNOLOGIA': 'purple',
            'AMBIENTE': 'green',
            'OTROS': 'gray',
        }
        color = colors.get(obj.categoria, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_categoria_display()
        )
    categoria_badge.short_description = 'Categoría'
    
    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': 'warning',
            'EN_ANALISIS': 'info',
            'APROBADA': 'success',
            'IMPLEMENTADA': 'primary',
            'RECHAZADA': 'danger',
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def impacto_badge(self, obj):
        colors = {
            'BAJO': 'success',
            'MEDIO': 'warning',
            'ALTO': 'danger',
            'CRITICO': 'dark',
        }
        color = colors.get(obj.impacto_estimado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_impacto_estimado_display()
        )
    impacto_badge.short_description = 'Impacto'
    
    def prioridad_badge(self, obj):
        colors = {
            'BAJA': 'success',
            'MEDIA': 'warning',
            'ALTA': 'danger',
            'URGENTE': 'dark',
        }
        color = colors.get(obj.prioridad, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'
    
    def marcar_en_analisis(self, request, queryset):
        updated = queryset.update(estado='EN_ANALISIS', fecha_revision=timezone.now())
        self.message_user(request, f'{updated} sugerencias marcadas como en análisis.')
    marcar_en_analisis.short_description = "Marcar como En Análisis"
    
    def aprobar_sugerencia(self, request, queryset):
        updated = queryset.update(estado='APROBADA')
        self.message_user(request, f'{updated} sugerencias aprobadas.')
    aprobar_sugerencia.short_description = "Aprobar Sugerencias"
    
    def implementar_sugerencia(self, request, queryset):
        updated = queryset.update(
            estado='IMPLEMENTADA', 
            fecha_implementacion=timezone.now()
        )
        self.message_user(request, f'{updated} sugerencias marcadas como implementadas.')
    implementar_sugerencia.short_description = "Marcar como Implementadas"

# ============================================================================
# ADMIN PARA PAQUETES Y ANÁLISIS
# ============================================================================

@admin.register(PaqueteServicio)
class PaqueteServicioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio_display', 'estado', 'fecha_creacion']
    list_filter = ['estado', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    filter_horizontal = ['servicios']
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def precio_display(self, obj):
        return f"${obj.precio:,.2f}"
    precio_display.short_description = 'Precio'

@admin.register(ClientePaquete)
class ClientePaqueteAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'paquete', 'fecha_inicio', 'fecha_fin', 'estado_badge']
    list_filter = ['estado', 'fecha_inicio', 'paquete']
    search_fields = ['cliente__razon_social', 'paquete__nombre']
    date_hierarchy = 'fecha_inicio'
    
    def estado_badge(self, obj):
        colors = {
            'ACTIVO': 'success',
            'FINALIZADO': 'secondary',
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

@admin.register(AnalisisCliente)
class AnalisisClienteAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'categoria_badge', 'ultima_actualizacion'
    ]
    list_filter = ['categoria', 'ultima_actualizacion']
    search_fields = ['cliente__razon_social', 'cliente__cuit']
    
    readonly_fields = ['ultima_actualizacion']
    
    def categoria_badge(self, obj):
        colors = {
            'A': 'success',
            'B': 'warning',
            'C': 'danger',
        }
        color = colors.get(obj.categoria, 'secondary')
        return format_html(
            '<span class="badge bg-{}">Categoría {}</span>',
            color, obj.categoria
        )
    categoria_badge.short_description = 'Categoría'

@admin.register(PotencialCompraModelo)
class PotencialCompraModeloAdmin(admin.ModelAdmin):
    list_display = ['modelo', 'potencial_anual_display', 'horas_uso_estimadas']
    search_fields = ['modelo__nombre']
    
    def potencial_anual_display(self, obj):
        return f"${obj.potencial_anual:,.2f}"
    potencial_anual_display.short_description = 'Potencial Anual USD' 