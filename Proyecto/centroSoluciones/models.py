from django.db import models
from django.utils import timezone
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario, Sucursal
import os

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
    
    # Campos para procesamiento SAR
    conexion_sar_realizada = models.BooleanField(default=False, verbose_name="Conexión SAR Realizada")
    fecha_conexion_sar = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Conexión SAR")
    resultado_conexion_sar = models.TextField(blank=True, verbose_name="Resultado de Conexión SAR")
    oportunidad_crm_creada = models.BooleanField(default=False, verbose_name="Oportunidad CRM Creada")
    
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
        
        # Actualizar fecha de conexión SAR cuando se marca como realizada
        if self.conexion_sar_realizada and not self.fecha_conexion_sar:
            self.fecha_conexion_sar = timezone.now()
        
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
    
    @property
    def embudo_ventas(self):
        """Retorna el embudo de ventas asociado a este lead"""
        try:
            from crm.models import EmbudoVentas
            return EmbudoVentas.objects.filter(lead_jd=self).first()
        except:
            return None


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


class CodigoAlerta(models.Model):
    """Modelo para almacenar códigos de alerta con sus descripciones por modelo de equipo"""
    
    CLASIFICACION_CHOICES = [
        ('CRITICA', 'Crítica'),
        ('ALTA', 'Alta'),
        ('MEDIA', 'Media'),
        ('BAJA', 'Baja'),
    ]
    
    # Información del código de alerta
    codigo = models.CharField(max_length=20, verbose_name="Código de Alerta", unique=True)
    modelo_equipo = models.CharField(max_length=100, verbose_name="Modelo de Equipo")
    descripcion = models.TextField(verbose_name="Descripción del Código")
    clasificacion = models.CharField(
        max_length=10, 
        choices=CLASIFICACION_CHOICES, 
        default='MEDIA',
        verbose_name="Clasificación por Defecto"
    )
    
    # Campos adicionales
    instrucciones_resolucion = models.TextField(
        blank=True, 
        verbose_name="Instrucciones de Resolución",
        help_text="Pasos recomendados para resolver este tipo de alerta"
    )
    repuestos_comunes = models.TextField(
        blank=True, 
        verbose_name="Repuestos Comunes",
        help_text="Repuestos que suelen necesitarse para este tipo de alerta"
    )
    tiempo_estimado_resolucion = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Tiempo Estimado de Resolución (horas)"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='codigos_alerta_creados',
        verbose_name="Creado por"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Código de Alerta"
        verbose_name_plural = "Códigos de Alerta"
        ordering = ['codigo', 'modelo_equipo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['modelo_equipo']),
            models.Index(fields=['clasificacion']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.modelo_equipo}"
    
    def get_prioridad_color(self):
        """Retorna el color CSS para la prioridad"""
        colors = {
            'CRITICA': 'danger',
            'ALTA': 'warning',
            'MEDIA': 'info',
            'BAJA': 'success',
        }
        return colors.get(self.clasificacion, 'secondary')

# Modelos para Reportes CSC
class ReporteCSC(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('GENERADO', 'Generado'),
        ('ENVIADO', 'Enviado'),
    ]
    
    equipo = models.ForeignKey('clientes.Equipo', on_delete=models.CASCADE, related_name='reportes_csc')
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    fecha_reporte = models.DateField(help_text="Fecha extraída del nombre del archivo CSV")
    archivo_csv = models.FileField(upload_to='reportes_csc/', help_text="Archivo CSV original")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')
    recomendaciones_automaticas = models.TextField(blank=True, help_text="Recomendaciones generadas automáticamente")
    comentarios_manuales = models.TextField(blank=True, help_text="Comentarios adicionales del usuario")
    creado_por = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE)
    
    # Datos calculados del reporte
    total_horas_analizadas = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    eficiencia_general = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje de eficiencia")
    
    class Meta:
        verbose_name = "Reporte CSC"
        verbose_name_plural = "Reportes CSC"
        ordering = ['-fecha_importacion']
    
    def __str__(self):
        return f"Reporte CSC - {self.equipo.numero_serie} ({self.fecha_reporte})"
    
    @property
    def nombre_archivo_original(self):
        """Extraer nombre original del archivo CSV"""
        if self.archivo_csv:
            return os.path.basename(self.archivo_csv.name)
        return ""

class DatosReporteCSC(models.Model):
    reporte = models.ForeignKey(ReporteCSC, on_delete=models.CASCADE, related_name='datos')
    categoria = models.CharField(max_length=100, help_text="Ej: Utilización del motor, MFWD Utilization per gear")
    serie = models.CharField(max_length=100, help_text="Ej: Carga baja, Activado - F1")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=20, help_text="hr, %, etc.")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    class Meta:
        verbose_name = "Dato Reporte CSC"
        verbose_name_plural = "Datos Reporte CSC"
        unique_together = ['reporte', 'categoria', 'serie']
    
    def __str__(self):
        return f"{self.categoria} - {self.serie}: {self.valor} {self.unidad}"

class AlertaReporteCSC(models.Model):
    """Modelo para alertas específicas de reportes CSC"""
    
    SEVERIDAD_CHOICES = [
        ('INFO', 'Info'),
        ('MEDIANA', 'Mediana'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    reporte = models.ForeignKey(ReporteCSC, on_delete=models.CASCADE, related_name='alertas')
    fecha_hora = models.DateTimeField(verbose_name="Fecha y Hora")
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, verbose_name="Severidad")
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Alerta")
    descripcion = models.TextField(blank=True, verbose_name="Descripción adicional")
    creado_por = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerta Reporte CSC"
        verbose_name_plural = "Alertas Reporte CSC"
        ordering = ['-fecha_hora', '-severidad']
    
    def __str__(self):
        return f"{self.nombre} - {self.get_severidad_display()} ({self.fecha_hora.strftime('%d/%m/%Y %H:%M')})"
    
    def get_severidad_color(self):
        """Retorna el color CSS para la severidad"""
        colors = {
            'INFO': 'info',
            'MEDIANA': 'warning',
            'ALTA': 'danger',
            'CRITICA': 'dark',
        }
        return colors.get(self.severidad, 'secondary')

class ArchivoDatosMensual(models.Model):
    """Modelo para almacenar archivos Excel mensuales cargados"""
    TIPO_CHOICES = [
        ('UTILIZACION', 'Datos de Utilización'),
        ('NOTIFICACIONES', 'Notificaciones y Alertas'),
    ]
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('COMPLETADO', 'Completado'),
        ('ERROR', 'Error'),
    ]
    
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='archivos_mensuales/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_procesamiento = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    periodo = models.CharField(max_length=50, blank=True)  # Ej: "01/07/2025 - 31/07/2025"
    total_registros = models.IntegerField(default=0)
    registros_procesados = models.IntegerField(default=0)
    cargado_por = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE)
    log_procesamiento = models.TextField(blank=True)
    errores = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha_carga']
        verbose_name = 'Archivo de Datos Mensual'
        verbose_name_plural = 'Archivos de Datos Mensuales'
    
    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_tipo_display()}) - {self.estado}"

class DatosUtilizacionMensual(models.Model):
    """Modelo para datos de utilización procesados del archivo Analizador_de_máquina"""
    archivo = models.ForeignKey(ArchivoDatosMensual, on_delete=models.CASCADE, related_name='datos_utilizacion')
    equipo = models.ForeignKey('clientes.Equipo', on_delete=models.CASCADE, null=True, blank=True)
    
    # Datos básicos del equipo
    maquina = models.CharField(max_length=255)  # Nombre de la máquina
    modelo = models.CharField(max_length=100)   # Modelo
    tipo = models.CharField(max_length=100)     # Tipo de máquina
    numero_serie = models.CharField(max_length=100)  # Número de serie
    organizacion = models.CharField(max_length=255)  # Organización
    identificador_organizacion = models.CharField(max_length=50)
    
    # Período de análisis
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    # Datos de combustible
    combustible_consumido_periodo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    consumo_promedio_periodo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    combustible_funcionamiento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    combustible_ralenti = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Datos de motor
    horas_trabajo_motor_periodo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    horas_trabajo_motor_vida_util = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Datos de temperatura
    temp_max_aceite_transmision = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temp_max_aceite_hidraulico = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temp_max_refrigerante = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Datos de modo ECO
    modo_eco_activado_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    modo_eco_activado_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    modo_eco_desactivado_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Datos de utilización (C&F)
    utilizacion_alta_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilizacion_media_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilizacion_baja_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilizacion_ralenti_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Datos de tiempo en marcha
    tiempo_avan_1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_4 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_5 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_6 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_7 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_avan_8 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_estacionamiento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_punto_muerto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_4 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_5 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_6 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_7 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tiempo_ret_8 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Datos adicionales
    nivel_tanque_combustible = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    odometro_vida_util = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ano_modelo = models.IntegerField(null=True, blank=True)
    estado_maquina = models.CharField(max_length=50, blank=True)
    ultima_latitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    ultima_longitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Datos originales completos (JSON)
    datos_originales = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Dato de Utilización Mensual'
        verbose_name_plural = 'Datos de Utilización Mensual'
        indexes = [
            models.Index(fields=['numero_serie', 'fecha_inicio']),
            models.Index(fields=['equipo', 'fecha_inicio']),
        ]
    
    def __str__(self):
        return f"{self.maquina} - {self.fecha_inicio} a {self.fecha_fin}"

class NotificacionMensual(models.Model):
    """Modelo para notificaciones y alertas procesadas del archivo Notificaciones"""
    archivo = models.ForeignKey(ArchivoDatosMensual, on_delete=models.CASCADE, related_name='notificaciones')
    equipo = models.ForeignKey('clientes.Equipo', on_delete=models.CASCADE, null=True, blank=True)
    
    # Datos básicos
    nombre_organizacion = models.CharField(max_length=255)
    nombre = models.CharField(max_length=255)
    fecha = models.DateField()
    codigo_hora = models.TimeField()
    pin_maquina = models.CharField(max_length=100)
    marca_maquina = models.CharField(max_length=100)
    tipo_maquina = models.CharField(max_length=100)
    modelo_maquina = models.CharField(max_length=100)
    
    # Datos de la notificación
    severidad = models.CharField(max_length=50)
    categoria = models.CharField(max_length=100)
    codigos_diagnostico = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField()
    texto = models.TextField()
    
    # Ubicación
    latitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Datos adicionales
    incidencias = models.IntegerField(default=1)
    duracion = models.IntegerField(null=True, blank=True)  # en segundos
    horas_trabajo_motor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Estado de resolución
    resuelta = models.BooleanField(default=False)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Datos originales completos (JSON)
    datos_originales = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-fecha', '-codigo_hora']
        verbose_name = 'Notificación Mensual'
        verbose_name_plural = 'Notificaciones Mensuales'
        indexes = [
            models.Index(fields=['pin_maquina', 'fecha']),
            models.Index(fields=['equipo', 'fecha']),
            models.Index(fields=['severidad', 'fecha']),
            models.Index(fields=['resuelta', 'fecha']),
        ]
    
    def __str__(self):
        return f"{self.pin_maquina} - {self.fecha} {self.codigo_hora} - {self.severidad}"
