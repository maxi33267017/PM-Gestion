from django.db import models
from django.utils import timezone
from clientes.models import Cliente, Equipo, ModeloEquipo, TipoEquipo
from recursosHumanos.models import Sucursal, Usuario


class EquipoStock(models.Model):
    """Equipos en stock (comprados a John Deere) antes de ser vendidos"""
    
    ESTADO_CHOICES = [
        ('EN_STOCK', 'En Stock'),
        ('RESERVADO', 'Reservado'),
        ('VENDIDO', 'Vendido'),
        ('DEVUELTO', 'Devuelto a JD'),
    ]
    
    # Información del equipo
    numero_serie = models.CharField(max_length=50, unique=True, verbose_name="Número de Serie")
    modelo = models.ForeignKey(ModeloEquipo, on_delete=models.PROTECT, verbose_name="Modelo")
    tipo_equipo = models.ForeignKey(TipoEquipo, on_delete=models.PROTECT, verbose_name="Tipo de Equipo")
    
    # Información de compra
    fecha_compra_jd = models.DateField(verbose_name="Fecha de Compra a JD")
    numero_orden_compra = models.CharField(max_length=50, verbose_name="Número de Orden de Compra", blank=True)
    costo_compra = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo de Compra")
    
    # Estado y ubicación
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='EN_STOCK', verbose_name="Estado")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, verbose_name="Sucursal")
    ubicacion_fisica = models.CharField(max_length=200, verbose_name="Ubicación Física", blank=True)
    
    # Información adicional
    año_fabricacion = models.PositiveIntegerField(verbose_name="Año de Fabricación")
    color = models.CharField(max_length=50, verbose_name="Color", blank=True)
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    
    # Fechas del sistema
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Equipo en Stock"
        verbose_name_plural = "Equipos en Stock"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'sucursal']),
            models.Index(fields=['numero_serie']),
            models.Index(fields=['modelo']),
        ]

    def __str__(self):
        return f"{self.modelo} - Serie: {self.numero_serie} ({self.get_estado_display()})"
    
    @property
    def dias_en_stock(self):
        """Calcula cuántos días lleva en stock"""
        if self.estado == 'EN_STOCK':
            return (timezone.now().date() - self.fecha_creacion.date()).days
        return 0


class Certificado(models.Model):
    """Certificados disponibles para asignar a equipos vendidos"""
    
    TIPO_CERTIFICADO = [
        ('GARANTIA', 'Registro en Garantía'),
        ('GARANTIA_EXTENDIDA', 'Garantía Extendida'),
        ('SVAP', 'SVAP (John Deere Protect)'),
        ('OTRO', 'Otro'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Certificado")
    tipo = models.CharField(max_length=20, choices=TIPO_CERTIFICADO, verbose_name="Tipo de Certificado")
    descripcion = models.TextField(verbose_name="Descripción", blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo", default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta", default=0)
    
    # Stock del certificado
    stock_disponible = models.PositiveIntegerField(default=0, verbose_name="Stock Disponible")
    stock_minimo = models.PositiveIntegerField(default=0, verbose_name="Stock Mínimo")
    
    # Estado
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    # Fechas del sistema
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"
        ordering = ['tipo', 'nombre']
        indexes = [
            models.Index(fields=['tipo', 'activo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre} (Stock: {self.stock_disponible})"
    
    @property
    def necesita_reposicion(self):
        """Indica si necesita reposición de stock"""
        return self.stock_disponible <= self.stock_minimo


class MovimientoStockCertificado(models.Model):
    """Registro de movimientos de stock de certificados"""
    
    TIPO_MOVIMIENTO = [
        ('ENTRADA', 'Entrada de Stock'),
        ('SALIDA', 'Salida de Stock'),
        ('AJUSTE', 'Ajuste de Stock'),
    ]
    
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO, verbose_name="Tipo de Movimiento")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    stock_anterior = models.PositiveIntegerField(verbose_name="Stock Anterior")
    stock_nuevo = models.PositiveIntegerField(verbose_name="Stock Nuevo")
    
    # Referencia a la venta (si aplica)
    venta = models.ForeignKey('VentaEquipo', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_certificados')
    
    # Usuario que realizó el movimiento
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, verbose_name="Usuario")
    
    # Información adicional
    motivo = models.TextField(verbose_name="Motivo", blank=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Movimiento")
    
    class Meta:
        verbose_name = "Movimiento de Stock de Certificado"
        verbose_name_plural = "Movimientos de Stock de Certificados"
        ordering = ['-fecha_movimiento']
        indexes = [
            models.Index(fields=['certificado', 'fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', 'fecha_movimiento']),
        ]

    def __str__(self):
        return f"{self.certificado} - {self.get_tipo_movimiento_display()} ({self.cantidad}) - {self.fecha_movimiento.strftime('%d/%m/%Y')}"


class VentaEquipo(models.Model):
    """Registro de venta de equipos con checklist de certificados"""
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    # Equipo vendido
    equipo_stock = models.OneToOneField(EquipoStock, on_delete=models.PROTECT, verbose_name="Equipo en Stock")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    
    # Información de la venta
    fecha_venta = models.DateField(verbose_name="Fecha de Venta")
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio de Venta")
    numero_factura = models.CharField(max_length=50, verbose_name="Número de Factura", blank=True)
    
    # Certificados asociados a la venta (varios certificados posibles)
    certificados = models.ManyToManyField('Certificado', blank=True, related_name='ventas', verbose_name="Certificados Asociados")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    
    # Usuario que realizó la venta
    vendedor = models.ForeignKey(Usuario, on_delete=models.PROTECT, verbose_name="Vendedor")
    
    # Información adicional
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    
    # Fechas del sistema
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Venta de Equipo"
        verbose_name_plural = "Ventas de Equipos"
        ordering = ['-fecha_venta']
        indexes = [
            models.Index(fields=['estado', 'fecha_venta']),
            models.Index(fields=['cliente', 'fecha_venta']),
        ]

    def __str__(self):
        return f"Venta #{self.id} - {self.equipo_stock.numero_serie} - {self.cliente.razon_social}"
    
    @property
    def total_certificados(self):
        """Calcula el total de certificados asociados a la venta"""
        return self.certificados.count()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ChecklistProcesosJD.objects.get_or_create(
            venta=self,
            defaults={
                'registro_garantias': False,
                'garantia_extendida': False,
                'operations_center': False,
                'svap': False,
            }
        )


class ChecklistProcesosJD(models.Model):
    """Checklist de procesos realizados en John Deere"""
    
    venta = models.OneToOneField(VentaEquipo, on_delete=models.CASCADE, related_name='checklist_procesos')
    
    # Procesos de John Deere
    registro_garantias = models.BooleanField(default=False, verbose_name="Registro en Garantías")
    garantia_extendida = models.BooleanField(default=False, verbose_name="Garantía Extendida")
    operations_center = models.BooleanField(default=False, verbose_name="Operations Center")
    svap = models.BooleanField(default=False, verbose_name="SVAP (John Deere Protect)")
    
    # Información adicional
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    usuario_actualizacion = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Usuario que Actualizó"
    )
    
    class Meta:
        verbose_name = "Checklist de Procesos JD"
        verbose_name_plural = "Checklists de Procesos JD"
    
    def __str__(self):
        return f"Checklist - Venta #{self.venta.id}"
    
    @property
    def procesos_completados(self):
        """Retorna el número de procesos completados"""
        return sum([
            self.registro_garantias,
            self.garantia_extendida,
            self.operations_center,
            self.svap
        ])
    
    @property
    def total_procesos(self):
        """Retorna el total de procesos disponibles"""
        return 4
    
    @property
    def porcentaje_completado(self):
        """Retorna el porcentaje de procesos completados"""
        if self.total_procesos == 0:
            return 0
        return (self.procesos_completados / self.total_procesos) * 100


class TransferenciaEquipo(models.Model):
    """Registro de transferencia de equipos vendidos a clientes"""
    
    venta = models.OneToOneField(VentaEquipo, on_delete=models.CASCADE, verbose_name="Venta")
    equipo_cliente = models.OneToOneField(Equipo, on_delete=models.CASCADE, verbose_name="Equipo del Cliente")
    
    # Información de la transferencia
    fecha_transferencia = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Transferencia")
    usuario_transferencia = models.ForeignKey(Usuario, on_delete=models.PROTECT, verbose_name="Usuario que Realizó la Transferencia")
    
    # Checklist completado
    checklist_completado = models.BooleanField(default=False, verbose_name="Checklist Completado")
    fecha_checklist = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Checklist")
    
    # Información adicional
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    
    class Meta:
        verbose_name = "Transferencia de Equipo"
        verbose_name_plural = "Transferencias de Equipos"
        ordering = ['-fecha_transferencia']

    def __str__(self):
        return f"Transferencia {self.id} - {self.equipo_cliente} a {self.venta.cliente}"
