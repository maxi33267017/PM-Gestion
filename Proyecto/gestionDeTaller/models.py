from django.db import models
from django.db.models import Avg, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings





    
# class CodigoError(models.Model):
#     codigo = models.CharField(max_length=20, unique=True, verbose_name="Código de Error")
#     descripcion = models.TextField(verbose_name="Descripción")
#     subsistema = models.CharField(max_length=100, verbose_name="Subsistema")
#     activo = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = "Código de Error"
#         verbose_name_plural = "Códigos de Error"
#         ordering = ['codigo']

#     def __str__(self):
#         return f"{self.codigo} - {self.subsistema}"

    

from django.db import models

class PreOrden(models.Model):
    TIPO_TRABAJO_CHOICES = [
        ('PRESENCIAL_TALLER', 'Presencial en Taller'),
        ('PRESENCIAL_CAMPO', 'Presencial en Campo'),
        ('REMOTO', 'Asistencia Remota'),
    ]

    # Nueva clasificación para las preórdenes
    CLASIFICACION_CHOICES = [
        ('SPOT', 'Spot'),  # Trabajo no planificado, urgente o inmediato
        ('PROGRAMADO', 'Programado'),  # Trabajo planificado con anticipación
        ('CAMPAÑA', 'Campaña'),  # Trabajo relacionado con una campaña específica
        ('ADICIONAL', 'Adicional'),  # Trabajo adicional no contemplado inicialmente
    ]

    numero = models.AutoField(primary_key=True)
    sucursal = models.ForeignKey(
        'recursosHumanos.Sucursal',
        on_delete=models.PROTECT,
        verbose_name="Sucursal asociada"
    )
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT)
    equipo = models.ForeignKey('clientes.Equipo', on_delete=models.PROTECT)
    horometro = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Horómetro Actual", blank=True, null=True)
    
    solicitud_cliente = models.TextField(verbose_name="Solicitud del Cliente")

    detalles_adicionales = models.TextField(blank=True)
    
    tipo_trabajo = models.CharField(max_length=20, choices=TIPO_TRABAJO_CHOICES)
    tecnicos = models.ManyToManyField('recursosHumanos.Usuario', limit_choices_to={'rol': 'TECNICO'}, related_name='preordenes_tecnicos')
    
    # Nuevo campo para la clasificación de la preorden
    clasificacion = models.CharField(
        max_length=20,
        choices=CLASIFICACION_CHOICES,
        default='SPOT',  # Puedes definir un valor por defecto si lo deseas
        verbose_name="Clasificación de la Preorden"
    )
    
    fecha_estimada = models.DateField(verbose_name="Fecha Estimada de Atención")
    hora_inicio_estimada = models.TimeField(null=True, blank=True)
    hora_fin_estimada = models.TimeField(null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.PROTECT, related_name='preordenes_creadas')
    activo = models.BooleanField(default=True)
    
    # Información del estado del equipo al recibirlo
    trae_llave = models.BooleanField(default=False, verbose_name="¿Trae Llave?")
    estado_cabina = models.CharField(max_length=100, blank=True, verbose_name="Estado de la Cabina")
    estado_neumaticos_tren = models.CharField(max_length=100, blank=True, verbose_name="Estado de Neumáticos/Tren Rodante")
    estado_vidrios = models.CharField(max_length=100, blank=True, verbose_name="Estado de los Vidrios")
    combustible_ingreso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Combustible al Ingreso (%)")
    observaciones_estado_equipo = models.TextField(blank=True, verbose_name="Observaciones del Estado del Equipo")

    # Firma y aclaración del cliente
    firma_cliente = models.ImageField(upload_to='firmas_clientes/', blank=True, null=True, verbose_name="Firma del Cliente")
    nombre_cliente = models.CharField(max_length=100, blank=True, verbose_name="Aclaración del Cliente")
    
    # Campos para códigos de error y métodos adicionales
    codigos_error = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pre Orden"
        verbose_name_plural = "Pre Órdenes"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"PreOrden #{self.numero} - {self.cliente} - {self.equipo}"

    def get_tecnicos_asignados(self):
        return ", ".join([t.get_nombre_completo() for t in self.tecnicos.all()])
    
    def get_codigos_error(self):
        return ", ".join([c.codigo for c in self.codigos_error.all()])

    
    
class Servicio(models.Model):
    ESTADO_CHOICES = [
        ('PROGRAMADO', 'Programado'),
        ('EN_PROCESO', 'En Proceso'),
        ('ESPERA_REPUESTOS', 'En Espera de Repuestos'),
        ('A_FACTURAR', 'Finalizado a Facturar'),
        ('COMPLETADO', 'Completado'),
    ]

    TRABAJO_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('GARANTIA', 'Garantia'),
        ('PIP', 'Pip'),
        ('PRE ENTREGA', 'Pre Entrega'),
        ('TRABAJO_INTERNO', 'Trabajo Interno (Ventas Maquinarias)'),
    ]

    PRIORIDAD_CHOICES = [
        ('0', 'Urgente'),
        ('1', 'Alta'),
        ('2', 'Media'),
        ('3', 'Baja'),
    ]

    preorden = models.OneToOneField(PreOrden, on_delete=models.PROTECT, related_name='servicio')
    fecha_servicio = models.DateField(verbose_name="Fecha de Servicio")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PROGRAMADO')
    horometro_servicio = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Horómetro en Servicio", 
        blank=True, 
        null=True
    )

    # Campo para Orden de Servicio (OR)
    orden_servicio = models.CharField(
        max_length=8, 
        blank=True, 
        null=True, 
        verbose_name="OR (Orden de Servicio)",
        help_text="Número de hasta 8 dígitos de la Orden de Servicio"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    trabajo = models.CharField(max_length=20, choices=TRABAJO_CHOICES)
    numero_factura = models.CharField(max_length=50, blank=True, verbose_name="Número de Factura")
    archivo_factura = models.FileField(upload_to='facturas/', blank=True, verbose_name="Archivo Factura", help_text="Sube un archivo PDF de la factura")
    observaciones = models.TextField(blank=True)
    numero_cotizacion = models.CharField(max_length=50, blank=True, verbose_name="Número de Cotización")
    archivo_cotizacion = models.FileField(upload_to='cotizaciones/', blank=True, verbose_name="Archivo Cotización", help_text="Sube un archivo PDF de la cotización")
    
    archivo_informe = models.FileField(upload_to='informes/', blank=True, verbose_name="Informe de Servicio", help_text="Sube un archivo PDF del informe")
    fecha_envio_documentacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío de Documentación")
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='0')


    valor_mano_obra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor Mano de Obra")

    causa = models.TextField(blank=True, verbose_name="Causa")
    accion_correctiva = models.TextField(blank=True, verbose_name="Acción Correctiva")
    ubicacion = models.TextField(blank=True, verbose_name="Ubicación")
    kilometros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Kilómetros")
    firma_cliente = models.ImageField(upload_to='firmas_clientes/', blank=True, null=True, verbose_name="Firma del Cliente")
    nombre_cliente = models.CharField(max_length=100, blank=True, verbose_name="Nombre del Cliente")

    @classmethod
    def get_tiempo_promedio_cierre(cls):
        """
        Calcula el tiempo promedio de cierre de los servicios completados en días.
        Se mide desde la fecha de creación del servicio hasta la fecha de finalización.
        """
        servicios = cls.objects.filter(estado='COMPLETADO')
        if not servicios.exists():
            return 0
        
        total_dias = servicios.aggregate(
            promedio=Avg(models.F('fecha_servicio') - models.F('fecha_creacion'))
        )['promedio']
        
        return total_dias.days if total_dias else 0

    
    
    def get_facturacion_por_tipo(cls, tipo):
        """
        Retorna la facturación total de servicios completados según la clasificación de la preorden.
        """
        return cls.objects.filter(
            preorden__clasificacion=tipo,
            estado='COMPLETADO'
        ).aggregate(total=Sum('valor_mano_obra'))['total'] or 0

    @classmethod
    def get_facturacion_spot(cls):
        return cls.get_facturacion_por_tipo('SPOT')

    @classmethod
    def get_facturacion_programados(cls):
        return cls.get_facturacion_por_tipo('PROGRAMADO')

    @classmethod
    def get_facturacion_campania(cls):
        return cls.get_facturacion_por_tipo('CAMPAÑA')

    @classmethod
    def get_facturacion_adicional(cls):
        return cls.get_facturacion_por_tipo('ADICIONAL')


    
    def tiene_documentacion_completa(self):
        return bool(self.numero_factura and self.imagen_factura and self.numero_cotizacion and 
                   self.imagen_cotizacion and self.imagen_informe)

    def get_horas_totales(self):
        return self.registrohorastecnico_set.aggregate(
            total=Sum('get_horas_totales')
        )['total'] or 0

    def get_valor_mano_obra(self):
            from recursosHumanos.models import TarifaManoObra
            total = 0
            registros = self.registrohorastecnico_set.all()
            cantidad_tecnicos = registros.values('tecnico').distinct().count()

            # Determinar el tipo de tarifa en base al tipo de trabajo (campo o taller) y cantidad de técnicos
            tipo_servicio = 'CAMPO' if self.preorden.tipo_trabajo == 'PRESENCIAL_CAMPO' else 'TALLER'
            tipo_tarifa = 'MULTIPLE' if cantidad_tecnicos > 1 else 'INDIVIDUAL'

            # Obtener la tarifa vigente
            tarifa = TarifaManoObra.objects.filter(
                tipo_servicio=tipo_servicio,
                tipo=tipo_tarifa,
                activo=True
            ).order_by('-fecha_vigencia').first()

            # Verificar que se haya encontrado una tarifa
            if tarifa:
                for registro in registros:
                    horas = registro.get_horas_totales()
                    total += horas * tarifa.valor_hora
            else:
                # Log or handle cases where no tarifa is found
                print("No se encontró tarifa de mano de obra activa para el tipo y servicio especificados.")
            return total
    def __str__(self):
        return f"Orden {self.id}"
    
    def save(self, *args, **kwargs):
        from clientes.models import RegistroHorometro
        # Establece un valor inicial para horometro_servicio si se crea el servicio
        if self.horometro_servicio is None:
            if self.preorden.horometro:  # Si la preorden tiene un horómetro asignado
                self.horometro_servicio = self.preorden.horometro

        # Llama al método save() original para guardar el servicio
        super().save(*args, **kwargs)

        # Actualiza el registro de horas del equipo después de guardar el servicio
        if self.horometro_servicio:
            # Crea o actualiza el registro de horómetro del equipo con el valor del servicio
            RegistroHorometro.objects.create(
                equipo=self.preorden.equipo,
                horas=self.horometro_servicio,
                origen='SERVICIO',
                usuario=self.preorden.creado_por,
                observaciones="Registro automático desde servicio"
            )

            # Actualiza la última hora registrada en el equipo (esto puede ser un campo en el equipo)
            self.preorden.equipo.ultima_hora_registrada = self.horometro_servicio
            self.preorden.equipo.save()
    
    @property
    def esta_firmado(self):
        """Verifica si el servicio tiene firma del cliente"""
        return bool(self.firma_cliente)
    
    @property
    def puede_retroceder_estado(self):
        """Verifica si el servicio puede retroceder a estados anteriores"""
        return self.estado != 'A_FACTURAR'
    
    def puede_cambiar_a_estado(self, nuevo_estado, usuario=None):
        """
        Verifica si el servicio puede cambiar a un estado específico
        
        Args:
            nuevo_estado: Estado al que se quiere cambiar
            usuario: Usuario que intenta hacer el cambio
        
        Returns:
            tuple: (bool, str) - (puede_cambiar, mensaje_error)
        """
        from .security import puede_cambiar_estado, es_transicion_valida
        
        # Si no se especifica usuario, permitir (para validaciones generales)
        if usuario:
            if not puede_cambiar_estado(usuario, self, nuevo_estado):
                return False, f"No tienes permisos para cambiar a '{nuevo_estado}'"
        
        # Verificar transición válida
        if not es_transicion_valida(self.estado, nuevo_estado):
            return False, f"No se puede cambiar de '{self.get_estado_display()}' a '{dict(self.ESTADO_CHOICES)[nuevo_estado]}'"
        
        return True, "Cambio válido"
    
    def cambiar_estado(self, nuevo_estado, usuario, motivo=""):
        """
        Cambia el estado del servicio con validaciones de seguridad
        
        Args:
            nuevo_estado: Nuevo estado
            usuario: Usuario que hace el cambio
            motivo: Motivo del cambio (opcional)
        
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        from .security import validar_cambio_estado, registrar_cambio_estado
        
        # Validar el cambio
        es_valido, mensaje = validar_cambio_estado(usuario, self, nuevo_estado)
        if not es_valido:
            return False, mensaje
        
        # Registrar el cambio
        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save()
        
        # Crear log de auditoría
        registrar_cambio_estado(self, usuario, estado_anterior, nuevo_estado, motivo)
        
        return True, f"Estado cambiado exitosamente de '{estado_anterior}' a '{nuevo_estado}'"

class PedidoRepuestosTerceros(models.Model):
    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('EN_TRANSITO', 'En Tránsito'),
        ('RECIBIDO', 'Recibido'),
        ('CANCELADO', 'Cancelado'),
    ]

    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='pedidos')
    proveedor = models.CharField(max_length=200, verbose_name="Proveedor")
    numero_pedido = models.CharField(max_length=50, verbose_name="Número de Pedido")
    fecha_pedido = models.DateField(verbose_name="Fecha de Pedido")
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso", null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Total")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='SOLICITADO')
    descripcion = models.TextField(verbose_name="Descripción del Pedido")
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pedido de Repuestos y Terceros"
        verbose_name_plural = "Pedidos de Repuestos y Terceros"
        ordering = ['-fecha_pedido']

    def __str__(self):
        return f"Pedido #{self.numero_pedido} - {self.servicio}"
    

class GastoAsistencia(models.Model):
    TIPO_GASTO = [
        ('VIAJE', 'Gastos de Viaje'),
        ('HOSPEDAJE', 'Hospedaje'),
        ('COMIDA', 'Comidas'),
        ('COMBUSTIBLE', 'Combustible'),
        ('OTROS', 'Otros Gastos'),
    ]

    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='gastos')
    tipo = models.CharField(max_length=20, choices=TIPO_GASTO)
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    comprobante = models.ImageField(upload_to='comprobantes/', blank=True)
    
    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.monto}"
    

class VentaRepuesto(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='repuestos')
    codigo = models.CharField(max_length=50, verbose_name="Código Repuesto")
    descripcion = models.CharField(max_length=200)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario", null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")

    def get_subtotal(self):
        return self.cantidad * self.precio_unitario

    def get_costo_total(self):
        return self.cantidad * self.costo_unitario

    def get_margen(self):
        return ((self.precio_unitario - self.costo_unitario) / self.costo_unitario) * 100



class Revision5S(models.Model):
    ESTADO_CHOICES = [
        ('CONFORME', 'Conforme'),
        ('NO_CONFORME', 'No Conforme'),
    ]

    sucursal = models.ForeignKey('recursosHumanos.Sucursal', on_delete=models.PROTECT)
    evaluador = models.ForeignKey(
        'recursosHumanos.Usuario',  # Updated to correct path
        on_delete=models.PROTECT,
        limit_choices_to={'rol__in': ['GERENTE', 'TECNICO', 'ADMINISTRATIVO']}
    )
    fecha_revision = models.DateField()
    fecha_proxima = models.DateField()
    
    # Seiri (Clasificar) - Organizar y clasificar elementos necesarios
    box_trabajo_limpios = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Box de trabajo están limpios, sin aceite, ordenados y sin elementos en el piso"
    )
    mesas_trabajo_estaticas = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Mesas de trabajo estáticas están limpias, sin elementos ajenos a un trabajo en curso"
    )
    herramientas_uso_comun_devueltas = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Las herramientas de uso común o especiales han sido devueltas y se encuentran limpias (sin contar las que se estén usando en un trabajo en curso)"
    )
    
    # Seiton (Ordenar) - Organizar elementos para uso eficiente
    paredes_limpias_tachos_ok = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Las paredes están limpias y los cestos de basura están siendo vaciados según corresponda"
    )
  
    sala_garantia_ordenada = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Sala de garantía se encuentra ordenada y con los elementos e información que corresponde según los procedimientos"
    )
    zona_repuestos_ordenada = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="La zona de repuestos dentro del taller se encuentra ordenada, identificada y con elementos correctamente ubicados"
    )
    
    # Seiso (Limpiar) - Mantener limpieza y orden
    epp_correspondiente_usado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Se están usando los EPP correspondientes en los trabajos en curso y todos tienen el uniforme correspondiente"
    )
    herramientas_calibradas_certificadas = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Todas las herramientas se encuentran calibradas y certificadas (las que correspondan)"
    )

    
    # Seiketsu (Estandarizar) - Estandarizar procesos y procedimientos
    procedimientos_seguidos = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Los procedimientos de trabajo se siguen correctamente según los estándares establecidos"
    )

    mantenimiento_preventivo = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="El mantenimiento preventivo de equipos y herramientas se realiza según el cronograma establecido"
    )
    
    # Shitsuke (Disciplina) - Mantener la disciplina y mejorar continuamente
    residuos_gestionados = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Los residuos depositados afuera del taller se gestionan correctamente según los procedimientos de reciclaje y disposición"
    )
    mejora_continua = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES,
        default='CONFORME',
        verbose_name="Se identifican y documentan oportunidades de mejora en los procesos de trabajo"
    )


    porcentaje_conformidad = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    # Campo de evidencias removido - ahora se maneja con modelo separado


    class Meta:
        verbose_name = "Revisión 5S"
        verbose_name_plural = "Revisiones 5S"
        ordering = ['-fecha_revision']

    def __str__(self):
        return f"Revisión 5S - {self.sucursal} - {self.fecha_revision}"

    def calcular_conformidad(self):
        campos = [
            self.box_trabajo_limpios, self.mesas_trabajo_estaticas, self.herramientas_uso_comun_devueltas,
            self.paredes_limpias_tachos_ok, self.sala_garantia_ordenada, self.zona_repuestos_ordenada,
            self.epp_correspondiente_usado, self.herramientas_calibradas_certificadas,
            self.procedimientos_seguidos, self.mantenimiento_preventivo,
            self.residuos_gestionados, self.mejora_continua
        ]
        total = len(campos)
        conformes = campos.count('CONFORME')
        return (conformes / total * 100) if total > 0 else 0

    def save(self, *args, **kwargs):
        self.porcentaje_conformidad = self.calcular_conformidad()
        super().save(*args, **kwargs)


class EvidenciaRevision5S(models.Model):
    """Modelo para múltiples evidencias de revisiones 5S"""
    revision = models.ForeignKey(Revision5S, on_delete=models.CASCADE, related_name='evidencias')
    imagen = models.ImageField(upload_to='5s/revision/evidencias/', verbose_name="Evidencia")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    
    class Meta:
        verbose_name = "Evidencia de Revisión 5S"
        verbose_name_plural = "Evidencias de Revisiones 5S"
        ordering = ['-fecha_subida']
    
    def __str__(self):
        return f"Evidencia {self.id} - {self.revision}"


class EvidenciaPlanAccion5S(models.Model):
    """Modelo para múltiples evidencias de planes de acción 5S"""
    plan_accion = models.ForeignKey('PlanAccion5S', on_delete=models.CASCADE, related_name='evidencias')
    imagen = models.ImageField(upload_to='5s/planes/evidencias/', verbose_name="Evidencia")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")

    class Meta:
        verbose_name = "Evidencia de Plan de Acción 5S"
        verbose_name_plural = "Evidencias de Planes de Acción 5S"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Evidencia {self.id} - {self.plan_accion}"

class PlanAccion5S(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
    ]

    revision = models.ForeignKey(Revision5S, on_delete=models.CASCADE, related_name='planes_accion')
    item_no_conforme = models.TextField()
    accion_correctiva = models.TextField()
    responsable = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.PROTECT)
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_cierre = models.DateField(null=True, blank=True)
    evidencia_despues = models.ImageField(upload_to='5s/despues/', blank=True)  # Mantener para compatibilidad
    observaciones = models.TextField(blank=True)

    @classmethod
    def get_items_no_conformes(cls, revision):
        items_no_conformes = []
        for field in revision._meta.fields:
            if isinstance(field, models.CharField) and field.choices == Revision5S.ESTADO_CHOICES:
                if getattr(revision, field.name) == 'NO_CONFORME':
                    items_no_conformes.append(field.verbose_name or field.name)
        return items_no_conformes

    class Meta:
        verbose_name = "Plan de Acción 5S"
        verbose_name_plural = "Planes de Acción 5S"
        ordering = ['fecha_limite']

    def __str__(self):
        return f"Plan de Acción - {self.item_no_conforme}"
    


class CostoPersonalTaller(models.Model):
    sucursal = models.ForeignKey('recursosHumanos.Sucursal', on_delete=models.PROTECT)
    usuario = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.PROTECT)
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)
    cargas_sociales = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vigencia = models.DateField()
    activo = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Costo Personal de Taller"
        verbose_name_plural = "Costos Personal de Taller"


class AnalisisTaller(models.Model):
    sucursal = models.ForeignKey('recursosHumanos.Sucursal', on_delete=models.PROTECT)
    mes = models.DateField()
    
    # Ingresos
    facturacion_mano_obra = models.DecimalField(max_digits=12, decimal_places=2)
    facturacion_repuestos = models.DecimalField(max_digits=12, decimal_places=2)
    facturacion_asistencia = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Costos
    costo_personal = models.DecimalField(max_digits=12, decimal_places=2)
    costo_operativo = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Analisis de Taller"
        verbose_name_plural = "Analisis de Taller"
 
    
    def get_margen_bruto(self):
        ingresos = self.facturacion_mano_obra + self.facturacion_repuestos + self.facturacion_asistencia
        costos = self.costo_personal + self.costo_operativo
        return ingresos - costos

    def get_rentabilidad(self):
        ingresos = self.facturacion_mano_obra + self.facturacion_repuestos + self.facturacion_asistencia
        return (self.get_margen_bruto() / ingresos * 100) if ingresos else 0
    
    def get_costos_fijos(self):
        return self.costo_personal + self.gastos_fijos

    def get_costos_variables(self):
        return self.costo_operativo + self.gastos_variables

    def get_punto_equilibrio(self):
        if self.get_costos_variables() == 0:
            return 0
        return self.get_costos_fijos() / (1 - (self.get_costos_variables() / self.facturacion_total))

    def get_roi(self):
        inversion = self.get_costos_fijos() + self.get_costos_variables()
        if inversion == 0:
            return 0
        return ((self.facturacion_total - inversion) / inversion) * 100

    @classmethod
    def get_top_clientes(cls, sucursal, año):
        return 'clientes.Cliente'.objects.annotate(
            total_facturacion=Sum(
                'servicios__valor_mano_obra' +
                'servicios__gastos__monto' +
                'servicios__repuestos__precio_unitario' * 'servicios__repuestos__cantidad'
            )
        ).filter(
            servicios__sucursal=sucursal,
            servicios__fecha_servicio__year=año
        ).order_by('-total_facturacion')


class Evidencia(models.Model):
    preorden = models.ForeignKey(PreOrden, related_name='evidencias', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='evidencias/')
    fecha_subida = models.DateTimeField(auto_now_add=True)


class CategoriaEquipo(models.TextChoices):
    MAQUINARIA = 'Maquinaria', 'Maquinaria'
    GRUPO_ELECTROGENO = 'Grupo Electrógeno', 'Grupo Electrógeno'
    TORRE_ILUMINACION = 'Torre de Iluminación', 'Torre de Iluminación'

class ChecklistSalidaCampo(models.Model):
    servicio = models.OneToOneField(Servicio, on_delete=models.CASCADE, related_name='checklist_salida_campo')

    # Categoría de equipo y cliente
    tipo_equipo = models.CharField(max_length=50, choices=CategoriaEquipo.choices)

    # Vehículo para servicio
    nivel_aceite_motor = models.BooleanField(default=False, verbose_name="Nivel de Aceite Motor Correcto")
    nivel_refrigerante = models.BooleanField(default=False, verbose_name="Nivel de Refrigerante Correcto")
    nivel_combustible = models.BooleanField(default=False, verbose_name="Nivel de Combustible Correcto")
    estado_neumaticos = models.BooleanField(default=False, verbose_name="Estado de Neumáticos Correcto")
    luces = models.BooleanField(default=False, verbose_name="Luces Funcionando")
    carroceria = models.BooleanField(default=False, verbose_name="Carrocería en Buen Estado")

    # Checklist de ejecución de servicio
    preorden = models.BooleanField(default=False, verbose_name="Preorden Confirmada")
    orden_servicio = models.BooleanField(default=False, verbose_name="Orden de Servicio Confirmada")
    herramientas_basicas = models.BooleanField(default=False, verbose_name="Herramientas Básicas Listas")
    herramientas_especiales = models.BooleanField(default=False, verbose_name="Herramientas Especiales Listas")
    repuestos = models.BooleanField(default=False, verbose_name="Repuestos Preparados")
    cobertores = models.BooleanField(default=False, verbose_name="Cobertores Listos")

    # Tiempo de preparación del equipo
    tiempo_preparacion = models.DurationField(verbose_name="Tiempo de Preparación (Horas:Minutos)")

    def __str__(self):
        return f"Checklist para servicio {self.servicio}"
    

class EncuestaServicio(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='encuestas')
    fecha_envio = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=[
        ('ENVIADA', 'Enviada'),
        ('RESPONDIDA', 'Respondida'),
        ('NO_RESPONDIDA', 'No Respondida')
    ], default='ENVIADA')
    link_encuesta = models.URLField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Encuesta de Servicio'
        verbose_name_plural = 'Encuestas de Servicios'
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"Encuesta para Servicio #{self.servicio.id} - {self.estado}"

    def enviar_encuesta(self):
        """Envía la encuesta por correo electrónico al cliente."""
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        cliente = self.servicio.preorden.cliente
        destinatarios = [cliente.email] if cliente.email else []
        
        # Agregar correos de contactos del cliente
        for contacto in cliente.contactos.all():
            if contacto.email:
                destinatarios.append(contacto.email)

        if destinatarios:
            asunto = f"Encuesta de Satisfacción - Servicio #{self.servicio.id}"
            mensaje_html = render_to_string('gestionDeTaller/encuestas/email_encuesta.html', {
                'servicio': self.servicio,
                'cliente': cliente,
                'link_encuesta': self.link_encuesta
            })
            mensaje_texto = strip_tags(mensaje_html)

            email = EmailMultiAlternatives(
                asunto,
                mensaje_texto,
                to=destinatarios,
                cc=settings.CC_EMAILS  # Agregar los correos en CC
            )
            email.attach_alternative(mensaje_html, "text/html")
            email.send()

            self.estado = 'ENVIADA'
            self.save()

class RespuestaEncuesta(models.Model):
    encuesta = models.ForeignKey(EncuestaServicio, on_delete=models.CASCADE, related_name='respuestas')
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    
    # Pregunta 1: Cumplimiento del acuerdo
    cumplimiento_acuerdo = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)], 
        verbose_name="Del momento del agendamiento hasta la entrega del Equipo, ¿Lo que fue acordado fue cumplido?",
        help_text="Calificación del 1 al 10",
        null=True,
        blank=True
    )
    motivo_cumplimiento_bajo = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Si la respuesta fue menor o igual a 7, ¿podría decirnos por qué?"
    )
    
    # Pregunta 2: Probabilidad de recomendación (NPS)
    probabilidad_recomendacion = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)], 
        verbose_name="En una escala de 1 a 10, ¿cuán probable es que recomiende el Servicio del Concesionario a otras personas?",
        help_text="Calificación del 1 al 10",
        null=True,
        blank=True
    )
    motivo_recomendacion_baja = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Si la respuesta fue menor o igual a 7, ¿podría decirnos por qué?"
    )
    
    # Pregunta 3: Problemas pendientes
    problemas_pendientes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="¿Algún pendiente o problema no resuelto?"
    )
    
    # Campos adicionales
    comentarios_generales = models.TextField(blank=True, null=True, verbose_name="Comentarios adicionales")
    nombre_respondente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del respondente")
    cargo_respondente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cargo del respondente")

    class Meta:
        verbose_name = "Respuesta de Encuesta"
        verbose_name_plural = "Respuestas de Encuestas"

    def __str__(self):
        return f"Respuesta para Servicio #{self.encuesta.servicio.id} - {self.fecha_respuesta}"
    
    def get_nps_category(self):
        """Determina la categoría NPS basada en la probabilidad de recomendación"""
        if self.probabilidad_recomendacion >= 9:
            return "Promotor"
        elif self.probabilidad_recomendacion >= 7:
            return "Pasivo"
        else:
            return "Detractor"
    
    def get_cumplimiento_category(self):
        """Determina la categoría del cumplimiento del acuerdo"""
        if self.cumplimiento_acuerdo >= 9:
            return "Excelente"
        elif self.cumplimiento_acuerdo >= 7:
            return "Bueno"
        elif self.cumplimiento_acuerdo >= 5:
            return "Regular"
        else:
            return "Deficiente"
    

class InsatisfaccionCliente(models.Model):
    encuesta = models.ForeignKey(EncuestaServicio, on_delete=models.CASCADE, related_name='insatisfacciones')
    fecha_comunicacion = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='insatisfacciones_atendidas')
    descripcion_problema = models.TextField()
    solucion = models.TextField(blank=True, null=True)
    fecha_solucion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('EN_PROCESO', 'En Proceso'),
            ('RESUELTO', 'Resuelto'),
            ('CERRADO', 'Cerrado')
        ],
        default='PENDIENTE'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Insatisfacción de Cliente'
        verbose_name_plural = 'Insatisfacciones de Clientes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Insatisfacción - Servicio #{self.encuesta.servicio.id} - {self.get_estado_display()}"
    

class LogCambioServicio(models.Model):
    """Modelo para registrar cambios de estado en servicios"""
    
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='logs_cambios')
    usuario = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE, related_name='cambios_estado_realizados')
    estado_anterior = models.CharField(max_length=50, verbose_name="Estado Anterior")
    estado_nuevo = models.CharField(max_length=50, verbose_name="Estado Nuevo")
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Cambio")
    motivo = models.TextField(blank=True, null=True, verbose_name="Motivo del Cambio")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Dirección IP")
    
    class Meta:
        verbose_name = "Log de Cambio de Estado"
        verbose_name_plural = "Logs de Cambios de Estado"
        ordering = ['-fecha_cambio']
        indexes = [
            models.Index(fields=['servicio', 'fecha_cambio']),
            models.Index(fields=['usuario', 'fecha_cambio']),
        ]
    
    def __str__(self):
        return f"Servicio {self.servicio.id}: {self.estado_anterior} → {self.estado_nuevo} por {self.usuario.nombre}"
    
    @property
    def tiempo_transcurrido(self):
        """Calcula el tiempo transcurrido desde el cambio"""
        return timezone.now() - self.fecha_cambio
    

class LogCambioInforme(models.Model):
    """Modelo para registrar cambios en informes de servicios"""
    
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='logs_cambios_informe')
    usuario = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE, related_name='cambios_informe_realizados')
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Cambio")
    campo_modificado = models.CharField(max_length=100, verbose_name="Campo Modificado")
    valor_anterior = models.TextField(blank=True, null=True, verbose_name="Valor Anterior")
    valor_nuevo = models.TextField(blank=True, null=True, verbose_name="Valor Nuevo")
    motivo = models.TextField(blank=True, null=True, verbose_name="Motivo del Cambio")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Dirección IP")
    
    class Meta:
        verbose_name = "Log de Cambio de Informe"
        verbose_name_plural = "Logs de Cambios de Informe"
        ordering = ['-fecha_cambio']
        indexes = [
            models.Index(fields=['servicio', 'fecha_cambio']),
            models.Index(fields=['usuario', 'fecha_cambio']),
        ]
    
    def __str__(self):
        return f"Informe Servicio {self.servicio.id}: {self.campo_modificado} por {self.usuario.nombre}"
    
    @property
    def tiempo_transcurrido(self):
        """Calcula el tiempo transcurrido desde el cambio"""
        return timezone.now() - self.fecha_cambio
    

class ObservacionServicio(models.Model):
    """Modelo para el historial de observaciones de servicios"""
    
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='observaciones_historial')
    usuario = models.ForeignKey('recursosHumanos.Usuario', on_delete=models.CASCADE, verbose_name="Usuario")
    observacion = models.TextField(verbose_name="Observación")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    class Meta:
        verbose_name = "Observación de Servicio"
        verbose_name_plural = "Observaciones de Servicios"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['servicio', '-fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Observación #{self.id} - {self.servicio} - {self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"
    
    def get_fecha_formateada(self):
        """Retorna la fecha formateada para mostrar"""
        return self.fecha_creacion.strftime('%d/%m/%Y %H:%M')


class Repuesto(models.Model):
    """Modelo para almacenar la base de datos de repuestos"""
    
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código del Repuesto")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    costo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Costo"
    )
    precio_venta = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Precio de Venta"
    )
    
    # Campos adicionales
    categoria = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Categoría",
        help_text="Ej: Filtros, Aceites, Neumáticos, etc."
    )
    proveedor = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Proveedor"
    )
    stock_minimo = models.PositiveIntegerField(
        default=0, 
        verbose_name="Stock Mínimo"
    )
    ubicacion_almacen = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Ubicación en Almacén"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='repuestos_creados',
        verbose_name="Creado por"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Repuesto"
        verbose_name_plural = "Repuestos"
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['categoria']),
            models.Index(fields=['proveedor']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:50] if self.descripcion else 'Sin descripción'}"
    
    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia en porcentaje"""
        if self.costo and self.precio_venta:
            return ((self.precio_venta - self.costo) / self.costo) * 100
        return 0
    
    @property
    def ganancia_unitaria(self):
        """Calcula la ganancia unitaria"""
        if self.costo and self.precio_venta:
            return self.precio_venta - self.costo
        return 0 
    

class HerramientaEspecial(models.Model):
    """Modelo para herramientas especiales John Deere"""
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=255, verbose_name="Nombre")
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    ubicacion = models.CharField(max_length=255, verbose_name="Ubicación")
    foto = models.ImageField(
        upload_to='herramientas_especiales/', 
        blank=True, 
        null=True, 
        verbose_name="Foto"
    )
    nota = models.TextField(blank=True, null=True, verbose_name="Nota")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='herramientas_creadas',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Herramienta Especial"
        verbose_name_plural = "Herramientas Especiales"
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def disponible(self):
        """Verifica si la herramienta está disponible para la fecha actual"""
        from django.utils import timezone
        from datetime import date
        
        hoy = date.today()
        reservas_activas = self.reservas.filter(
            fecha_reserva=hoy,
            estado__in=['RESERVADA', 'RETIRADA']
        )
        return not reservas_activas.exists()
    
    @property
    def estado_actual(self):
        """Retorna el estado actual de la herramienta"""
        if not self.disponible:
            return "No Disponible"
        return "Disponible"
    
    @property
    def reserva_actual(self):
        """Retorna la reserva actual si existe"""
        from django.utils import timezone
        from datetime import date
        
        hoy = date.today()
        return self.reservas.filter(
            fecha_reserva=hoy,
            estado__in=['RESERVADA', 'RETIRADA']
        ).first()


class ReservaHerramienta(models.Model):
    """Modelo para reservas de herramientas especiales"""
    ESTADO_CHOICES = [
        ('RESERVADA', 'Reservada'),
        ('RETIRADA', 'Retirada'),
        ('DEVUELTA', 'Devuelta'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    herramienta = models.ForeignKey(
        HerramientaEspecial, 
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name="Herramienta"
    )
    usuario = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Usuario"
    )
    fecha_reserva = models.DateField(verbose_name="Fecha de Reserva")
    preorden = models.ForeignKey(
        'gestionDeTaller.PreOrden', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Pre-Orden"
    )
    servicio = models.ForeignKey(
        'gestionDeTaller.Servicio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Servicio"
    )
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='RESERVADA',
        verbose_name="Estado"
    )
    fecha_retiro = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Retiro")
    fecha_devolucion = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Devolución")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Reserva de Herramienta"
        verbose_name_plural = "Reservas de Herramientas"
        ordering = ['-fecha_reserva', '-fecha_creacion']
    
    def __str__(self):
        return f"{self.herramienta.codigo} - {self.fecha_reserva} - {self.get_estado_display()}"
    
    def marcar_retirada(self):
        """Marca la herramienta como retirada"""
        from django.utils import timezone
        self.estado = 'RETIRADA'
        self.fecha_retiro = timezone.now()
        self.save()
        
        # Crear log
        LogHerramienta.objects.create(
            herramienta=self.herramienta,
            usuario=self.usuario,
            accion='RETIRO',
            reserva=self,
            observaciones=f"Herramienta retirada por {self.usuario.get_full_name() or self.usuario.username if self.usuario else 'Usuario'}"
        )
    
    def marcar_devuelta(self):
        """Marca la herramienta como devuelta"""
        from django.utils import timezone
        self.estado = 'DEVUELTA'
        self.fecha_devolucion = timezone.now()
        self.save()
        
        # Crear log
        LogHerramienta.objects.create(
            herramienta=self.herramienta,
            usuario=self.usuario,
            accion='DEVOLUCION',
            reserva=self,
            observaciones=f"Herramienta devuelta por {self.usuario.get_full_name() or self.usuario.username if self.usuario else 'Usuario'}"
        )


class LogHerramienta(models.Model):
    """Modelo para el log de movimientos de herramientas"""
    ACCION_CHOICES = [
        ('RESERVA', 'Reserva'),
        ('RETIRO', 'Retiro'),
        ('DEVOLUCION', 'Devolución'),
        ('CANCELACION', 'Cancelación'),
    ]
    
    herramienta = models.ForeignKey(
        HerramientaEspecial, 
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Herramienta"
    )
    usuario = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Usuario"
    )
    accion = models.CharField(
        max_length=20, 
        choices=ACCION_CHOICES,
        verbose_name="Acción"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    reserva = models.ForeignKey(
        ReservaHerramienta, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Reserva"
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Log de Herramienta"
        verbose_name_plural = "Logs de Herramientas"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.herramienta.codigo} - {self.get_accion_display()} - {self.fecha}" 
    

class HerramientaPersonal(models.Model):
    """Modelo para el catálogo de herramientas personales"""
    CATEGORIA_CHOICES = [
        ('CAJA_HERRAMIENTAS', 'Caja de Herramientas'),
        ('TESTER', 'Tester/Multímetro'),
        ('HERRAMIENTA_ADICIONAL', 'Herramienta Adicional'),
        ('EPP', 'Elemento de Protección Personal'),
    ]
    
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('ASIGNADA', 'Asignada'),
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('PERDIDA', 'Perdida'),
        ('DAÑADA', 'Dañada'),
        ('VENCIDA', 'Vencida'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=255, verbose_name="Nombre")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, verbose_name="Categoría")
    marca = models.CharField(max_length=100, blank=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    costo_reposicion = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Costo de Reposición"
    )
    vida_util_meses = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Vida Útil (meses)"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        verbose_name="Estado"
    )
    
    # Campos de certificación
    fecha_certificacion = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Certificación"
    )
    fecha_vencimiento_certificacion = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Vencimiento de Certificación"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    creado_por = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='herramientas_personales_creadas',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Herramienta Personal"
        verbose_name_plural = "Herramientas Personales"
        ordering = ['categoria', 'nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def es_epp(self):
        """Verifica si es un elemento de protección personal"""
        return self.categoria == 'EPP'
    
    @property
    def asignacion_actual(self):
        """Retorna la asignación actual activa de la herramienta"""
        return self.asignaciones.filter(estado_asignacion='ENTREGADA').first()
    
    @property
    def requiere_certificacion(self):
        """Verifica si la herramienta requiere certificación"""
        return self.categoria in ['TESTER', 'HERRAMIENTA_ADICIONAL']
    
    @property
    def certificacion_vencida(self):
        """Verifica si la certificación está vencida"""
        if not self.fecha_vencimiento_certificacion:
            return False
        from django.utils import timezone
        return self.fecha_vencimiento_certificacion < timezone.now().date()
    
    @property
    def certificacion_proxima_vencer(self):
        """Verifica si la certificación está próxima a vencer (30 días)"""
        if not self.fecha_vencimiento_certificacion:
            return False
        from django.utils import timezone
        from datetime import timedelta
        fecha_limite = timezone.now().date() + timedelta(days=30)
        return self.fecha_vencimiento_certificacion <= fecha_limite
    
    @property
    def dias_vencimiento_certificacion(self):
        """Retorna los días restantes para el vencimiento de la certificación"""
        if not self.fecha_vencimiento_certificacion:
            return None
        from django.utils import timezone
        from datetime import date
        return (self.fecha_vencimiento_certificacion - date.today()).days
    
    @property
    def total_items(self):
        """Retorna el total de items en la herramienta"""
        return self.items.count()
    
    @property
    def items_presentes(self):
        """Retorna el número de items presentes"""
        return self.items.filter(estado='PRESENTE').count()
    
    @property
    def items_ausentes(self):
        """Retorna el número de items ausentes"""
        return self.items.filter(estado='AUSENTE').count()
    
    @property
    def items_danados(self):
        """Retorna el número de items dañados"""
        return self.items.filter(estado='DAÑADO').count()
    
    @property
    def items_requieren_reposicion(self):
        """Retorna el número de items que requieren reposición"""
        return self.items.filter(estado__in=['AUSENTE', 'DAÑADO', 'VENCIDO']).count()
    
    @property
    def completitud_herramienta(self):
        """Retorna el porcentaje de completitud de la herramienta"""
        if self.total_items == 0:
            return 100
        return round((self.items_presentes / self.total_items) * 100, 1)
    
    @property
    def tiene_items_criticos(self):
        """Verifica si la herramienta tiene items críticos ausentes"""
        return self.items.filter(estado='AUSENTE', cantidad=1).exists()


class ItemHerramientaPersonal(models.Model):
    """Modelo para items individuales dentro de herramientas personales"""
    ESTADO_CHOICES = [
        ('PRESENTE', 'Presente'),
        ('AUSENTE', 'Ausente'),
        ('DAÑADO', 'Dañado'),
        ('DESGASTADO', 'Desgastado'),
        ('VENCIDO', 'Vencido'),
    ]
    
    herramienta = models.ForeignKey(
        HerramientaPersonal, 
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Herramienta"
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Item")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PRESENTE',
        verbose_name="Estado"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Item de Herramienta Personal"
        verbose_name_plural = "Items de Herramientas Personales"
        ordering = ['herramienta', 'nombre']
        unique_together = ['herramienta', 'nombre']
    
    def __str__(self):
        return f"{self.herramienta.nombre} - {self.nombre}"
    
    @property
    def requiere_reposicion(self):
        """Verifica si el item requiere reposición"""
        return self.estado in ['AUSENTE', 'DAÑADO', 'VENCIDO']
    
    @property
    def es_critico(self):
        """Verifica si el item es crítico para la herramienta"""
        return self.estado == 'AUSENTE' and self.cantidad == 1





class AsignacionHerramientaPersonal(models.Model):
    """Modelo para asignaciones de herramientas personales a técnicos"""
    ESTADO_CHOICES = [
        ('ENTREGADA', 'Entregada'),
        ('DEVUELTA', 'Devuelta'),
        ('PERDIDA', 'Perdida'),
        ('DAÑADA', 'Dañada'),
        ('VENCIDA', 'Vencida'),
    ]
    
    tecnico = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.CASCADE,
        related_name='asignaciones_herramientas',
        verbose_name="Técnico"
    )
    herramienta = models.ForeignKey(
        HerramientaPersonal, 
        on_delete=models.CASCADE,
        related_name='asignaciones',
        verbose_name="Herramienta"
    )
    fecha_asignacion = models.DateField(verbose_name="Fecha de Asignación")
    fecha_devolucion = models.DateField(blank=True, null=True, verbose_name="Fecha de Devolución")
    estado_asignacion = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='ENTREGADA',
        verbose_name="Estado"
    )
    observaciones_asignacion = models.TextField(blank=True, verbose_name="Observaciones")
    observaciones_devolucion = models.TextField(blank=True, verbose_name="Observaciones de Devolución")
    asignado_por = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='herramientas_asignadas',
        verbose_name="Asignado por"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Asignación de Herramienta Personal"
        verbose_name_plural = "Asignaciones de Herramientas Personales"
        ordering = ['-fecha_asignacion', '-fecha_creacion']
        unique_together = ['tecnico', 'herramienta', 'estado_asignacion']
    
    def __str__(self):
        return f"{self.tecnico.get_full_name()} - {self.herramienta.nombre}"
    
    @property
    def dias_asignada(self):
        """Calcula los días que lleva asignada la herramienta"""
        from django.utils import timezone
        from datetime import date
        return (date.today() - self.fecha_asignacion).days
    
    @property
    def proxima_vencer(self):
        """Verifica si la herramienta está próxima a vencer"""
        if self.herramienta.vida_util_meses:
            dias_vida_util = self.herramienta.vida_util_meses * 30
            dias_restantes = dias_vida_util - self.dias_asignada
            return dias_restantes <= 30  # Alerta 30 días antes
        return False


class AuditoriaHerramientaPersonal(models.Model):
    """Modelo para auditorías de herramientas personales"""
    TIPO_AUDITORIA_CHOICES = [
        ('SEMESTRAL', 'Semestral'),
        ('EXTRAORDINARIA', 'Extraordinaria'),
        ('DEVOLUCION', 'Devolución'),
        ('VENCIMIENTO', 'Vencimiento'),
    ]
    
    ESTADO_GENERAL_CHOICES = [
        ('EXCELENTE', 'Excelente'),
        ('BUENO', 'Bueno'),
        ('REGULAR', 'Regular'),
        ('MALO', 'Malo'),
    ]
    
    tecnico = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.CASCADE,
        related_name='auditorias_herramientas',
        verbose_name="Técnico"
    )
    fecha_auditoria = models.DateField(verbose_name="Fecha de Auditoría")
    auditor = models.ForeignKey(
        'recursosHumanos.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='auditorias_realizadas',
        verbose_name="Auditor"
    )
    tipo_auditoria = models.CharField(
        max_length=20, 
        choices=TIPO_AUDITORIA_CHOICES,
        verbose_name="Tipo de Auditoría"
    )
    estado_general = models.CharField(
        max_length=20, 
        choices=ESTADO_GENERAL_CHOICES,
        verbose_name="Estado General"
    )
    observaciones_generales = models.TextField(blank=True, verbose_name="Observaciones Generales")
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Auditoría de Herramientas Personales"
        verbose_name_plural = "Auditorías de Herramientas Personales"
        ordering = ['-fecha_auditoria', '-fecha_creacion']
    
    def __str__(self):
        return f"Auditoría {self.tipo_auditoria} - {self.tecnico.get_full_name()} - {self.fecha_auditoria}"
    
    @property
    def herramientas_auditadas(self):
        """Retorna el número de herramientas auditadas"""
        return self.detalles_auditoria.count()
    
    @property
    def herramientas_presentes(self):
        """Retorna el número de herramientas presentes"""
        return self.detalles_auditoria.filter(estado_herramienta='PRESENTE').count()
    
    @property
    def herramientas_ausentes(self):
        """Retorna el número de herramientas ausentes"""
        return self.detalles_auditoria.filter(estado_herramienta='AUSENTE').count()
    
    @property
    def acciones_pendientes(self):
        """Retorna el número de acciones pendientes"""
        return self.detalles_auditoria.filter(
            accion_requerida__in=['REPOSICION', 'REPARACION', 'LIMPIEZA']
        ).count()


class LogCambioItemHerramienta(models.Model):
    """Modelo para registrar cambios de estado de items durante auditorías"""
    item = models.ForeignKey(
        ItemHerramientaPersonal, 
        on_delete=models.CASCADE,
        related_name='logs_cambios',
        verbose_name="Item"
    )
    auditoria = models.ForeignKey(
        AuditoriaHerramientaPersonal, 
        on_delete=models.CASCADE,
        related_name='cambios_items',
        verbose_name="Auditoría"
    )
    estado_anterior = models.CharField(max_length=20, verbose_name="Estado Anterior")
    estado_nuevo = models.CharField(max_length=20, verbose_name="Estado Nuevo")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Cambio")
    
    class Meta:
        verbose_name = "Log de Cambio de Item"
        verbose_name_plural = "Logs de Cambios de Items"
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.item.nombre} - {self.estado_anterior} → {self.estado_nuevo}"


class DetalleAuditoriaHerramienta(models.Model):
    """Modelo para el detalle de auditorías de herramientas"""
    ESTADO_HERRAMIENTA_CHOICES = [
        ('PRESENTE', 'Presente'),
        ('AUSENTE', 'Ausente'),
        ('DAÑADA', 'Dañada'),
        ('DESGASTADA', 'Desgastada'),
        ('VENCIDA', 'Vencida'),
    ]
    
    ACCION_REQUERIDA_CHOICES = [
        ('NINGUNA', 'Ninguna'),
        ('REPOSICION', 'Reposición'),
        ('REPARACION', 'Reparación'),
        ('LIMPIEZA', 'Limpieza'),
        ('MANTENIMIENTO', 'Mantenimiento'),
    ]
    
    auditoria = models.ForeignKey(
        AuditoriaHerramientaPersonal, 
        on_delete=models.CASCADE,
        related_name='detalles_auditoria',
        verbose_name="Auditoría"
    )
    herramienta = models.ForeignKey(
        HerramientaPersonal, 
        on_delete=models.CASCADE,
        verbose_name="Herramienta"
    )
    estado_herramienta = models.CharField(
        max_length=20, 
        choices=ESTADO_HERRAMIENTA_CHOICES,
        verbose_name="Estado de la Herramienta"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    accion_requerida = models.CharField(
        max_length=20, 
        choices=ACCION_REQUERIDA_CHOICES,
        default='NINGUNA',
        verbose_name="Acción Requerida"
    )
    fecha_limite_accion = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha Límite de Acción"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Detalle de Auditoría de Herramienta"
        verbose_name_plural = "Detalles de Auditorías de Herramientas"
        ordering = ['auditoria', 'herramienta__categoria', 'herramienta__nombre']
        unique_together = ['auditoria', 'herramienta']
    
    def __str__(self):
        return f"{self.auditoria} - {self.herramienta.nombre}"
    
    @property
    def requiere_accion(self):
        """Verifica si requiere alguna acción"""
        return self.accion_requerida != 'NINGUNA'
    
    @property
    def accion_vencida(self):
        """Verifica si la acción requerida está vencida"""
        if self.fecha_limite_accion:
            from datetime import date
            return date.today() > self.fecha_limite_accion
        return False 
    
