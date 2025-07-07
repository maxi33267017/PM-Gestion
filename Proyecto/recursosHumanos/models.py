from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from datetime import datetime, date
from django.utils.timezone import timedelta
from django.db.models import Sum
from gestionDeTaller.models import Servicio

class Provincia(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    def __str__(self):
        return self.nombre
   
    class Meta:
        verbose_name = "Provincia"
        verbose_name_plural = "Provincias"

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, verbose_name="Provincia")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"


class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    direccion = models.CharField(max_length=200, verbose_name="Dirección")
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE, verbose_name="Ciudad")
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, verbose_name="Provincia")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.ciudad}"

    def get_direccion_completa(self):
        return f"{self.direccion}, {self.ciudad}, CP: {self.codigo_postal}"
    

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

class TarifaManoObra(models.Model):
    TIPO_TARIFA = [
        ('INDIVIDUAL', 'Técnico Individual'),
        ('MULTIPLE', 'Múltiples Técnicos'),
    ]
    
    TIPO_SERVICIO = [
        ('TALLER', 'Trabajo en Taller'),
        ('CAMPO', 'Trabajo en Campo'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_TARIFA)
    tipo_servicio = models.CharField(max_length=20, choices=TIPO_SERVICIO)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Hora")
    fecha_vigencia = models.DateField(verbose_name="Fecha de Vigencia")
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_vigencia']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.get_tipo_servicio_display()} - ${self.valor_hora} - Desde: {self.fecha_vigencia}"

    

class Usuario(AbstractUser):
    ROLES = [
        ('TECNICO', 'Técnico'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('GERENTE', 'Gerente'),
    ]

    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, verbose_name="Sucursal")
    rol = models.CharField(max_length=15, choices=ROLES, verbose_name="Rol")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    tarifa_individual = models.ForeignKey(
        TarifaManoObra, 
        on_delete=models.PROTECT, 
        limit_choices_to={'tipo': 'INDIVIDUAL'},
        null=True,
        blank=True,
        related_name='tecnicos'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido', 'sucursal', 'rol']

    objects = CustomUserManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f"{self.apellido}, {self.nombre} - {self.get_rol_display()}"

    def get_nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def get_username(self):
        return self.email

    def get_short_name(self):
        return self.nombre





class ActividadTrabajo(models.Model):
    DISPONIBILIDAD_CHOICES = [
        ('DISPONIBLE', 'Horas disponibles'),
        ('NO_DISPONIBLE', 'Horas no disponibles'),
    ]
    GENERACION_INGRESO_CHOICES = [
        ('INGRESO', 'Genera Ingreso'),
        ('NO_INGRESO', 'No genera Ingreso'),
    ]
    CATEGORIA_FACTURACION_CHOICES = [
        ('FACTURABLE', 'Facturable'),
        ('NO_FACTURABLE', 'No facturable, Ineficiente'),
    ]


    """Actividad específica que puede realizar el técnico"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    disponibilidad = models.CharField(max_length=15, choices=DISPONIBILIDAD_CHOICES, verbose_name="Disponibilidad")
    genera_ingreso = models.CharField(max_length=15, choices=GENERACION_INGRESO_CHOICES, verbose_name="Generación de Ingreso", null=True, blank=True)
    categoria_facturacion = models.CharField(max_length=15, choices=CATEGORIA_FACTURACION_CHOICES, verbose_name="Categoría de Facturación", null=True, blank=True)
   
    class Meta:
        verbose_name = "Actividad de Trabajo"
        verbose_name_plural = "Actividades de Trabajo"

       
    def __str__(self):
        return f"{self.nombre} ({self.disponibilidad} - {self.genera_ingreso})"




from django.db import models
from datetime import datetime
from django.db.models import Sum
from recursosHumanos.models import Usuario
from gestionDeTaller.models import Servicio

class RegistroHorasTecnico(models.Model):
    tecnico = models.ForeignKey(Usuario, on_delete=models.PROTECT, limit_choices_to={'rol': 'TECNICO'})
    fecha = models.DateField(verbose_name="Fecha")
    hora_inicio = models.TimeField(verbose_name="Hora Inicio")
    hora_fin = models.TimeField(verbose_name="Hora Fin")
    tipo_hora = models.ForeignKey(ActividadTrabajo, on_delete=models.PROTECT, verbose_name="Actividad")
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField(verbose_name="Descripción de la Actividad", blank=True)

    aprobado = models.BooleanField(default=False, verbose_name="¿Aprobado?")
    aprobado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='horas_aprobadas',
        limit_choices_to={'rol': 'GERENTE'},
        verbose_name="Aprobado por"
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Horas Técnico"
        verbose_name_plural = "Registros de Horas Técnicos"
        ordering = ['-fecha', '-hora_inicio']

    def __str__(self):
        return f"{self.tecnico} - {self.fecha} - {self.tipo_hora}"

    def save(self, *args, **kwargs):
        """
        Validaciones al guardar:
        1. La hora de inicio debe ser menor que la hora de fin.
        2. Si la actividad es DISPONIBLE y genera INGRESO, el servicio es obligatorio.
        3. Si la actividad no es DISPONIBLE o no genera INGRESO, el servicio debe ser NULL.
        4. Solo se pueden registrar horas en servicios en proceso.
        """
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("La hora de inicio debe ser menor que la hora de fin.")

        if self.tipo_hora.disponibilidad == 'DISPONIBLE' and self.tipo_hora.genera_ingreso == 'INGRESO':
            if not self.servicio:
                raise ValueError("Las horas productivas deben estar asociadas a un servicio.")
        else:
            if self.servicio:
                raise ValueError("Las horas no productivas no pueden estar asociadas a un servicio.")

        if self.servicio and self.servicio.estado not in ['EN_PROCESO']:
            raise ValueError("Solo se pueden registrar horas en servicios en proceso.")

        super().save(*args, **kwargs)



class Competencia(models.Model):
    NIVEL_CHOICES = [
        ('BASICO', 'Básico'),
        ('INTERMEDIO', 'Intermedio'),
        ('AVANZADO', 'Avanzado'),
        ('EXPERTO', 'Experto'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(verbose_name="Descripción")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Competencia"
        verbose_name_plural = "Competencias"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class CertificacionJD(models.Model):
    LEVEL_CHOICES = [
        ('LEVEL1', 'Level 1'),
        ('LEVEL2', 'Level 2'),
        ('LEVEL3', 'Level 3'),
    ]

    nombre = models.CharField(max_length=200, verbose_name="Nombre del Curso")
    codigo_curso = models.CharField(max_length=50, verbose_name="Código JD")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    descripcion = models.TextField(verbose_name="Descripción")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.get_level_display()}"

class CertificacionTecnico(models.Model):
    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'TECNICO'})
    certificacion = models.ForeignKey(CertificacionJD, on_delete=models.CASCADE)
    fecha_obtencion = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    certificado_url = models.URLField(blank=True)
    nota_final = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_obtencion']

    def __str__(self):
        return f"{self.tecnico} - {self.certificacion}"

class CompetenciaTecnico(models.Model):
    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'TECNICO'})
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=15, choices=Competencia.NIVEL_CHOICES)
    fecha_evaluacion = models.DateField(verbose_name="Fecha de Evaluación")
    evaluador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='evaluaciones_realizadas', limit_choices_to={'rol': 'GERENTE'})
    certificaciones = models.ManyToManyField(CertificacionTecnico, blank=True)
    nivel_jd = models.CharField(
        max_length=10, 
        choices=CertificacionJD.LEVEL_CHOICES,
        verbose_name="Nivel JD",
        blank=True
    )
    observaciones = models.TextField(blank=True)
    fecha_proxima_evaluacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Competencia de Técnico"
        verbose_name_plural = "Competencias de Técnicos"
        unique_together = ['tecnico', 'competencia']
        ordering = ['tecnico', 'competencia']

    def __str__(self):
        return f"{self.tecnico} - {self.competencia}: {self.get_nivel_display()}"




class EvaluacionSistema(models.Model):
    ESTADO_CHOICES = [
        ('OK', 'Correcto'),
        ('PENDIENTE', 'Pendiente'),
        ('NO_APLICA', 'No Aplica'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='evaluaciones_sistema')
    evaluador = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'GERENTE'}, related_name='sistemas_evaluados')
    fecha_evaluacion = models.DateField(verbose_name="Fecha de Evaluación")
    
    # Sistema Operativo
    windows_activado = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    windows_actualizado = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    antivirus_activo = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    
    # Software Corporativo
    jd_sistemas_actualizados = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    office_activado = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    
    # Hardware
    espacio_disco = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    memoria_ram = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    
    observaciones = models.TextField(blank=True)
    fecha_proxima_revision = models.DateField()
    
    class Meta:
        verbose_name = "Evaluación de Sistema"
        verbose_name_plural = "Evaluaciones de Sistemas"
        ordering = ['-fecha_evaluacion']

    def __str__(self):
        return f"Evaluación {self.usuario} - {self.fecha_evaluacion}"

    def get_items_pendientes(self):
        return sum(1 for field in [
            self.windows_activado,
            self.windows_actualizado,
            self.antivirus_activo,
            self.jd_sistemas_actualizados,
            self.office_activado,
            self.espacio_disco,
            self.memoria_ram
        ] if field == 'PENDIENTE')

    def save(self, *args, **kwargs):
        if not self.fecha_proxima_revision:
            # Automatically set next review date to 6 months from evaluation
            self.fecha_proxima_revision = self.fecha_evaluacion + timedelta(days=180)
        super().save(*args, **kwargs)

    @classmethod
    def get_evaluaciones_pendientes(cls):
        return cls.objects.filter(fecha_proxima_revision__lte=date.today())

    @property
    def dias_hasta_proxima_revision(self):
        return (self.fecha_proxima_revision - date.today()).days
    

class RevisionHerramientas(models.Model):
    ESTADO_CHOICES = [
        ('OK', 'Correcto'),
        ('REPARAR', 'Necesita Reparación'),
        ('REEMPLAZAR', 'Necesita Reemplazo'),
        ('NO_TIENE', 'No Posee'),
    ]

    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'TECNICO'}, related_name='revisiones_herramientas')
    revisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'ADMINISTRATIVO'}, related_name='herramientas_revisadas')
    fecha_revision = models.DateField(verbose_name="Fecha de Revisión")
    fecha_proxima_revision = models.DateField(verbose_name="Próxima Revisión")
    
    # Herramientas básicas
    caja_herramientas = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    llaves_impacto = models.CharField(max_length=10, choices=ESTADO_CHOICES, blank=True)
    multimetro = models.CharField(max_length=10, choices=ESTADO_CHOICES, blank=True)
    manometros = models.CharField(max_length=10, choices=ESTADO_CHOICES, blank=True)
    laptop = models.CharField(max_length=10, choices=ESTADO_CHOICES, blank=True)
    service_advisor = models.CharField(max_length=10, choices=ESTADO_CHOICES, blank=True)
    
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Revisión de Herramientas"
        verbose_name_plural = "Revisiones de Herramientas"
        ordering = ['-fecha_revision']

    def __str__(self):
        return f"Revisión Herramientas {self.tecnico} - {self.fecha_revision}"

    def save(self, *args, **kwargs):
        if not self.fecha_proxima_revision:
            self.fecha_proxima_revision = self.fecha_revision + timedelta(days=180)
        super().save(*args, **kwargs)

    @classmethod
    def get_revisiones_pendientes(cls):
        return cls.objects.filter(fecha_proxima_revision__lte=date.today())

    def get_items_para_reparar(self):
        return sum(1 for field in [
            self.caja_herramientas,
            self.llaves_impacto,
            self.multimetro,
            self.manometros,
            self.laptop,
            self.service_advisor
        ] if field == 'REPARAR')

    def get_items_para_reemplazar(self):
        return sum(1 for field in [
            self.caja_herramientas,
            self.llaves_impacto,
            self.multimetro,
            self.manometros,
            self.laptop,
            self.service_advisor
        ] if field == 'REEMPLAZAR')


class HerramientaEspecial(models.Model):
    UBICACION_CHOICES = [
        ('EST_JD01', 'Estante JD01'),
        ('EST_JD02', 'Estante JD02'),
        ('EST_JD03', 'Estante JD03'),
        ('EST_JD04', 'Estante JD04'),
        ('EST_JD05', 'Estante JD05'),
        ('EST_JD06', 'Estante JD06'),
    ]

    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(verbose_name="Descripción")
    foto = models.ImageField(upload_to='herramientas/', blank=True)
    ubicacion = models.CharField(max_length=10, choices=UBICACION_CHOICES)
    disponible = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Herramienta Especial"
        verbose_name_plural = "Herramientas Especiales"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} - {self.ubicacion}"


class PrestamoHerramienta(models.Model):
    herramienta = models.ForeignKey(HerramientaEspecial, on_delete=models.PROTECT)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    fecha_retiro = models.DateTimeField(auto_now_add=True)
    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    estado_salida = models.TextField(verbose_name="Estado al Retirar", blank=True)
    estado_devolucion = models.TextField(verbose_name="Estado al Devolver", blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Préstamo de Herramienta"
        verbose_name_plural = "Préstamos de Herramientas"
        ordering = ['-fecha_retiro']

    def __str__(self):
        return f"{self.herramienta} - {self.usuario} - {self.fecha_retiro}"

    @property
    def esta_prestada(self):
        return self.fecha_devolucion is None

    @classmethod
    def get_herramientas_prestadas(cls):
        return cls.objects.filter(fecha_devolucion__isnull=True)

    @classmethod
    def get_prestamos_usuario(cls, usuario):
        return cls.objects.filter(usuario=usuario)



