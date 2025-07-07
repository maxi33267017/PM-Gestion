from django.db import models
from django.utils import timezone
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario, Sucursal

class AlertaEquipo(models.Model):
    """Modelo para las alertas de equipos recibidas del Centro de Soluciones Conectadas"""
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ASIGNADA', 'Asignada a Técnico'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESUELTA', 'Resuelta'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    CLASIFICACION_CHOICES = [
        ('CRITICA', 'Crítica'),
        ('ALTA', 'Alta'),
        ('MEDIA', 'Media'),
        ('BAJA', 'Baja'),
    ]
    
    # Información básica de la alerta
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    pin_equipo = models.CharField(max_length=50, verbose_name="PIN del Equipo")
    clasificacion = models.CharField(max_length=10, choices=CLASIFICACION_CHOICES, verbose_name="Clasificación")
    codigo = models.CharField(max_length=20, verbose_name="Código de Alerta")
    descripcion = models.TextField(verbose_name="Descripción")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, verbose_name="Sucursal")
    
    # Campos de seguimiento y asignación
    fecha_asignacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Asignación")
    tecnico_asignado = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'rol': 'TECNICO'},
        verbose_name="Técnico Asignado"
    )
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Resolución")
    observaciones_tecnico = models.TextField(blank=True, verbose_name="Observaciones del Técnico")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='alertas_creadas',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Alerta de Equipo"
        verbose_name_plural = "Alertas de Equipos"
        ordering = ['-fecha', '-clasificacion']
        indexes = [
            models.Index(fields=['estado', 'clasificacion']),
            models.Index(fields=['cliente', 'fecha']),
            models.Index(fields=['tecnico_asignado', 'estado']),
        ]
    
    def __str__(self):
        return f"Alerta {self.codigo} - {self.cliente.razon_social} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        # Actualizar fecha de asignación cuando se asigna un técnico
        if self.tecnico_asignado and not self.fecha_asignacion:
            self.fecha_asignacion = timezone.now()
        
        # Actualizar fecha de resolución cuando se resuelve
        if self.estado == 'RESUELTA' and not self.fecha_resolucion:
            self.fecha_resolucion = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def tiempo_pendiente(self):
        """Calcula el tiempo que lleva pendiente la alerta"""
        if self.estado == 'PENDIENTE':
            return timezone.now() - self.fecha
        return None
    
    @property
    def tiempo_resolucion(self):
        """Calcula el tiempo total de resolución"""
        if self.fecha_resolucion:
            return self.fecha_resolucion - self.fecha
        return None
    
    def get_prioridad_color(self):
        """Retorna el color CSS para la prioridad"""
        colors = {
            'CRITICA': 'danger',
            'ALTA': 'warning',
            'MEDIA': 'info',
            'BAJA': 'success',
        }
        return colors.get(self.clasificacion, 'secondary')


class LeadJohnDeere(models.Model):
    """Modelo para los leads proporcionados por John Deere"""
    
    ESTADO_CHOICES = [
        ('NUEVO', 'Nuevo'),
        ('CONTACTADO', 'Contactado'),
        ('CALIFICADO', 'Calificado'),
        ('CONVERTIDO', 'Convertido'),
        ('DESCARTADO', 'Descartado'),
    ]
    
    CLASIFICACION_CHOICES = [
        ('JOHN_DEERE_PROTECT', 'John Deere Protect'),
        ('MTTO_PREVENTIVO', 'Mtto Preventivo'),
        ('PIP', 'PIP'),
        ('REFORMA_COMPONENTES', 'Reforma de componentes'),
        ('DIENTES_CUCHILLAS', 'Dientes / Cuchillas'),
        ('TREN_RODANTE', 'Tren rodante'),
        ('GARANTIA_BASICA', 'Garantía Básica'),
        ('GARANTIA_EXTENDIDA', 'Garantía Extendida'),
        ('DISPONIBILIDAD', 'Disponibilidad'),
        ('RECONEXION', 'Reconexión'),
        ('OTROS', 'Otros'),
    ]
    
    # Información básica del lead
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, verbose_name="Equipo")
    clasificacion = models.CharField(
        max_length=25, 
        choices=CLASIFICACION_CHOICES, 
        verbose_name="Clasificación",
        help_text="Tipo de servicio o producto solicitado"
    )
    descripcion = models.TextField(verbose_name="Descripción")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='NUEVO', verbose_name="Estado")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, verbose_name="Sucursal")
    
    # Campos de seguimiento
    fecha_contacto = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Primer Contacto")
    observaciones_contacto = models.TextField(blank=True, verbose_name="Observaciones del Contacto")
    valor_estimado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Valor Estimado"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='leads_creados',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Lead John Deere"
        verbose_name_plural = "Leads John Deere"
        ordering = ['-fecha', 'estado']
        indexes = [
            models.Index(fields=['estado', 'fecha']),
            models.Index(fields=['cliente', 'equipo']),
            models.Index(fields=['sucursal', 'estado']),
            models.Index(fields=['clasificacion', 'estado']),
        ]
    
    def __str__(self):
        return f"Lead JD - {self.cliente.razon_social} - {self.equipo.numero_serie} - {self.get_clasificacion_display()}"
    
    def save(self, *args, **kwargs):
        # Actualizar fecha de contacto cuando cambia a contactado
        if self.estado == 'CONTACTADO' and not self.fecha_contacto:
            self.fecha_contacto = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def tiempo_sin_contactar(self):
        """Calcula el tiempo que lleva sin contactar"""
        if self.estado == 'NUEVO':
            return timezone.now() - self.fecha
        return None
    
    def get_clasificacion_color(self):
        """Retorna el color CSS para la clasificación"""
        colors = {
            'JOHN_DEERE_PROTECT': 'primary',
            'MTTO_PREVENTIVO': 'success',
            'PIP': 'info',
            'REFORMA_COMPONENTES': 'warning',
            'DIENTES_CUCHILLAS': 'secondary',
            'TREN_RODANTE': 'dark',
            'GARANTIA_BASICA': 'light',
            'GARANTIA_EXTENDIDA': 'primary',
            'DISPONIBILIDAD': 'success',
            'RECONEXION': 'info',
            'OTROS': 'secondary',
        }
        return colors.get(self.clasificacion, 'secondary')


class AsignacionAlerta(models.Model):
    """Modelo para el historial de asignaciones de alertas"""
    
    alerta = models.ForeignKey(AlertaEquipo, on_delete=models.CASCADE, verbose_name="Alerta")
    tecnico = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE,
        limit_choices_to={'rol': 'TECNICO'},
        verbose_name="Técnico"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Asignación")
    asignado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='asignaciones_realizadas',
        verbose_name="Asignado por"
    )
    motivo = models.TextField(blank=True, verbose_name="Motivo de la Asignación")
    
    class Meta:
        verbose_name = "Asignación de Alerta"
        verbose_name_plural = "Asignaciones de Alertas"
        ordering = ['-fecha_asignacion']
    
    def __str__(self):
        return f"Asignación: {self.alerta.codigo} → {self.tecnico.get_nombre_completo()}"
