from django.db import models
from recursosHumanos.models import Sucursal, Provincia, Ciudad, Usuario
from django.utils import timezone

class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()
    
    class Meta:
        abstract = True

# Create your models here.
class Cliente(models.Model):
    TIPO_CLIENTE = [
        ('EMPRESA', 'Empresa'),
        ('PARTICULAR', 'Particular'),
        ('ORGANISMO_PUBLICO', 'Organismo Público'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CLIENTE, default='EMPRESA', verbose_name="Tipo de Cliente")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, verbose_name="Sucursal")
    razon_social = models.CharField(max_length=100, verbose_name="Razón Social")
    nombre_fantasia = models.CharField(max_length=100, verbose_name="Nombre Fantasía", blank=True)
    cuit = models.CharField(max_length=13, verbose_name="CUIT", unique=True)
    email = models.EmailField(verbose_name="Email")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.CharField(max_length=200, verbose_name="Dirección")
    codigo_postal = models.CharField(max_length=10, verbose_name="Código Postal")
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE, verbose_name="Ciudad")
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, verbose_name="Provincia")
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['razon_social']

    def __str__(self):
        return f"{self.razon_social} - {self.cuit}"

    def get_direccion_completa(self):
        return f"{self.direccion}, {self.ciudad}, {self.provincia}, CP: {self.codigo_postal}"

class ContactoCliente(models.Model):
    ROLES_CONTACTO = [
        ('GERENTE', 'Gerente'),
        ('JEFE_TALLER', 'Jefe de Taller'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('COMPRAS', 'Encargado de Compras'),
        ('OTRO', 'Otro'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contactos')
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    rol = models.CharField(max_length=20, choices=ROLES_CONTACTO, verbose_name="Rol")
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    telefono_fijo = models.CharField(max_length=20, verbose_name="Teléfono Fijo", blank=True, null=True)
    telefono_celular = models.CharField(max_length=20, verbose_name="Teléfono Celular", blank=True, null=True)
    es_contacto_principal = models.BooleanField(default=False, verbose_name="Contacto Principal")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")

    class Meta:
        verbose_name = "Contacto de Cliente"
        verbose_name_plural = "Contactos de Clientes"
        ordering = ['cliente', 'apellido', 'nombre']

    def __str__(self):
        return f"{self.apellido}, {self.nombre} - {self.get_rol_display()} ({self.cliente.razon_social})"

    def get_nombre_completo(self):
        return f"{self.nombre} {self.apellido}"



class TipoEquipo(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre", unique=True)  # Retroexcavadora, Motoniveladora, Grupo Electrógeno
    descripcion = models.TextField(verbose_name="Descripción", blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de Equipo"
        verbose_name_plural = "Tipos de Equipos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class ModeloEquipo(models.Model):
    tipo_equipo = models.ForeignKey(TipoEquipo, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, unique=True)  # 310SL, 670G, PP100
    marca = models.CharField(max_length=100)  # John Deere, PowerPro
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Modelo de Equipo"
        verbose_name_plural = "Modelos de Equipos"
        ordering = ['tipo_equipo', 'nombre']

    def __str__(self):
        return f"{self.tipo_equipo.nombre} - {self.marca} {self.nombre}"

class ModeloMotor(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Modelo de Motor", unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Modelo de Motor"
        verbose_name_plural = "Modelos de Motores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    # ESTADO_CHOICES = [
    #     ('ACTIVO', 'Activo'),
    #     ('BAJA', 'Baja'),
    # ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='equipos')
    modelo = models.ForeignKey(ModeloEquipo, on_delete=models.PROTECT)
    numero_serie = models.CharField(max_length=50, unique=True, verbose_name="Número de Serie/PIN")
    modelo_motor = models.ForeignKey(ModeloMotor, on_delete=models.PROTECT, null=True, blank=True)
    numero_serie_motor = models.CharField(max_length=50, verbose_name="Número de Serie Motor", null=True, blank=True)
    año_fabricacion = models.PositiveIntegerField(verbose_name="Año de Fabricación", null=True, blank=True)
    fecha_venta = models.DateField(verbose_name="Fecha de Venta", null=True, blank=True)
    # estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ACTIVO')
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    ultima_hora_registrada = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Última Hora Registrada", 
        blank=True, 
        null=True
    )

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
        ordering = ['cliente', 'modelo']
    
    class Meta:
        indexes = [
            models.Index(fields=['cliente', 'modelo']),
            models.Index(fields=['numero_serie']),
        ]

    def __str__(self):
        return f"{self.modelo} - Serie: {self.numero_serie} ({self.cliente.razon_social})"

    def get_horas_para_servicio(self):
        if self.proximo_servicio:
            return self.proximo_servicio - self.horometro
        return None



class RegistroHorometro(models.Model):
    ORIGEN_CHOICES = [
        ('MANUAL', 'Registro Manual'),
        ('PRE_ORDER', 'Pre Order'),
        ('SERVICIO', 'Servicio'),
        ('API_JD_LINK', 'JD Link API'),
        ('API_POWER_SIGHT', 'Power Sight API'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='registros_horometro')
    horas = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Horas")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    api_response_id = models.CharField(max_length=100, blank=True, null=True)
    datos_api = models.JSONField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_registro']


