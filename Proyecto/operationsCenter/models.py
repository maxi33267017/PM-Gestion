from django.db import models
from django.utils import timezone
from clientes.models import Cliente, Equipo
from gestionDeTaller.models import Servicio


class OperationsCenterConfig(models.Model):
    """Configuración para la API de John Deere Operations Center"""
    client_id = models.CharField(max_length=100, verbose_name="Client ID")
    client_secret = models.CharField(max_length=200, verbose_name="Client Secret")
    redirect_uri = models.URLField(verbose_name="Redirect URI")
    access_token = models.TextField(blank=True, null=True, verbose_name="Access Token")
    refresh_token = models.TextField(blank=True, null=True, verbose_name="Refresh Token")
    token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Token Expires At")
    organization_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Organization ID")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración Operations Center"
        verbose_name_plural = "Configuraciones Operations Center"

    def __str__(self):
        return f"Configuración OC - {self.organization_id or 'Sin organización'}"


class Machine(models.Model):
    """Máquinas sincronizadas desde Operations Center"""
    machine_id = models.CharField(max_length=100, unique=True, verbose_name="Machine ID")
    equipment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Equipment ID")
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Serie")
    model_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Modelo")
    make_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    year = models.IntegerField(blank=True, null=True, verbose_name="Año")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    # Relación con el equipo local
    equipo_local = models.ForeignKey(
        Equipo, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name="Equipo Local",
        related_name='machines_oc'
    )
    
    # Información de telemetría
    last_location_lat = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        blank=True, 
        null=True, 
        verbose_name="Última Latitud"
    )
    last_location_lng = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        blank=True, 
        null=True, 
        verbose_name="Última Longitud"
    )
    last_location_timestamp = models.DateTimeField(blank=True, null=True, verbose_name="Última Ubicación")
    
    # Estado de sincronización
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    last_sync = models.DateTimeField(blank=True, null=True, verbose_name="Última Sincronización")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Máquina Operations Center"
        verbose_name_plural = "Máquinas Operations Center"
        ordering = ['-last_sync']

    def __str__(self):
        return f"{self.make_name} {self.model_name} - {self.serial_number or self.machine_id}"

    def has_active_alerts(self):
        """Verificar si la máquina tiene alertas activas"""
        return self.alerts.filter(status='ACTIVE').exists()

    def get_active_alerts_count(self):
        """Obtener el número de alertas activas"""
        return self.alerts.filter(status='ACTIVE').count()


class MachineLocation(models.Model):
    """Historial de ubicaciones de las máquinas"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, verbose_name="Latitud")
    longitude = models.DecimalField(max_digits=11, decimal_places=8, verbose_name="Longitud")
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    altitude = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Altitud")
    speed = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, verbose_name="Velocidad")
    heading = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Dirección")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ubicación de Máquina"
        verbose_name_plural = "Ubicaciones de Máquinas"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['machine', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.machine} - {self.timestamp}"


class MachineEngineHours(models.Model):
    """Horas de motor de las máquinas"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='engine_hours')
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    engine_hours = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Horas de Motor")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horas de Motor"
        verbose_name_plural = "Horas de Motor"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['machine', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.machine} - {self.engine_hours}h - {self.timestamp}"


class MachineAlert(models.Model):
    """Alertas de las máquinas"""
    SEVERITY_CHOICES = [
        ('LOW', 'Baja'),
        ('MEDIUM', 'Media'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Activa'),
        ('ACKNOWLEDGED', 'Reconocida'),
        ('RESOLVED', 'Resuelta'),
        ('CLEARED', 'Limpiada'),
    ]

    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='alerts')
    alert_id = models.CharField(max_length=100, unique=True, verbose_name="Alert ID")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name="Severidad")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Estado")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Categoría")
    description = models.TextField(verbose_name="Descripción")
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    acknowledged_at = models.DateTimeField(blank=True, null=True, verbose_name="Reconocida en")
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Resuelta en")
    
    # Relación con servicio local si existe
    servicio_relacionado = models.ForeignKey(
        Servicio, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name="Servicio Relacionado"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alerta de Máquina"
        verbose_name_plural = "Alertas de Máquinas"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['machine', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.machine} - {self.severity} - {self.description[:50]}"


class MachineHoursOfOperation(models.Model):
    """Horas de operación de las máquinas"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='hours_of_operation')
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    hours_of_operation = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Horas de Operación")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horas de Operación"
        verbose_name_plural = "Horas de Operación"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['machine', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.machine} - {self.hours_of_operation}h - {self.timestamp}"


class DeviceStateReport(models.Model):
    """Reportes de estado del dispositivo telemático"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='device_reports')
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    device_state = models.CharField(max_length=50, verbose_name="Estado del Dispositivo")
    signal_strength = models.IntegerField(blank=True, null=True, verbose_name="Intensidad de Señal")
    battery_level = models.IntegerField(blank=True, null=True, verbose_name="Nivel de Batería")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reporte de Estado de Dispositivo"
        verbose_name_plural = "Reportes de Estado de Dispositivos"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['machine', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.machine} - {self.device_state} - {self.timestamp}"


class TelemetryReport(models.Model):
    """Reportes de telemetría generados automáticamente"""
    REPORT_TYPE_CHOICES = [
        ('DAILY', 'Diario'),
        ('WEEKLY', 'Semanal'),
        ('MONTHLY', 'Mensual'),
        ('CUSTOM', 'Personalizado'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('GENERATED', 'Generado'),
        ('SENT', 'Enviado'),
        ('FAILED', 'Fallido'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='telemetry_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="Tipo de Reporte")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")
    
    # Período del reporte
    start_date = models.DateField(verbose_name="Fecha de Inicio")
    end_date = models.DateField(verbose_name="Fecha de Fin")
    
    # Archivo generado
    report_file = models.FileField(
        upload_to='telemetry_reports/', 
        blank=True, 
        null=True, 
        verbose_name="Archivo del Reporte"
    )
    
    # Información de envío
    sent_to = models.EmailField(blank=True, null=True, verbose_name="Enviado a")
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Enviado en")
    
    # Configuración del reporte
    include_location = models.BooleanField(default=True, verbose_name="Incluir Ubicación")
    include_hours = models.BooleanField(default=True, verbose_name="Incluir Horas")
    include_alerts = models.BooleanField(default=True, verbose_name="Incluir Alertas")
    include_usage = models.BooleanField(default=True, verbose_name="Incluir Uso")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reporte de Telemetría"
        verbose_name_plural = "Reportes de Telemetría"
        ordering = ['-created_at']

    def __str__(self):
        return f"Reporte {self.report_type} - {self.cliente} - {self.start_date} a {self.end_date}"


class TelemetryReportMachine(models.Model):
    """Máquinas incluidas en cada reporte de telemetría"""
    report = models.ForeignKey(TelemetryReport, on_delete=models.CASCADE, related_name='machines')
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='telemetry_reports')
    
    # Resumen de datos para el reporte
    total_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Horas Totales")
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Distancia Total")
    alerts_count = models.IntegerField(default=0, verbose_name="Cantidad de Alertas")
    fuel_consumption = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Consumo de Combustible")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Máquina en Reporte"
        verbose_name_plural = "Máquinas en Reportes"
        unique_together = ['report', 'machine']

    def __str__(self):
        return f"{self.machine} en {self.report}"
