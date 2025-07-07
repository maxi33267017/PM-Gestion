from django.contrib import admin
from .models import (
    PreOrden, Servicio, PedidoRepuestosTerceros, GastoAsistencia,
    VentaRepuesto, Revision5S, PlanAccion5S, CostoPersonalTaller,
    AnalisisTaller, Evidencia, ChecklistSalidaCampo, EncuestaServicio,
    RespuestaEncuesta, InsatisfaccionCliente, LogCambioServicio, ObservacionServicio
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
    list_display = [ 'get_cliente', 'fecha_servicio', 'estado']
    list_filter = ['estado', 'fecha_servicio']
    search_fields = [ 'preorden__cliente__nombre']

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

@admin.register(PlanAccion5S)
class PlanAccion5SAdmin(admin.ModelAdmin):
    list_display = ['revision', 'item_no_conforme', 'estado', 'fecha_limite']
    list_filter = ['estado', 'fecha_limite']


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
    list_display = ('id', 'encuesta', 'calificacion', 'fecha_respuesta')
    list_filter = ('calificacion', 'fecha_respuesta')
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

