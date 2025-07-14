from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    EquipoStock, Certificado, MovimientoStockCertificado, 
    VentaEquipo, TransferenciaEquipo, ChecklistProcesosJD
)


@admin.register(EquipoStock)
class EquipoStockAdmin(admin.ModelAdmin):
    list_display = [
        'numero_serie', 'modelo', 'tipo_equipo', 'estado', 
        'sucursal', 'fecha_compra_jd', 'dias_en_stock', 'costo_compra'
    ]
    list_filter = [
        'estado', 'sucursal', 'tipo_equipo', 'modelo__marca', 
        'fecha_compra_jd', 'año_fabricacion'
    ]
    search_fields = [
        'numero_serie', 'modelo__nombre', 'modelo__marca', 
        'numero_orden_compra', 'observaciones'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'dias_en_stock']
    
    fieldsets = (
        ('Información del Equipo', {
            'fields': ('numero_serie', 'modelo', 'tipo_equipo', 'año_fabricacion', 'color')
        }),
        ('Información de Compra', {
            'fields': ('fecha_compra_jd', 'numero_orden_compra', 'costo_compra')
        }),
        ('Estado y Ubicación', {
            'fields': ('estado', 'sucursal', 'ubicacion_fisica')
        }),
        ('Información Adicional', {
            'fields': ('observaciones',)
        }),
        ('Sistema', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def dias_en_stock(self, obj):
        return obj.dias_en_stock
    dias_en_stock.short_description = 'Días en Stock'


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'tipo', 'stock_disponible', 'stock_minimo', 
        'necesita_reposicion', 'costo', 'precio_venta', 'activo'
    ]
    list_filter = ['tipo', 'activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'necesita_reposicion']
    
    fieldsets = (
        ('Información del Certificado', {
            'fields': ('nombre', 'tipo', 'descripcion')
        }),
        ('Precios', {
            'fields': ('costo', 'precio_venta')
        }),
        ('Stock', {
            'fields': ('stock_disponible', 'stock_minimo')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Sistema', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def necesita_reposicion(self, obj):
        if obj.necesita_reposicion:
            return format_html('<span style="color: red;">⚠️ Necesita Reposición</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    necesita_reposicion.short_description = 'Estado Stock'


@admin.register(MovimientoStockCertificado)
class MovimientoStockCertificadoAdmin(admin.ModelAdmin):
    list_display = [
        'certificado', 'tipo_movimiento', 'cantidad', 
        'stock_anterior', 'stock_nuevo', 'usuario', 'fecha_movimiento'
    ]
    list_filter = [
        'tipo_movimiento', 'certificado__tipo', 'fecha_movimiento', 'usuario'
    ]
    search_fields = [
        'certificado__nombre', 'motivo', 'usuario__nombre', 'usuario__apellido'
    ]
    readonly_fields = ['fecha_movimiento']
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('certificado', 'tipo_movimiento', 'cantidad')
        }),
        ('Stock', {
            'fields': ('stock_anterior', 'stock_nuevo')
        }),
        ('Referencias', {
            'fields': ('venta', 'usuario')
        }),
        ('Información Adicional', {
            'fields': ('motivo', 'fecha_movimiento')
        }),
    )


@admin.register(VentaEquipo)
class VentaEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'equipo_stock', 'cliente', 'fecha_venta', 
        'precio_venta', 'estado', 'vendedor', 'total_certificados'
    ]
    list_filter = [
        'estado', 'fecha_venta', 'vendedor__sucursal', 
        'equipo_stock__tipo_equipo', 'equipo_stock__modelo__marca'
    ]
    search_fields = [
        'cliente__razon_social', 'cliente__cuit', 
        'equipo_stock__numero_serie', 'numero_factura'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'total_certificados']
    
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('equipo_stock', 'cliente', 'fecha_venta', 'precio_venta', 'numero_factura')
        }),
        ('Certificados', {
            'fields': ('certificado_garantia', 'certificado_garantia_extendida', 'certificado_svap')
        }),
        ('Estado y Usuario', {
            'fields': ('estado', 'vendedor')
        }),
        ('Información Adicional', {
            'fields': ('observaciones',)
        }),
        ('Sistema', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def total_certificados(self, obj):
        return obj.total_certificados
    total_certificados.short_description = 'Total Certificados'


@admin.register(TransferenciaEquipo)
class TransferenciaEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'venta', 'equipo_cliente', 'cliente', 
        'fecha_transferencia', 'checklist_completado', 'usuario_transferencia'
    ]
    list_filter = [
        'checklist_completado', 'fecha_transferencia', 
        'usuario_transferencia__sucursal'
    ]
    search_fields = [
        'venta__cliente__razon_social', 'equipo_cliente__numero_serie'
    ]
    readonly_fields = ['fecha_transferencia']
    
    fieldsets = (
        ('Información de la Transferencia', {
            'fields': ('venta', 'equipo_cliente')
        }),
        ('Checklist', {
            'fields': ('checklist_completado', 'fecha_checklist')
        }),
        ('Usuario y Fechas', {
            'fields': ('usuario_transferencia', 'fecha_transferencia')
        }),
        ('Información Adicional', {
            'fields': ('observaciones',)
        }),
    )
    
    def cliente(self, obj):
        return obj.venta.cliente
    cliente.short_description = 'Cliente'
