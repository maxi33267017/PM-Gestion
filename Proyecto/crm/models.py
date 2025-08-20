from django.db import models
from gestionDeTaller.models import Servicio
from clientes.models import Cliente, ModeloEquipo
from recursosHumanos.models import Usuario, Sucursal
from django.db.models import Sum, F, DecimalField
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


# Create your models here.
    



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
        
        # Calcular facturación incluyendo modelos antiguos y nuevos
        total_mano_obra = servicios.aggregate(total=Sum('valor_mano_obra'))['total'] or 0
        
        # Gastos (antiguos + simplificados + terceros)
        total_gastos_antiguos = servicios.aggregate(total=Sum('gastos__monto'))['total'] or 0
        total_gastos_simplificados = servicios.aggregate(total=Sum('gastos_asistencia_simplificados__monto'))['total'] or 0
        total_gastos_terceros = servicios.aggregate(total=Sum('gastos_insumos_terceros__monto'))['total'] or 0
        total_gastos = total_gastos_antiguos + total_gastos_simplificados + total_gastos_terceros
        
        # Repuestos (antiguos + simplificados)
        total_repuestos_antiguos = servicios.aggregate(total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad')))['total'] or 0
        total_repuestos_simplificados = servicios.aggregate(total=Sum('venta_repuestos_simplificada__monto_total'))['total'] or 0
        total_repuestos = total_repuestos_antiguos + total_repuestos_simplificados
        
        total_facturacion = total_mano_obra + total_gastos + total_repuestos

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
    
    # Campos para segmentación por equipos
    tipo_equipo = models.ForeignKey(
        'clientes.TipoEquipo', 
        on_delete=models.CASCADE, 
        verbose_name="Tipo de Equipo",
        null=True,
        blank=True,
        help_text="Dejar vacío para incluir todos los tipos de equipos"
    )
    modelo_equipo = models.ForeignKey(
        'clientes.ModeloEquipo', 
        on_delete=models.CASCADE, 
        verbose_name="Modelo de Equipo",
        null=True,
        blank=True,
        help_text="Dejar vacío para incluir todos los modelos del tipo seleccionado"
    )
    
    # Métricas y objetivos
    presupuesto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Presupuesto")
    objetivo_contactos = models.IntegerField(null=True, blank=True, verbose_name="Objetivo de Contactos")
    objetivo_ventas = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Objetivo de Ventas")
    
    # Campos adicionales del modelo antiguo
    valor_paquete = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor del Paquete")
    objetivo_paquetes = models.IntegerField(null=True, blank=True, verbose_name="Objetivo de Paquetes")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PLANIFICADA', verbose_name="Estado")
    
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
    
    def get_clientes_objetivo(self):
        """Obtiene los clientes objetivo basados en el tipo y modelo de equipo"""
        from clientes.models import Cliente, Equipo
        
        print(f"=== DEBUG GET_CLIENTES_OBJETIVO ===")
        print(f"Tipo de equipo: {self.tipo_equipo}")
        print(f"Modelo de equipo: {self.modelo_equipo}")
        
        # Filtrar equipos según la segmentación de la campaña
        equipos_query = {'activo': True}
        
        if self.tipo_equipo:
            equipos_query['modelo__tipo_equipo'] = self.tipo_equipo
            print(f"Filtrando por tipo: {self.tipo_equipo.nombre}")
            
        if self.modelo_equipo:
            equipos_query['modelo'] = self.modelo_equipo
            print(f"Filtrando por modelo: {self.modelo_equipo.nombre}")
        
        print(f"Query de equipos: {equipos_query}")
        
        # Obtener equipos que cumplen los criterios
        equipos_objetivo = Equipo.objects.filter(**equipos_query)
        print(f"Equipos encontrados: {equipos_objetivo.count()}")
        
        # Obtener clientes únicos que tienen estos equipos
        clientes_ids = equipos_objetivo.values_list('cliente_id', flat=True).distinct()
        print(f"IDs de clientes únicos: {list(clientes_ids)}")
        
        clientes = Cliente.objects.filter(id__in=clientes_ids, activo=True)
        print(f"Clientes activos encontrados: {clientes.count()}")
        
        return clientes
    
    def crear_embudos_ventas_automaticos(self):
        """Crea automáticamente embudos de ventas para todos los clientes objetivo"""
        print(f"=== DEBUG CREAR EMBUDOS AUTOMÁTICOS ===")
        print(f"Campaña: {self.nombre}")
        print(f"Tipo de equipo: {self.tipo_equipo}")
        print(f"Modelo de equipo: {self.modelo_equipo}")
        
        clientes_objetivo = self.get_clientes_objetivo()
        print(f"Clientes objetivo encontrados: {clientes_objetivo.count()}")
        
        # Crear 1 embudo genérico para la campaña
        embudo_nombre = f"{self.nombre} - {self.fecha_inicio}"
        
        # Verificar si ya existe un embudo genérico para esta campaña
        embudo_existente = self.embudos_ventas.filter(cliente__isnull=True).first()
        
        if embudo_existente:
            print(f"⚠️ Embudo genérico ya existe: {embudo_existente}")
            embudo = embudo_existente
        else:
            embudo = EmbudoVentas.objects.create(
                campana=self,
                cliente=None,  # Embudo genérico
                etapa='CONTACTO_INICIAL',
                origen='CAMPAÑA_MARKETING'
            )
            print(f"✅ Embudo genérico creado: {embudo}")
        
        # Crear ContactoCliente para cada cliente objetivo
        contactos_creados = 0
        
        for cliente in clientes_objetivo:
            print(f"Procesando cliente: {cliente.razon_social}")
            # Verificar si ya existe un contacto para este cliente en este embudo
            if not ContactoCliente.objects.filter(embudo_ventas=embudo, cliente=cliente).exists():
                ContactoCliente.objects.create(
                    embudo_ventas=embudo,
                    cliente=cliente,
                    tipo_contacto='PRESENTACION',
                    descripcion=f"Oportunidad de campaña: {self.nombre}",
                    resultado='EXITOSO',
                    observaciones=f"Campaña automática creada para cliente con equipos del tipo seleccionado",
                    responsable=self.creado_por
                )
                contactos_creados += 1
                print(f"✅ Contacto creado para {cliente.razon_social}")
            else:
                print(f"⚠️ Contacto ya existe para {cliente.razon_social}")
        
        print(f"Total contactos creados: {contactos_creados}")
        return contactos_creados


class Contacto(models.Model):
    RESULTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('VENTA_EXITOSA', 'Venta Exitosa'),
        ('VENTA_PERDIDA', 'Venta Perdida'),
        ('REPROGRAMADO', 'Reprogramado'),
    ]

    campania = models.ForeignKey(Campana, on_delete=models.PROTECT, null=True, blank=True, related_name='contactos')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    fecha_contacto = models.DateTimeField()
    responsable = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES)
    observaciones = models.TextField(blank=True)
    fecha_seguimiento = models.DateField(null=True, blank=True)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


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
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Cliente")
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
            ('POPS', 'POPS'),
            ('REFERENCIA', 'Referencia'),
            ('MARKETING', 'Marketing'),
            ('CAMPAÑA_MARKETING', 'Campaña Marketing'),
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
        cliente_nombre = self.cliente.razon_social if self.cliente else "Embudo Genérico"
        return f"{cliente_nombre} - {self.get_etapa_display()} - {self.origen}"
    
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

class EmbudoChecklistAdicional(models.Model):
    """Modelo para el embudo de checklist adicionales y observaciones de informes de equipos"""
    
    ETAPA_CHOICES = [
        ('IDENTIFICADO', 'Identificado'),
        ('EN_ANALISIS', 'En Análisis'),
        ('PLANIFICADO', 'Planificado'),
        ('EN_DESARROLLO', 'En Desarrollo'),
        ('IMPLEMENTADO', 'Implementado'),
        ('VERIFICADO', 'Verificado'),
        ('CERRADO', 'Cerrado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    TIPO_CHOICES = [
        ('CHECKLIST_ADICIONAL', 'Checklist Adicional'),
        ('OBSERVACION', 'Observación'),
        ('MEJORA_PROCEDIMIENTO', 'Mejora de Procedimiento'),
        ('MANTENIMIENTO_PREVENTIVO', 'Mantenimiento Preventivo'),
        ('SEGURIDAD', 'Seguridad'),
        ('CALIDAD', 'Calidad'),
        ('OTRO', 'Otro'),
    ]
    
    # Información básica
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion = models.TextField(verbose_name="Descripción Detallada")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo")
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='MEDIA', verbose_name="Prioridad")
    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES, default='IDENTIFICADO', verbose_name="Etapa")
    
    # Relaciones
    servicio = models.ForeignKey(
        'gestionDeTaller.Servicio',
        on_delete=models.CASCADE,
        verbose_name="Servicio Relacionado",
        related_name='checklists_adicionales'
    )
    equipo = models.ForeignKey(
        'clientes.Equipo',
        on_delete=models.CASCADE,
        verbose_name="Equipo",
        related_name='checklists_adicionales'
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        verbose_name="Cliente",
        related_name='checklists_adicionales'
    )
    
    # Responsables
    identificado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        verbose_name="Identificado por",
        related_name='checklists_identificados'
    )
    responsable_implementacion = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Responsable de Implementación",
        related_name='checklists_responsable'
    )
    
    # Fechas
    fecha_identificacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Identificación")
    fecha_limite = models.DateField(null=True, blank=True, verbose_name="Fecha Límite")
    fecha_implementacion = models.DateField(null=True, blank=True, verbose_name="Fecha de Implementación")
    fecha_verificacion = models.DateField(null=True, blank=True, verbose_name="Fecha de Verificación")
    fecha_ultima_actividad = models.DateTimeField(auto_now=True, verbose_name="Última Actividad")
    
    # Campos adicionales
    costo_estimado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Costo Estimado"
    )
    tiempo_estimado_horas = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Tiempo Estimado (horas)"
    )
    recursos_necesarios = models.TextField(blank=True, verbose_name="Recursos Necesarios")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Embudo de Checklist Adicional"
        verbose_name_plural = "Embudos de Checklist Adicionales"
        ordering = ['-fecha_identificacion']
        indexes = [
            models.Index(fields=['etapa', 'prioridad']),
            models.Index(fields=['fecha_identificacion']),
            models.Index(fields=['responsable_implementacion']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.get_etapa_display()}"
    
    @property
    def dias_pendiente(self):
        """Calcula los días que lleva pendiente"""
        if self.etapa in ['IMPLEMENTADO', 'VERIFICADO', 'CERRADO', 'CANCELADO']:
            return 0
        return (timezone.now().date() - self.fecha_identificacion.date()).days
    
    @property
    def esta_vencido(self):
        """Verifica si está vencido"""
        if self.fecha_limite and self.etapa not in ['IMPLEMENTADO', 'VERIFICADO', 'CERRADO', 'CANCELADO']:
            return timezone.now().date() > self.fecha_limite
        return False
    
    @property
    def tiempo_restante(self):
        """Calcula el tiempo restante hasta la fecha límite"""
        if self.fecha_limite and self.etapa not in ['IMPLEMENTADO', 'VERIFICADO', 'CERRADO', 'CANCELADO']:
            return (self.fecha_limite - timezone.now().date()).days
        return None
    
    def avanzar_etapa(self, nueva_etapa, usuario=None):
        """Método para avanzar a la siguiente etapa"""
        etapas = [choice[0] for choice in self.ETAPA_CHOICES]
        etapa_actual_index = etapas.index(self.etapa)
        
        if nueva_etapa in etapas:
            self.etapa = nueva_etapa
            self.fecha_ultima_actividad = timezone.now()
            
            # Actualizar fechas específicas según la etapa
            if nueva_etapa == 'IMPLEMENTADO':
                self.fecha_implementacion = timezone.now().date()
            elif nueva_etapa == 'VERIFICADO':
                self.fecha_verificacion = timezone.now().date()
            
            self.save()
            return True
        return False
    
    def get_color_prioridad(self):
        """Retorna el color CSS para la prioridad"""
        colores = {
            'BAJA': '#28a745',
            'MEDIA': '#ffc107',
            'ALTA': '#fd7e14',
            'CRITICA': '#dc3545',
        }
        return colores.get(self.prioridad, '#6c757d')
    
    def get_color_etapa(self):
        """Retorna el color CSS para la etapa"""
        colores = {
            'IDENTIFICADO': '#17a2b8',
            'EN_ANALISIS': '#6f42c1',
            'PLANIFICADO': '#fd7e14',
            'EN_DESARROLLO': '#ffc107',
            'IMPLEMENTADO': '#28a745',
            'VERIFICADO': '#20c997',
            'CERRADO': '#6c757d',
            'CANCELADO': '#dc3545',
        }
        return colores.get(self.etapa, '#6c757d')


class HistorialFacturacion(models.Model):
    """
    Modelo para almacenar el histórico de facturación de servicios
    importado desde archivos externos.
    """
    pin_equipo = models.CharField(max_length=50, verbose_name='PIN del Equipo')
    fecha_servicio = models.DateField(verbose_name='Fecha de Servicio')
    numero_factura = models.CharField(max_length=50, verbose_name='Número de Factura')
    monto_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto USD')
    tipo_servicio = models.CharField(max_length=100, verbose_name='Tipo de Servicio')
    modelo_equipo = models.CharField(max_length=100, verbose_name='Modelo del Equipo')
    fecha_importacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Importación')
    
    # Relaciones
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, verbose_name='Cliente')
    equipo = models.ForeignKey('clientes.Equipo', blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Equipo')
    
    class Meta:
        verbose_name = 'Historial de Facturación'
        verbose_name_plural = 'Historial de Facturación'
        ordering = ['-fecha_servicio']
        indexes = [
            models.Index(fields=['pin_equipo']),
            models.Index(fields=['fecha_servicio']),
            models.Index(fields=['cliente']),
            models.Index(fields=['equipo']),
        ]
    
    def __str__(self):
        return f"{self.pin_equipo} - {self.fecha_servicio} - ${self.monto_usd}"
    
    @property
    def cliente_nombre(self):
        """Retorna el nombre del cliente"""
        return self.cliente.razon_social if self.cliente else "Sin Cliente"
    
    @property
    def equipo_existe_en_bd(self):
        """Verifica si el equipo existe en la base de datos"""
        return self.equipo is not None
