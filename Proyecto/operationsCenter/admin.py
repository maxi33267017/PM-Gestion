from django.contrib import admin
from .models import (
    OperationsCenterConfig, Machine, MachineLocation, MachineEngineHours,
    MachineAlert, MachineHoursOfOperation, DeviceStateReport,
    TelemetryReport, TelemetryReportMachine
)


@admin.register(OperationsCenterConfig)
class OperationsCenterConfigAdmin(admin.ModelAdmin):
    list_display = ['organization_id', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['organization_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Configuración API', {
            'fields': ('client_id', 'client_secret', 'redirect_uri', 'organization_id')
        }),
        ('Tokens', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['machine_id', 'serial_number', 'make_name', 'model_name', 'equipo_local', 'is_active', 'last_sync']
    list_filter = ['is_active', 'make_name', 'last_sync']
    search_fields = ['machine_id', 'serial_number', 'model_name', 'make_name']
    readonly_fields = ['created_at', 'updated_at', 'last_sync']
    
    fieldsets = (
        ('Información de la Máquina', {
            'fields': ('machine_id', 'equipment_id', 'serial_number', 'model_name', 'make_name', 'year', 'description')
        }),
        ('Relación Local', {
            'fields': ('equipo_local',)
        }),
        ('Ubicación Actual', {
            'fields': ('last_location_lat', 'last_location_lng', 'last_location_timestamp'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active', 'last_sync', 'created_at', 'updated_at')
        }),
    )


@admin.register(MachineLocation)
class MachineLocationAdmin(admin.ModelAdmin):
    list_display = ['machine', 'latitude', 'longitude', 'timestamp', 'speed']
    list_filter = ['timestamp', 'machine']
    search_fields = ['machine__machine_id', 'machine__serial_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(MachineEngineHours)
class MachineEngineHoursAdmin(admin.ModelAdmin):
    list_display = ['machine', 'engine_hours', 'timestamp']
    list_filter = ['timestamp', 'machine']
    search_fields = ['machine__machine_id', 'machine__serial_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(MachineAlert)
class MachineAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_id', 'machine', 'severity', 'status', 'category', 'timestamp']
    list_filter = ['severity', 'status', 'category', 'timestamp']
    search_fields = ['alert_id', 'machine__machine_id', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Información de la Alerta', {
            'fields': ('alert_id', 'machine', 'severity', 'status', 'category', 'description')
        }),
        ('Fechas', {
            'fields': ('timestamp', 'acknowledged_at', 'resolved_at')
        }),
        ('Relación Local', {
            'fields': ('servicio_relacionado',)
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MachineHoursOfOperation)
class MachineHoursOfOperationAdmin(admin.ModelAdmin):
    list_display = ['machine', 'hours_of_operation', 'timestamp']
    list_filter = ['timestamp', 'machine']
    search_fields = ['machine__machine_id', 'machine__serial_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(DeviceStateReport)
class DeviceStateReportAdmin(admin.ModelAdmin):
    list_display = ['machine', 'device_state', 'signal_strength', 'battery_level', 'timestamp']
    list_filter = ['device_state', 'timestamp', 'machine']
    search_fields = ['machine__machine_id', 'machine__serial_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(TelemetryReport)
class TelemetryReportAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'report_type', 'status', 'start_date', 'end_date', 'sent_at']
    list_filter = ['report_type', 'status', 'start_date', 'end_date']
    search_fields = ['cliente__razon_social']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información del Reporte', {
            'fields': ('cliente', 'report_type', 'status', 'start_date', 'end_date')
        }),
        ('Archivo', {
            'fields': ('report_file',)
        }),
        ('Envío', {
            'fields': ('sent_to', 'sent_at')
        }),
        ('Configuración', {
            'fields': ('include_location', 'include_hours', 'include_alerts', 'include_usage'),
            'classes': ('collapse',)
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TelemetryReportMachine)
class TelemetryReportMachineAdmin(admin.ModelAdmin):
    list_display = ['report', 'machine', 'total_hours', 'total_distance', 'alerts_count']
    list_filter = ['report__report_type', 'report__status']
    search_fields = ['report__cliente__razon_social', 'machine__serial_number']
    readonly_fields = ['created_at']
