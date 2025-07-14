from django.db import models
from gestionDeTaller.models import Servicio
from clientes.models import Cliente, ModeloEquipo
from recursosHumanos.models import Usuario, Sucursal
from django.db.models import Sum, F, DecimalField
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


# Create your models here.
class Campania(models.Model):
    ESTADO_CHOICES = [
        ('PLANIFICADA', 'Planificada'),
        ('EN_CURSO', 'En Curso'),
        ('FINALIZADA', 'Finalizada'),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    valor_paquete = models.DecimalField(max_digits=10, decimal_places=2)
    objetivo_paquetes = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    def clean(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio')
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_objetivo_usd(self):
        return self.valor_paquete * self.objetivo_paquetes
    
    def get_cumplimiento(self):
        ventas = self.contactos.filter(resultado='VENTA_EXITOSA').count()
        return (ventas / self.objetivo_paquetes) * 100 if self.objetivo_paquetes else 0
    

class Contacto(models.Model):
    RESULTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('VENTA_EXITOSA', 'Venta Exitosa'),
        ('VENTA_PERDIDA', 'Venta Perdida'),
        ('REPROGRAMADO', 'Reprogramado'),
    ]

    campania = models.ForeignKey(Campania, on_delete=models.PROTECT, null=True, blank=True, related_name='contactos')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    fecha_contacto = models.DateTimeField()
    responsable = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES)
    observaciones = models.TextField(blank=True)
    fecha_seguimiento = models.DateField(null=True, blank=True)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class PotencialCompraModelo(models.Model):
    modelo = models.OneToOneField(ModeloEquipo, on_delete=models.PROTECT)
    potencial_anual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Potencial Anual USD")
    horas_uso_estimadas = models.IntegerField(verbose_name="Horas de Uso Estimadas Anuales")
    
    def __str__(self):
        return f"Potencial {self.modelo} - USD {self.potencial_anual}"
    

class AnalisisCliente(models.Model):
    CATEGORIA_CHOICES = [
        ('A', 'Categoría A'),
        ('B', 'Categoría B'),
        ('C', 'Categoría C'),
    ]

    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE)
    categoria = models.CharField(max_length=1, choices=CATEGORIA_CHOICES)
    ultima_actualizacion = models.DateField(auto_now=True)

    def calcular_categoria(self):
        dos_años_atras = timezone.now() - timedelta(days=730)
        
        servicios = Servicio.objects.filter(
            preorden__cliente=self.cliente,
            fecha_servicio__gte=dos_años_atras
        )
        
        total_servicios = servicios.count()
        
        total_facturacion = servicios.aggregate(
            total=Sum(
                F('valor_mano_obra') + 
                F('gastos__monto') + 
                F('repuestos__precio_unitario') * F('repuestos__cantidad'),
                output_field=DecimalField()
            )
        )['total'] or 0

        # Define thresholds for categories
        if total_servicios >= 10 and total_facturacion >= 50000:
            return 'A'
        elif total_servicios >= 5 and total_facturacion >= 20000:
            return 'B'
        else:
            return 'C'

    def save(self, *args, **kwargs):
        self.categoria = self.calcular_categoria()
        super().save(*args, **kwargs)


    def get_potencial_total(self):
        potencial = 0
        for equipo in self.cliente.equipos.filter(activo=True):
            try:
                potencial += equipo.modelo.potencialcompramodelo.potencial_anual
            except PotencialCompraModelo.DoesNotExist:
                continue
        return potencial

    def get_compra_real(self):
        año_actual = timezone.now().year
        return Servicio.objects.filter(
            preorden__cliente=self.cliente,
            fecha_servicio__year=año_actual
        ).aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0

    def get_cumplimiento_potencial(self):
        potencial = self.get_potencial_total()
        real = self.get_compra_real()
        return (real / potencial * 100) if potencial else 0

class PaqueteServicio(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')
    servicios = models.ManyToManyField(Servicio, related_name='paquetes')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class ClientePaquete(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('FINALIZADO', 'Finalizado'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='paquetes')
    paquete = models.ForeignKey(PaqueteServicio, on_delete=models.CASCADE, related_name='clientes')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')

    def __str__(self):
        return f"{self.cliente} - {self.paquete} ({self.estado})"


# Nuevos modelos para el Embudo de Ventas
class Campana(models.Model):
    """Modelo para campañas de marketing y ventas"""
    
    ESTADO_CHOICES = [
        ('PLANIFICADA', 'Planificada'),
        ('ACTIVA', 'Activa'),
        ('PAUSADA', 'Pausada'),
        ('FINALIZADA', 'Finalizada'),
    ]
    
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Campaña")
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin")
    activa = models.BooleanField(default=True, verbose_name="Activa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, verbose_name="Sucursal")
    
    # Métricas y objetivos
    presupuesto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Presupuesto")
    objetivo_contactos = models.IntegerField(null=True, blank=True, verbose_name="Objetivo de Contactos")
    objetivo_ventas = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Objetivo de Ventas")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='campanas_creadas',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Campaña"
        verbose_name_plural = "Campañas"
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.nombre} - {self.sucursal.nombre}"
    
    def get_contactos_count(self):
        """Retorna el número total de contactos de esta campaña"""
        return self.embudos_ventas.count()
    
    def get_ventas_count(self):
        """Retorna el número de ventas convertidas"""
        return self.embudos_ventas.filter(etapa='CIERRE').count()
    
    def get_valor_total_ventas(self):
        """Retorna el valor total de las ventas convertidas"""
        return self.embudos_ventas.filter(etapa='CIERRE').aggregate(
            total=models.Sum('valor_estimado')
        )['total'] or 0
    
    def get_tasa_conversion(self):
        """Calcula la tasa de conversión de la campaña"""
        total_contactos = self.get_contactos_count()
        ventas = self.get_ventas_count()
        return (ventas / total_contactos * 100) if total_contactos > 0 else 0


class EmbudoVentas(models.Model):
    """Modelo para el embudo de ventas con etapas"""
    
    ETAPA_CHOICES = [
        ('CONTACTO_INICIAL', 'Contacto Inicial'),
        ('CALIFICACION', 'Calificación'),
        ('PROPUESTA', 'Propuesta'),
        ('NEGOCIACION', 'Negociación'),
        ('CIERRE', 'Cierre'),
        ('PERDIDO', 'Perdido'),
    ]
    
    campana = models.ForeignKey(
        Campana, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='embudos_ventas',
        verbose_name="Campaña"
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES, verbose_name="Etapa")
    fecha_ingreso = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Ingreso")
    fecha_ultima_actividad = models.DateTimeField(auto_now=True, verbose_name="Última Actividad")
    valor_estimado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Valor Estimado"
    )
    valor_cierre = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Valor de Cierre"
    )
    
    # Origen del lead
    origen = models.CharField(
        max_length=50, 
        choices=[
            ('ALERTA_EQUIPO', 'Alerta de Equipo'),
            ('LEAD_JD', 'Lead John Deere'),
            ('REFERENCIA', 'Referencia'),
            ('MARKETING', 'Marketing'),
            ('SERVICIO_EXISTENTE', 'Servicio Existente'),
            ('OTRO', 'Otro'),
        ],
        verbose_name="Origen"
    )
    
    # Relación con alertas/leads
    alerta_equipo = models.ForeignKey(
        'centroSoluciones.AlertaEquipo', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Alerta de Equipo"
    )
    lead_jd = models.ForeignKey(
        'centroSoluciones.LeadJohnDeere', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Lead John Deere"
    )
    
    # Campos adicionales
    descripcion_negocio = models.TextField(blank=True, verbose_name="Descripción del Negocio")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='embudos_creados',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Embudo de Ventas"
        verbose_name_plural = "Embudos de Ventas"
        ordering = ['-fecha_ingreso']
        indexes = [
            models.Index(fields=['etapa', 'origen']),
            models.Index(fields=['cliente', 'fecha_ingreso']),
            models.Index(fields=['campana', 'etapa']),
        ]
    
    def __str__(self):
        return f"{self.cliente.razon_social} - {self.get_etapa_display()} - {self.origen}"
    
    @property
    def tiempo_en_embudo(self):
        """Calcula el tiempo que lleva en el embudo"""
        return timezone.now() - self.fecha_ingreso
    
    @property
    def venta_concretada(self):
        """Indica si la venta fue concretada (tiene valor de cierre)"""
        return self.valor_cierre is not None and self.valor_cierre > 0
    
    @property
    def diferencia_estimado_cierre(self):
        """Calcula la diferencia entre valor estimado y valor de cierre"""
        from decimal import Decimal
        if self.valor_estimado and self.valor_cierre:
            return self.valor_cierre - self.valor_estimado
        return Decimal('0')


class ContactoCliente(models.Model):
    """Modelo para registrar contactos con clientes"""
    
    TIPO_CONTACTO_CHOICES = [
        ('TELEFONO', 'Teléfono'),
        ('EMAIL', 'Email'),
        ('WHATSAPP', 'WhatsApp'),
        ('VISITA', 'Visita'),
        ('VIDEO_LLAMADA', 'Video Llamada'),
        ('REUNION', 'Reunión'),
        ('PRESENTACION', 'Presentación'),
    ]
    
    RESULTADO_CHOICES = [
        ('EXITOSO', 'Exitoso'),
        ('NO_CONTESTA', 'No Contesta'),
        ('REPROGRAMADO', 'Reprogramado'),
        ('CANCELADO', 'Cancelado'),
        ('VENTA', 'Venta Realizada'),
        ('OBJECCION', 'Objeción'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    fecha_contacto = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Contacto")
    tipo_contacto = models.CharField(max_length=15, choices=TIPO_CONTACTO_CHOICES, verbose_name="Tipo de Contacto")
    descripcion = models.TextField(verbose_name="Descripción del Contacto")
    resultado = models.CharField(max_length=15, choices=RESULTADO_CHOICES, verbose_name="Resultado")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    proximo_seguimiento = models.DateTimeField(null=True, blank=True, verbose_name="Próximo Seguimiento")
    
    # Responsable del contacto
    responsable = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE,
        verbose_name="Responsable"
    )
    
    # Relación con embudo
    embudo_ventas = models.ForeignKey(
        EmbudoVentas, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='contactos',
        verbose_name="Embudo de Ventas"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Contacto con Cliente"
        verbose_name_plural = "Contactos con Clientes"
        ordering = ['-fecha_contacto']
        indexes = [
            models.Index(fields=['cliente', 'fecha_contacto']),
            models.Index(fields=['responsable', 'resultado']),
            models.Index(fields=['embudo_ventas', 'fecha_contacto']),
        ]
    
    def __str__(self):
        return f"{self.cliente.razon_social} - {self.get_tipo_contacto_display()} - {self.fecha_contacto.strftime('%d/%m/%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        # Si hay un embudo asociado, actualizar su fecha de última actividad
        if self.embudo_ventas:
            self.embudo_ventas.fecha_ultima_actividad = timezone.now()
            self.embudo_ventas.save()
        
        super().save(*args, **kwargs)


class SugerenciaMejora(models.Model):
    """Modelo para el buzon anónimo de sugerencias de mejora"""
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Revisión'),
        ('EN_ANALISIS', 'En Análisis'),
        ('APROBADA', 'Aprobada'),
        ('IMPLEMENTADA', 'Implementada'),
        ('RECHAZADA', 'Rechazada'),
    ]
    
    CATEGORIA_CHOICES = [
        ('PROCESOS', 'Procesos de Trabajo'),
        ('EQUIPOS', 'Equipos y Herramientas'),
        ('SEGURIDAD', 'Seguridad Laboral'),
        ('CALIDAD', 'Control de Calidad'),
        ('MANTENIMIENTO', 'Mantenimiento Preventivo'),
        ('ATENCION_CLIENTE', 'Atención al Cliente'),
        ('FORMACION', 'Formación y Capacitación'),
        ('TECNOLOGIA', 'Tecnología y Sistemas'),
        ('AMBIENTE', 'Ambiente de Trabajo'),
        ('OTROS', 'Otros'),
    ]
    
    # Información de la sugerencia
    titulo = models.CharField(max_length=200, verbose_name="Título de la Sugerencia")
    descripcion = models.TextField(verbose_name="Descripción Detallada")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='OTROS', verbose_name="Categoría")
    
    # Estado y seguimiento
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    fecha_sugerencia = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Sugerencia")
    fecha_revision = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Revisión")
    fecha_implementacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Implementación")
    
    # Respuesta de la gerencia
    respuesta_gerencia = models.TextField(blank=True, null=True, verbose_name="Respuesta de la Gerencia")
    accion_especifica = models.TextField(blank=True, null=True, verbose_name="Acción Específica")
    responsable_implementacion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable de Implementación")
    
    # Información del revisor (solo para gerentes/admin)
    revisor = models.ForeignKey(
        'recursosHumanos.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Revisor",
        related_name='sugerencias_revisadas'
    )
    
    # Métricas
    impacto_estimado = models.CharField(
        max_length=20,
        choices=[
            ('BAJO', 'Bajo'),
            ('MEDIO', 'Medio'),
            ('ALTO', 'Alto'),
            ('CRITICO', 'Crítico'),
        ],
        default='MEDIO',
        verbose_name="Impacto Estimado"
    )
    
    prioridad = models.CharField(
        max_length=20,
        choices=[
            ('BAJA', 'Baja'),
            ('MEDIA', 'Media'),
            ('ALTA', 'Alta'),
            ('URGENTE', 'Urgente'),
        ],
        default='MEDIA',
        verbose_name="Prioridad"
    )
    
    # Campos adicionales
    beneficios_esperados = models.TextField(blank=True, null=True, verbose_name="Beneficios Esperados")
    recursos_necesarios = models.TextField(blank=True, null=True, verbose_name="Recursos Necesarios")
    tiempo_estimado_implementacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tiempo Estimado de Implementación")
    
    class Meta:
        verbose_name = "Sugerencia de Mejora"
        verbose_name_plural = "Sugerencias de Mejora"
        ordering = ['-fecha_sugerencia']
    
    def __str__(self):
        return f"{self.titulo} - {self.get_estado_display()}"
    
    @property
    def dias_pendiente(self):
        """Calcula los días que lleva pendiente la sugerencia"""
        if self.estado == 'PENDIENTE':
            return (timezone.now() - self.fecha_sugerencia).days
        return 0
    
    @property
    def tiempo_resolucion(self):
        """Calcula el tiempo total de resolución"""
        if self.fecha_implementacion:
            return (self.fecha_implementacion - self.fecha_sugerencia).days
        elif self.fecha_revision:
            return (self.fecha_revision - self.fecha_sugerencia).days
        return None
