from django.contrib import admin
from .models import (
    PreOrden, Servicio, PedidoRepuestosTerceros, GastoAsistencia,
    VentaRepuesto, Revision5S, PlanAccion5S, ItemPlanAccion5S, EvidenciaPlanAccion5S, CostoPersonalTaller,
    AnalisisTaller, Evidencia, ChecklistSalidaCampo, EncuestaServicio,
    RespuestaEncuesta, InsatisfaccionCliente, LogCambioServicio, ObservacionServicio,
    EvidenciaRevision5S, Repuesto, HerramientaEspecial, ReservaHerramienta, LogHerramienta,
    HerramientaPersonal, AsignacionHerramientaPersonal, AuditoriaHerramientaPersonal, DetalleAuditoriaHerramienta, ItemHerramientaPersonal, LogCambioItemHerramienta,
    Tarifario, TarifarioModeloEquipo
)



@admin.register(PreOrden)
class PreOrdenAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'equipo', 'fecha_estimada', 'tipo_trabajo', 'activo']
    list_filter = [ 'tipo_trabajo', 'activo']
    search_fields = ['cliente__razon_social', 'equipo__numero_serie', 'numero']

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     # Optimizar consultas relacionadas
    #     return qs.select_related('cliente', 'equipo', 'sucursal').prefetch_related('tecnicos')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = [ 'get_cliente', 'fecha_servicio', 'orden_servicio', 'estado']
    list_filter = ['estado', 'fecha_servicio']
    search_fields = [ 'preorden__cliente__nombre', 'orden_servicio']
    fieldsets = (
        ('Información Básica', {
            'fields': ('preorden', 'fecha_servicio', 'horometro_servicio', 'orden_servicio', 'estado', 'trabajo', 'prioridad')
        }),
        ('Documentación', {
            'fields': ('numero_factura', 'archivo_factura', 'numero_cotizacion', 'archivo_cotizacion', 'archivo_informe')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'valor_mano_obra', 'causa', 'accion_correctiva', 'ubicacion', 'kilometros', 'firma_cliente', 'nombre_cliente')
        }),
    )

    def get_cliente(self, obj):
        return obj.preorden.cliente.razon_social
    get_cliente.short_description = 'Cliente'

@admin.register(PedidoRepuestosTerceros)
class PedidoRepuestosTercerosAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'proveedor', 'fecha_pedido', 'estado']
    list_filter = ['estado', 'fecha_pedido']
    search_fields = ['numero_pedido', 'proveedor']





@admin.register(VentaRepuesto)
class VentaRepuestoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descripcion', 'cantidad', 'precio_unitario']
    search_fields = ['codigo', 'descripcion']

@admin.register(Revision5S)
class Revision5SAdmin(admin.ModelAdmin):
    list_display = ['sucursal', 'evaluador', 'fecha_revision']
    list_filter = ['sucursal', 'fecha_revision']

@admin.register(EvidenciaPlanAccion5S)
class EvidenciaPlanAccion5SAdmin(admin.ModelAdmin):
    list_display = ['plan_accion', 'descripcion', 'fecha_subida']
    list_filter = ['fecha_subida']
    search_fields = ['plan_accion__item_no_conforme', 'descripcion']

@admin.register(PlanAccion5S)
class PlanAccion5SAdmin(admin.ModelAdmin):
    list_display = ['revision', 'item_no_conforme', 'estado', 'fecha_limite']
    list_filter = ['estado', 'fecha_limite']


@admin.register(ItemPlanAccion5S)
class ItemPlanAccion5SAdmin(admin.ModelAdmin):
    list_display = [
        'plan_accion', 
        'item_no_conforme', 
        'responsable', 
        'estado', 
        'fecha_limite',
        'esta_vencido_display',
        'dias_restantes_display'
    ]
    list_filter = [
        'estado', 
        'fecha_limite', 
        'plan_accion__revision__sucursal',
        'responsable__rol'
    ]
    search_fields = [
        'item_no_conforme', 
        'responsable__nombre', 
        'responsable__apellido',
        'plan_accion__revision__sucursal__nombre'
    ]
    date_hierarchy = 'fecha_limite'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Item', {
            'fields': ('plan_accion', 'item_no_conforme', 'responsable')
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_limite', 'fecha_completado'),
        }),
        ('Información de Corrección', {
            'fields': ('comentario_correccion', 'evidencia_foto', 'observaciones'),
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    actions = ['marcar_completado', 'marcar_en_proceso', 'marcar_pendiente']
    
    def marcar_completado(self, request, queryset):
        updated = queryset.update(estado='COMPLETADO')
        self.message_user(request, f'{updated} items marcados como completados.')
    marcar_completado.short_description = "Marcar como completado"
    
    def marcar_en_proceso(self, request, queryset):
        updated = queryset.update(estado='EN_PROCESO')
        self.message_user(request, f'{updated} items marcados como en proceso.')
    marcar_en_proceso.short_description = "Marcar como en proceso"
    
    def marcar_pendiente(self, request, queryset):
        updated = queryset.update(estado='PENDIENTE')
        self.message_user(request, f'{updated} items marcados como pendientes.')
    marcar_pendiente.short_description = "Marcar como pendiente"
    
    def esta_vencido_display(self, obj):
        return obj.esta_vencido
    esta_vencido_display.boolean = True
    esta_vencido_display.short_description = 'Vencido'
    
    def dias_restantes_display(self, obj):
        if obj.estado == 'COMPLETADO':
            return 'Completado'
        dias = obj.dias_restantes
        if dias < 0:
            return f'Vencido ({abs(dias)} días)'
        elif dias <= 3:
            return f'⚠️ {dias} días'
        else:
            return f'{dias} días'
    dias_restantes_display.short_description = 'Días Restantes'


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ['preorden', 'imagen_preview', 'fecha_subida']
    list_filter = ['fecha_subida', 'preorden__tipo_trabajo']
    search_fields = ['preorden__numero', 'preorden__cliente__razon_social']
    readonly_fields = ['fecha_subida', 'imagen_preview']
    date_hierarchy = 'fecha_subida'
    
    fieldsets = (
        ('Información de la Evidencia', {
            'fields': ('preorden', 'imagen')
        }),
        ('Vista Previa', {
            'fields': ('imagen_preview',),
            'classes': ('collapse',)
        }),
        ('Información del Sistema', {
            'fields': ('fecha_subida',),
            'classes': ('collapse',)
        }),
    )
    
    def imagen_preview(self, obj):
        if obj.imagen:
            return f'<img src="{obj.imagen.url}" style="max-width: 200px; max-height: 200px;" />'
        return "Sin imagen"
    imagen_preview.short_description = 'Vista Previa'
    imagen_preview.allow_tags = True


@admin.register(EvidenciaRevision5S)
class EvidenciaRevision5SAdmin(admin.ModelAdmin):
    list_display = ['revision', 'descripcion', 'fecha_subida']
    list_filter = ['fecha_subida', 'revision__sucursal']
    search_fields = ['revision__sucursal__nombre', 'descripcion']
    readonly_fields = ['fecha_subida']


@admin.register(CostoPersonalTaller)
class CostoPersonalTallerAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'sucursal', 'salario_base', 'fecha_vigencia']
    list_filter = ['sucursal', 'fecha_vigencia']

@admin.register(AnalisisTaller)
class AnalisisTallerAdmin(admin.ModelAdmin):
    list_display = ['sucursal', 'mes', 'facturacion_mano_obra', 'facturacion_repuestos']
    list_filter = ['sucursal', 'mes']

@admin.register(GastoAsistencia)
class GastoAsistenciaAdmin(admin.ModelAdmin):
    list_display = ['servicio', 'monto', 'fecha']
    list_filter = ['servicio', 'monto', 'fecha']

@admin.register(EncuestaServicio)
class EncuestaServicioAdmin(admin.ModelAdmin):
    list_display = ('id', 'servicio', 'fecha_envio', 'estado', 'fecha_respuesta')
    list_filter = ('estado', 'fecha_envio')
    search_fields = ('servicio__id', 'servicio__preorden__cliente__razon_social')
    readonly_fields = ('fecha_envio', 'fecha_respuesta')
    ordering = ('-fecha_envio',)

@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'encuesta', 'cumplimiento_acuerdo', 'probabilidad_recomendacion', 'fecha_respuesta')
    list_filter = ('cumplimiento_acuerdo', 'probabilidad_recomendacion', 'fecha_respuesta')
    search_fields = ('encuesta__servicio__id', 'encuesta__servicio__preorden__cliente__razon_social')
    readonly_fields = ('fecha_respuesta',)
    ordering = ('-fecha_respuesta',)

@admin.register(InsatisfaccionCliente)
class InsatisfaccionClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'encuesta', 'fecha_comunicacion', 'responsable', 'estado', 'fecha_solucion')
    list_filter = ('estado', 'fecha_comunicacion', 'fecha_solucion')
    search_fields = ('encuesta__servicio__id', 'encuesta__servicio__preorden__cliente__razon_social', 'responsable__username')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    ordering = ('-fecha_creacion',)

@admin.register(LogCambioServicio)
class LogCambioServicioAdmin(admin.ModelAdmin):
    list_display = ['servicio', 'usuario', 'estado_anterior', 'estado_nuevo', 'fecha_cambio']
    list_filter = ['estado_anterior', 'estado_nuevo', 'fecha_cambio', 'usuario__rol']
    search_fields = ['servicio__id', 'usuario__nombre', 'motivo']
    readonly_fields = ['servicio', 'usuario', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'ip_address']
    ordering = ['-fecha_cambio']
    
    def has_add_permission(self, request):
        return False  # No permitir crear logs manualmente
    
    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Solo superusuarios pueden eliminar logs


@admin.register(ObservacionServicio)
class ObservacionServicioAdmin(admin.ModelAdmin):
    list_display = ['servicio', 'usuario', 'fecha_creacion', 'observacion_corta']
    list_filter = ['fecha_creacion', 'usuario__rol']
    search_fields = ['servicio__id', 'usuario__nombre', 'observacion']
    readonly_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']
    
    def observacion_corta(self, obj):
        return obj.observacion[:100] + "..." if len(obj.observacion) > 100 else obj.observacion
    observacion_corta.short_description = 'Observación'


@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 
        'descripcion_corta', 
        'costo', 
        'precio_venta', 
        'margen_ganancia_display',
        'categoria',
        'proveedor',
        'activo_badge'
    ]
    list_filter = [
        'categoria', 
        'proveedor', 
        'activo', 
        'fecha_creacion'
    ]
    search_fields = [
        'codigo', 
        'descripcion', 
        'categoria',
        'proveedor'
    ]
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'descripcion', 'categoria', 'proveedor', 'activo')
        }),
        ('Precios', {
            'fields': ('costo', 'precio_venta'),
            'classes': ('collapse',)
        }),
        ('Inventario', {
            'fields': ('stock_minimo', 'ubicacion_almacen'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    actions = ['activar_repuestos', 'desactivar_repuestos']
    
    def descripcion_corta(self, obj):
        if obj.descripcion:
            return obj.descripcion[:50] + "..." if len(obj.descripcion) > 50 else obj.descripcion
        return "Sin descripción"
    descripcion_corta.short_description = 'Descripción'
    
    def margen_ganancia_display(self, obj):
        margen = obj.margen_ganancia
        if margen > 0:
            return f"{margen:.1f}%"
        return "-"
    margen_ganancia_display.short_description = 'Margen'
    
    def activo_badge(self, obj):
        if obj.activo:
            return '<span style="color: green;">✓ Activo</span>'
        return '<span style="color: red;">✗ Inactivo</span>'
    activo_badge.short_description = 'Estado'
    activo_badge.allow_tags = True
    
    def activar_repuestos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f'{updated} repuestos activados.')
    activar_repuestos.short_description = "Activar repuestos seleccionados"
    
    def desactivar_repuestos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f'{updated} repuestos desactivados.')
    desactivar_repuestos.short_description = "Desactivar repuestos seleccionados"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo repuesto
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(HerramientaEspecial)
class HerramientaEspecialAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 
        'nombre', 
        'ubicacion', 
        'cantidad', 
        'estado_actual_display',
        'creado_por'
    ]
    list_filter = [
        'ubicacion', 
        'cantidad', 
        'fecha_creacion',
        'creado_por__rol'
    ]
    search_fields = [
        'codigo', 
        'nombre', 
        'ubicacion',
        'nota'
    ]
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'cantidad', 'ubicacion')
        }),
        ('Información Adicional', {
            'fields': ('foto', 'nota'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def estado_actual_display(self, obj):
        if obj.disponible:
            return '<span style="color: green;">✓ Disponible</span>'
        else:
            return '<span style="color: red;">✗ No Disponible</span>'
    estado_actual_display.short_description = 'Estado'
    estado_actual_display.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva herramienta
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReservaHerramienta)
class ReservaHerramientaAdmin(admin.ModelAdmin):
    list_display = [
        'herramienta', 
        'usuario', 
        'fecha_reserva', 
        'estado_display',
        'preorden_servicio_display'
    ]
    list_filter = [
        'estado', 
        'fecha_reserva', 
        'fecha_creacion',
        'usuario__rol'
    ]
    search_fields = [
        'herramienta__codigo', 
        'herramienta__nombre', 
        'usuario__nombre',
        'observaciones'
    ]
    date_hierarchy = 'fecha_reserva'
    list_per_page = 25
    
    fieldsets = (
        ('Información de la Reserva', {
            'fields': ('herramienta', 'usuario', 'fecha_reserva', 'estado')
        }),
        ('Asociaciones', {
            'fields': ('preorden', 'servicio'),
            'classes': ('collapse',)
        }),
        ('Fechas de Movimiento', {
            'fields': ('fecha_retiro', 'fecha_devolucion'),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('observaciones',)
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def estado_display(self, obj):
        colors = {
            'RESERVADA': 'blue',
            'RETIRADA': 'orange',
            'DEVUELTA': 'green',
            'CANCELADA': 'red'
        }
        color = colors.get(obj.estado, 'gray')
        return f'<span style="color: {color};">{obj.get_estado_display()}</span>'
    estado_display.short_description = 'Estado'
    estado_display.allow_tags = True
    
    def preorden_servicio_display(self, obj):
        if obj.preorden:
            return f'PO: {obj.preorden.numero}'
        elif obj.servicio:
            return f'Servicio: {obj.servicio.id}'
        return 'Sin asociación'
    preorden_servicio_display.short_description = 'Pre-Orden/Servicio'


@admin.register(LogHerramienta)
class LogHerramientaAdmin(admin.ModelAdmin):
    list_display = [
        'herramienta', 
        'usuario', 
        'accion_display', 
        'fecha',
        'reserva_display'
    ]
    list_filter = [
        'accion', 
        'fecha', 
        'usuario__rol'
    ]
    search_fields = [
        'herramienta__codigo', 
        'herramienta__nombre', 
        'usuario__nombre',
        'observaciones'
    ]
    date_hierarchy = 'fecha'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Log', {
            'fields': ('herramienta', 'usuario', 'accion', 'fecha')
        }),
        ('Asociaciones', {
            'fields': ('reserva',),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('observaciones',)
        }),
    )
    
    readonly_fields = ['fecha']
    
    def accion_display(self, obj):
        colors = {
            'RESERVA': 'blue',
            'RETIRO': 'orange',
            'DEVOLUCION': 'green',
            'CANCELACION': 'red'
        }
        color = colors.get(obj.accion, 'gray')
        return f'<span style="color: {color};">{obj.get_accion_display()}</span>'
    accion_display.short_description = 'Acción'
    accion_display.allow_tags = True
    
    def reserva_display(self, obj):
        if obj.reserva:
            return f'Reserva #{obj.reserva.id}'
        return '-'
    reserva_display.short_description = 'Reserva'
    
    def has_add_permission(self, request):
        return False  # No permitir crear logs manualmente
    
    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Solo superusuarios pueden eliminar logs


@admin.register(HerramientaPersonal)
class HerramientaPersonalAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 
        'nombre', 
        'categoria', 
        'marca', 
        'estado_display',
        'certificacion_display',
        'costo_reposicion_display',
        'vida_util_display',
        'activo_badge'
    ]
    list_filter = [
        'categoria', 
        'estado',
        'marca', 
        'activo', 
        'fecha_creacion',
        'fecha_vencimiento_certificacion'
    ]
    search_fields = [
        'codigo', 
        'nombre', 
        'marca',
        'modelo'
    ]
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'categoria', 'marca', 'modelo', 'estado', 'activo')
        }),
        ('Certificación', {
            'fields': ('fecha_certificacion', 'fecha_vencimiento_certificacion'),
            'classes': ('collapse',)
        }),
        ('Información Técnica', {
            'fields': ('descripcion', 'costo_reposicion', 'vida_util_meses'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']

    actions = ['marcar_disponible', 'marcar_mantenimiento', 'exportar_certificaciones_vencidas']

    def marcar_disponible(self, request, queryset):
        updated = queryset.update(estado='DISPONIBLE')
        self.message_user(request, f'{updated} herramientas marcadas como disponibles.')
    marcar_disponible.short_description = "Marcar como disponibles"

    def marcar_mantenimiento(self, request, queryset):
        updated = queryset.update(estado='MANTENIMIENTO')
        self.message_user(request, f'{updated} herramientas marcadas en mantenimiento.')
    marcar_mantenimiento.short_description = "Marcar en mantenimiento"

    def exportar_certificaciones_vencidas(self, request, queryset):
        from django.http import HttpResponse
        import csv
        from django.utils import timezone

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="certificaciones_vencidas.csv"'

        writer = csv.writer(response)
        writer.writerow(['Código', 'Nombre', 'Categoría', 'Fecha Vencimiento', 'Días Vencida'])

        for herramienta in queryset.filter(fecha_vencimiento_certificacion__lt=timezone.now().date()):
            dias_vencida = (timezone.now().date() - herramienta.fecha_vencimiento_certificacion).days
            writer.writerow([
                herramienta.codigo,
                herramienta.nombre,
                herramienta.get_categoria_display(),
                herramienta.fecha_vencimiento_certificacion,
                dias_vencida
            ])

        return response
    exportar_certificaciones_vencidas.short_description = "Exportar certificaciones vencidas"
    
    def estado_display(self, obj):
        colors = {
            'DISPONIBLE': 'green',
            'ASIGNADA': 'blue',
            'MANTENIMIENTO': 'orange',
            'PERDIDA': 'red',
            'DAÑADA': 'red',
            'VENCIDA': 'purple'
        }
        color = colors.get(obj.estado, 'gray')
        return f'<span style="color: {color}; font-weight: bold;">{obj.get_estado_display()}</span>'
    estado_display.short_description = 'Estado'
    estado_display.allow_tags = True
    
    def certificacion_display(self, obj):
        if not obj.fecha_vencimiento_certificacion:
            return '<span style="color: gray;">Sin certificación</span>'
        
        if obj.certificacion_vencida:
            return f'<span style="color: red; font-weight: bold;">Vencida ({obj.fecha_vencimiento_certificacion})</span>'
        elif obj.certificacion_proxima_vencer:
            return f'<span style="color: orange; font-weight: bold;">Próxima ({obj.fecha_vencimiento_certificacion})</span>'
        else:
            return f'<span style="color: green;">Vigente ({obj.fecha_vencimiento_certificacion})</span>'
    certificacion_display.short_description = 'Certificación'
    certificacion_display.allow_tags = True
    
    def costo_reposicion_display(self, obj):
        if obj.costo_reposicion:
            return f"${obj.costo_reposicion:,.2f}"
        return '-'
    costo_reposicion_display.short_description = 'Costo Reposición'
    
    def vida_util_display(self, obj):
        if obj.vida_util_meses:
            return f"{obj.vida_util_meses} meses"
        return '-'
    vida_util_display.short_description = 'Vida Útil'
    
    def activo_badge(self, obj):
        if obj.activo:
            return '<span style="color: green;">✓ Activo</span>'
        else:
            return '<span style="color: red;">✗ Inactivo</span>'
    activo_badge.short_description = 'Estado'
    activo_badge.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva herramienta
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AsignacionHerramientaPersonal)
class AsignacionHerramientaPersonalAdmin(admin.ModelAdmin):
    list_display = [
        'tecnico', 
        'herramienta', 
        'fecha_asignacion', 
        'estado_display',
        'dias_asignada_display',
        'asignado_por'
    ]
    list_filter = [
        'estado_asignacion', 
        'fecha_asignacion', 
        'herramienta__categoria',
        'tecnico__rol'
    ]
    search_fields = [
        'tecnico__nombre', 
        'tecnico__apellido', 
        'herramienta__codigo',
        'herramienta__nombre'
    ]
    date_hierarchy = 'fecha_asignacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información de Asignación', {
            'fields': ('tecnico', 'herramienta', 'fecha_asignacion', 'estado_asignacion')
        }),
        ('Información Adicional', {
            'fields': ('observaciones_asignacion', 'asignado_por'),
            'classes': ('collapse',)
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def estado_display(self, obj):
        colors = {
            'ENTREGADA': 'green',
            'DEVUELTA': 'blue',
            'PERDIDA': 'red',
            'DAÑADA': 'orange',
            'VENCIDA': 'purple'
        }
        color = colors.get(obj.estado_asignacion, 'gray')
        return f'<span style="color: {color};">{obj.get_estado_asignacion_display()}</span>'
    estado_display.short_description = 'Estado'
    estado_display.allow_tags = True
    
    def dias_asignada_display(self, obj):
        dias = obj.dias_asignada
        if dias < 0:
            return f"{abs(dias)} días (futura)"
        return f"{dias} días"
    dias_asignada_display.short_description = 'Días Asignada'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva asignación
            obj.asignado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditoriaHerramientaPersonal)
class AuditoriaHerramientaPersonalAdmin(admin.ModelAdmin):
    list_display = [
        'tecnico', 
        'tipo_auditoria', 
        'fecha_auditoria', 
        'estado_general_display',
        'herramientas_auditadas_display',
        'auditor'
    ]
    list_filter = [
        'tipo_auditoria', 
        'estado_general', 
        'fecha_auditoria',
        'auditor__rol'
    ]
    search_fields = [
        'tecnico__nombre', 
        'tecnico__apellido', 
        'auditor__nombre',
        'auditor__apellido'
    ]
    date_hierarchy = 'fecha_auditoria'
    list_per_page = 25
    
    fieldsets = (
        ('Información de Auditoría', {
            'fields': ('tecnico', 'fecha_auditoria', 'tipo_auditoria', 'auditor')
        }),
        ('Resultados', {
            'fields': ('estado_general', 'observaciones_generales'),
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def estado_general_display(self, obj):
        colors = {
            'EXCELENTE': 'green',
            'BUENO': 'blue',
            'REGULAR': 'orange',
            'MALO': 'red'
        }
        color = colors.get(obj.estado_general, 'gray')
        return f'<span style="color: {color};">{obj.get_estado_general_display()}</span>'
    estado_general_display.short_description = 'Estado General'
    estado_general_display.allow_tags = True
    
    def herramientas_auditadas_display(self, obj):
        return f"{obj.herramientas_presentes}/{obj.herramientas_auditadas} presentes"
    herramientas_auditadas_display.short_description = 'Herramientas'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva auditoría
            obj.auditor = request.user
        super().save_model(request, obj, form, change)


@admin.register(DetalleAuditoriaHerramienta)
class DetalleAuditoriaHerramientaAdmin(admin.ModelAdmin):
    list_display = [
        'auditoria', 
        'herramienta', 
        'estado_herramienta_display', 
        'accion_requerida_display',
        'fecha_limite_accion'
    ]
    list_filter = [
        'estado_herramienta', 
        'accion_requerida', 
        'herramienta__categoria',
        'fecha_creacion'
    ]
    search_fields = [
        'auditoria__tecnico__nombre', 
        'herramienta__codigo', 
        'herramienta__nombre',
        'observaciones'
    ]
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Detalle', {
            'fields': ('auditoria', 'herramienta', 'estado_herramienta')
        }),
        ('Acciones', {
            'fields': ('accion_requerida', 'fecha_limite_accion', 'observaciones'),
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    def estado_herramienta_display(self, obj):
        colors = {
            'PRESENTE': 'green',
            'AUSENTE': 'red',
            'DAÑADA': 'orange',
            'DESGASTADA': 'yellow',
            'VENCIDA': 'purple'
        }
        color = colors.get(obj.estado_herramienta, 'gray')
        return f'<span style="color: {color};">{obj.get_estado_herramienta_display()}</span>'
    estado_herramienta_display.short_description = 'Estado'
    estado_herramienta_display.allow_tags = True
    
    def accion_requerida_display(self, obj):
        if obj.accion_requerida == 'NINGUNA':
            return '-'
        colors = {
            'REPOSICION': 'red',
            'REPARACION': 'orange',
            'LIMPIEZA': 'blue',
            'MANTENIMIENTO': 'purple'
        }
        color = colors.get(obj.accion_requerida, 'gray')
        return f'<span style="color: {color};">{obj.get_accion_requerida_display()}</span>'
    accion_requerida_display.short_description = 'Acción Requerida'
    accion_requerida_display.allow_tags = True


@admin.register(ItemHerramientaPersonal)
class ItemHerramientaPersonalAdmin(admin.ModelAdmin):
    list_display = [
        'herramienta', 'nombre', 'cantidad', 'estado', 'requiere_reposicion'
    ]
    list_filter = [
        'estado', 'herramienta__categoria', 'herramienta__estado'
    ]
    search_fields = [
        'nombre', 'herramienta__nombre', 'herramienta__codigo'
    ]
    list_editable = ['estado', 'cantidad']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información del Item', {
            'fields': ('herramienta', 'nombre', 'descripcion', 'cantidad', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def requiere_reposicion(self, obj):
        return obj.requiere_reposicion
    requiere_reposicion.boolean = True
    requiere_reposicion.short_description = 'Requiere Reposición'
    
    actions = ['marcar_presente', 'marcar_ausente', 'marcar_danado']
    
    def marcar_presente(self, request, queryset):
        updated = queryset.update(estado='PRESENTE')
        self.message_user(request, f'{updated} items marcados como presentes.')
    marcar_presente.short_description = 'Marcar como Presente'
    
    def marcar_ausente(self, request, queryset):
        updated = queryset.update(estado='AUSENTE')
        self.message_user(request, f'{updated} items marcados como ausentes.')
    marcar_ausente.short_description = 'Marcar como Ausente'
    
    def marcar_danado(self, request, queryset):
        updated = queryset.update(estado='DAÑADO')
        self.message_user(request, f'{updated} items marcados como dañados.')
    marcar_danado.short_description = 'Marcar como Dañado'


@admin.register(LogCambioItemHerramienta)
class LogCambioItemHerramientaAdmin(admin.ModelAdmin):
    list_display = [
        'item', 
        'auditoria', 
        'estado_anterior', 
        'estado_nuevo', 
        'fecha_cambio'
    ]
    list_filter = [
        'estado_anterior', 
        'estado_nuevo', 
        'fecha_cambio',
        'item__herramienta__categoria'
    ]
    search_fields = [
        'item__nombre', 
        'item__herramienta__codigo', 
        'auditoria__tecnico__nombre',
        'observaciones'
    ]
    date_hierarchy = 'fecha_cambio'
    list_per_page = 25
    
    fieldsets = (
        ('Información del Cambio', {
            'fields': ('item', 'auditoria', 'estado_anterior', 'estado_nuevo')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'fecha_cambio'),
        }),
    )
    
    readonly_fields = ['fecha_cambio']
    
    def has_add_permission(self, request):
        return False  # No permitir crear logs manualmente
    
    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Solo superusuarios pueden eliminar logs


# Admin para Tarifario
@admin.register(Tarifario)
class TarifarioAdmin(admin.ModelAdmin):
    list_display = [
        'fecha', 
        'nombre_servicio', 
        'precio_usd_display', 
        'tmo_display',
        'modelos_asociados_display',
        'creado_por', 
        'activo_badge'
    ]
    list_filter = [
        'fecha', 
        'activo', 
        'fecha_creacion',
        'creado_por__rol'
    ]
    search_fields = [
        'nombre_servicio', 
        'descripcion',
        'creado_por__nombre',
        'creado_por__apellido'
    ]
    date_hierarchy = 'fecha'
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('fecha', 'nombre_servicio', 'descripcion', 'precio_usd', 'activo')
        }),
        ('Información Técnica', {
            'fields': ('tmo_horas', 'actividades'),
            'description': 'Información técnica del servicio'
        }),
        ('Información de Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    actions = ['activar_tarifarios', 'desactivar_tarifarios']
    
    def precio_usd_display(self, obj):
        return f"${obj.precio_usd} USD"
    precio_usd_display.short_description = 'Precio USD'
    
    def tmo_display(self, obj):
        if obj.tmo_horas:
            return f"{obj.tmo_horas}h"
        return "-"
    tmo_display.short_description = 'TMO'
    
    def modelos_asociados_display(self, obj):
        modelos = obj.modelos_equipo.all()
        if modelos.count() > 3:
            return f"{modelos.count()} modelos"
        return ", ".join([f"{m.modelo_equipo.marca} {m.modelo_equipo.nombre}" for m in modelos[:3]])
    modelos_asociados_display.short_description = 'Modelos Asociados'
    
    def activo_badge(self, obj):
        if obj.activo:
            return '<span style="color: green;">✓ Activo</span>'
        return '<span style="color: red;">✗ Inactivo</span>'
    activo_badge.allow_tags = True
    activo_badge.short_description = 'Estado'
    
    def activar_tarifarios(self, request, queryset):
        queryset.update(activo=True)
        self.message_user(request, f"{queryset.count()} tarifarios activados exitosamente.")
    activar_tarifarios.short_description = "Activar tarifarios seleccionados"
    
    def desactivar_tarifarios(self, request, queryset):
        queryset.update(activo=False)
        self.message_user(request, f"{queryset.count()} tarifarios desactivados exitosamente.")
    desactivar_tarifarios.short_description = "Desactivar tarifarios seleccionados"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo objeto
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Agregar campo personalizado para modelos de equipo
        from django import forms
        from clientes.models import ModeloEquipo
        
        class TarifarioForm(form):
            modelos_equipo = forms.ModelMultipleChoiceField(
                queryset=ModeloEquipo.objects.filter(activo=True).select_related('tipo_equipo').order_by('tipo_equipo__nombre', 'nombre'),
                required=False,
                widget=forms.SelectMultiple(attrs={'size': '15'}),
                help_text="Selecciona los modelos de equipo a los que aplica este tarifario"
            )
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Personalizar las etiquetas de los modelos
                self.fields['modelos_equipo'].label_from_instance = lambda obj: f"{obj.tipo_equipo.nombre} - {obj.marca} {obj.nombre}"
                
                if obj:
                    # Pre-seleccionar modelos existentes
                    self.fields['modelos_equipo'].initial = [
                        relacion.modelo_equipo.id 
                        for relacion in obj.modelos_equipo.all()
                    ]
            
            def save(self, commit=True):
                tarifario = super().save(commit=False)
                if commit:
                    tarifario.save()
                    # Actualizar relaciones muchos a muchos
                    tarifario.modelos_equipo.clear()
                    for modelo in self.cleaned_data.get('modelos_equipo', []):
                        from .models import TarifarioModeloEquipo
                        TarifarioModeloEquipo.objects.create(
                            tarifario=tarifario,
                            modelo_equipo=modelo
                        )
                return tarifario
        
        return TarifarioForm


# Admin para TarifarioModeloEquipo (modelo intermedio)
@admin.register(TarifarioModeloEquipo)
class TarifarioModeloEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'tarifario', 
        'modelo_equipo_display', 
        'tipo_equipo_display'
    ]
    list_filter = [
        'modelo_equipo__tipo_equipo',
        'tarifario__activo'
    ]
    search_fields = [
        'tarifario__nombre_servicio',
        'modelo_equipo__nombre',
        'modelo_equipo__marca',
        'modelo_equipo__tipo_equipo__nombre'
    ]
    list_per_page = 25
    
    fieldsets = (
        ('Información de Relación', {
            'fields': ('tarifario', 'modelo_equipo')
        }),
    )
    
    def modelo_equipo_display(self, obj):
        return f"{obj.modelo_equipo.marca} {obj.modelo_equipo.nombre}"
    modelo_equipo_display.short_description = 'Modelo de Equipo'
    
    def tipo_equipo_display(self, obj):
        return obj.modelo_equipo.tipo_equipo.nombre
    tipo_equipo_display.short_description = 'Tipo de Equipo'

