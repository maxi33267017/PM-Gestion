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
    # Campo para múltiples sucursales (solo para gerentes)
    sucursales_adicionales = models.ManyToManyField(
        Sucursal, 
        blank=True, 
        verbose_name="Sucursales Adicionales",
        related_name='usuarios_adicionales',
        help_text="Sucursales adicionales para gerentes (opcional)"
    )
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

    def get_sucursales_disponibles(self):
        """
        Retorna todas las sucursales disponibles para el usuario.
        Para gerentes: sucursal principal + sucursales adicionales
        Para otros: solo la sucursal principal
        """
        if self.rol == 'GERENTE':
            sucursales = [self.sucursal]
            sucursales.extend(self.sucursales_adicionales.all())
            return list(set(sucursales))  # Eliminar duplicados
        else:
            return [self.sucursal]

    def puede_acceder_sucursal(self, sucursal):
        """
        Verifica si el usuario puede acceder a una sucursal específica
        """
        return sucursal in self.get_sucursales_disponibles()

    def get_sucursales_para_formulario(self):
        """
        Retorna las sucursales que deben aparecer en formularios
        """
        if self.rol == 'GERENTE':
            return Sucursal.objects.filter(activo=True)
        else:
            return Sucursal.objects.filter(id=self.sucursal.id, activo=True)





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
    requiere_servicio = models.BooleanField(
        default=False, 
        verbose_name="Requiere Asociación de Servicio",
        help_text="Si está marcado, esta actividad siempre requiere asociar un servicio"
    )
   
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
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("La hora de inicio debe ser menor que la hora de fin.")

        # Nueva lógica: verificar si la actividad requiere servicio
        if self.tipo_hora.requiere_servicio:
            if not self.servicio:
                raise ValueError("Esta actividad requiere asociar un servicio.")
        # Lógica para actividades que NO requieren servicio pero son productivas
        elif self.tipo_hora.disponibilidad == 'DISPONIBLE' and self.tipo_hora.genera_ingreso == 'INGRESO' and not self.tipo_hora.requiere_servicio:
            # Estas actividades pueden existir sin servicio (ej: viajes, capacitaciones, etc.)
            pass
        # Lógica para actividades no productivas
        elif self.tipo_hora.disponibilidad == 'NO_DISPONIBLE' or self.tipo_hora.genera_ingreso == 'NO_INGRESO':
            if self.servicio:
                raise ValueError("Las horas no productivas no pueden estar asociadas a un servicio.")

        # Validar que el servicio esté en un estado válido y no sea muy antiguo
        if self.servicio:
            from django.utils import timezone
            from datetime import timedelta
            
            fecha_limite = timezone.now().date() - timedelta(days=15)
            
            if self.servicio.estado not in ['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR', 'COMPLETADO']:
                raise ValueError("Solo se pueden registrar horas en servicios en proceso, programados, finalizados a facturar o completados recientemente.")
            elif self.servicio.estado == 'COMPLETADO' and self.servicio.fecha_servicio < fecha_limite:
                raise ValueError("No se pueden registrar horas en servicios completados con más de 15 días de antigüedad.")
        
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




class SesionCronometro(models.Model):
    """Modelo para manejar sesiones activas del cronómetro de técnicos"""
    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'TECNICO'})
    actividad = models.ForeignKey(ActividadTrabajo, on_delete=models.CASCADE, verbose_name="Actividad")
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Servicio")
    hora_inicio = models.DateTimeField(auto_now_add=True, verbose_name="Hora de Inicio")
    hora_fin = models.DateTimeField(null=True, blank=True, verbose_name="Hora de Fin")
    activa = models.BooleanField(default=True, verbose_name="¿Activa?")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")

    class Meta:
        verbose_name = "Sesión de Cronómetro"
        verbose_name_plural = "Sesiones de Cronómetro"
        ordering = ['-fecha_creacion']

    def __str__(self):
        estado = "Activa" if self.activa else "Finalizada"
        servicio_info = f" - {self.servicio}" if self.servicio else ""
        return f"{self.tecnico} - {self.actividad}{servicio_info} ({estado})"

    def get_duracion(self):
        """Calcula la duración de la sesión"""
        if self.hora_fin:
            return self.hora_fin - self.hora_inicio
        else:
            from django.utils import timezone
            return timezone.now() - self.hora_inicio

    def get_duracion_horas(self):
        """Retorna la duración en horas decimales"""
        duracion = self.get_duracion()
        return duracion.total_seconds() / 3600

    def finalizar_sesion(self, hora_fin=None):
        """Finaliza la sesión y crea el registro de horas"""
        from django.utils import timezone
        from datetime import datetime
        
        if not self.activa:
            return False, "La sesión ya está finalizada"
        
        # Establecer hora de fin
        if hora_fin is None:
            hora_fin = timezone.now()
        
        self.hora_fin = hora_fin
        self.activa = False
        self.save()
        
        # Crear registro de horas
        try:
            registro = RegistroHorasTecnico.objects.create(
                tecnico=self.tecnico,
                fecha=self.hora_inicio.date(),
                hora_inicio=self.hora_inicio.time(),
                hora_fin=self.hora_fin.time(),
                tipo_hora=self.actividad,
                servicio=self.servicio,
                descripcion=self.descripcion
            )
            return True, f"Sesión finalizada y registro creado: {registro}"
        except Exception as e:
            # Si hay error al crear el registro, reactivar la sesión
            self.hora_fin = None
            self.activa = True
            self.save()
            return False, f"Error al crear registro: {str(e)}"

    @classmethod
    def get_sesion_activa_tecnico(cls, tecnico):
        """Obtiene la sesión activa de un técnico"""
        return cls.objects.filter(tecnico=tecnico, activa=True).first()

    @classmethod
    def finalizar_sesiones_automaticas(cls):
        """Finaliza automáticamente las sesiones activas a las 19:00"""
        from django.utils import timezone
        from datetime import datetime, time
        
        ahora = timezone.now()
        hora_limite = time(19, 0)  # 19:00 hora local Argentina
        
        # Si es después de las 19:00, finalizar sesiones activas
        if ahora.time() >= hora_limite:
            sesiones_activas = cls.objects.filter(activa=True)
            for sesion in sesiones_activas:
                # Establecer hora de fin a las 19:00 del día actual
                hora_fin = datetime.combine(ahora.date(), hora_limite)
                hora_fin = timezone.make_aware(hora_fin)
                sesion.finalizar_sesion(hora_fin)




class AlertaCronometro(models.Model):
    """Modelo para rastrear alertas enviadas por cronómetros activos"""
    TIPO_ALERTA_CHOICES = [
        ('CRONOMETRO_ACTIVO', 'Cronómetro Activo'),
        ('CRONOMETRO_OLVIDADO', 'Cronómetro Olvidado'),
        ('FINALIZACION_AUTOMATICA', 'Finalización Automática'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADA', 'Enviada'),
        ('FALLIDA', 'Fallida'),
    ]
    
    sesion = models.ForeignKey(SesionCronometro, on_delete=models.CASCADE, verbose_name="Sesión de Cronómetro")
    tipo_alerta = models.CharField(max_length=25, choices=TIPO_ALERTA_CHOICES, verbose_name="Tipo de Alerta")
    destinatarios = models.JSONField(verbose_name="Destinatarios", help_text="Lista de emails a los que se envió la alerta")
    asunto = models.CharField(max_length=200, verbose_name="Asunto del Email")
    mensaje = models.TextField(verbose_name="Mensaje Enviado")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Envío")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    class Meta:
        verbose_name = "Alerta de Cronómetro"
        verbose_name_plural = "Alertas de Cronómetros"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Alerta {self.get_tipo_alerta_display()} - {self.sesion.tecnico} ({self.get_estado_display()})"
    
    @classmethod
    def crear_alerta_cronometro_activo(cls, sesion):
        """Crea una alerta para cronómetro activo"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Verificar si ya se envió una alerta reciente (últimas 2 horas)
        alerta_reciente = cls.objects.filter(
            sesion=sesion,
            tipo_alerta='CRONOMETRO_ACTIVO',
            estado='ENVIADA',
            fecha_envio__gte=timezone.now() - timedelta(hours=2)
        ).first()
        
        if alerta_reciente:
            return None  # No enviar alerta si ya se envió una recientemente
        
        # Obtener destinatarios
        destinatarios = cls._obtener_destinatarios_alerta(sesion)
        
        # Crear mensaje
        duracion = sesion.get_duracion()
        horas = int(duracion.total_seconds() // 3600)
        minutos = int((duracion.total_seconds() % 3600) // 60)
        
        asunto = f"⏰ Cronómetro Activo - {sesion.tecnico.get_nombre_completo()}"
        mensaje = f"""
        <h2>⏰ Cronómetro Activo</h2>
        <p><strong>Técnico:</strong> {sesion.tecnico.get_nombre_completo()}</p>
        <p><strong>Actividad:</strong> {sesion.actividad.nombre}</p>
        <p><strong>Duración actual:</strong> {horas}h {minutos}m</p>
        <p><strong>Inicio:</strong> {sesion.hora_inicio.strftime('%d/%m/%Y %H:%M')}</p>
        """
        
        if sesion.servicio:
            mensaje += f"<p><strong>Servicio:</strong> {sesion.servicio}</p>"
        
        if sesion.descripcion:
            mensaje += f"<p><strong>Descripción:</strong> {sesion.descripcion}</p>"
        
        mensaje += f"""
        <p><strong>Sucursal:</strong> {sesion.tecnico.sucursal.nombre}</p>
        <p><em>Este cronómetro se detendrá automáticamente a las 19:00 si no se detiene manualmente.</em></p>
        """
        
        return cls.objects.create(
            sesion=sesion,
            tipo_alerta='CRONOMETRO_ACTIVO',
            destinatarios=destinatarios,
            asunto=asunto,
            mensaje=mensaje
        )
    
    @classmethod
    def crear_alerta_cronometro_olvidado(cls, sesion):
        """Crea una alerta para cronómetro olvidado (más de 4 horas activo)"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Verificar si ya se envió una alerta reciente (últimas 2 horas)
        alerta_reciente = cls.objects.filter(
            sesion=sesion,
            tipo_alerta='CRONOMETRO_OLVIDADO',
            estado='ENVIADA',
            fecha_envio__gte=timezone.now() - timedelta(hours=2)
        ).first()
        
        if alerta_reciente:
            return None
        
        # Obtener destinatarios
        destinatarios = cls._obtener_destinatarios_alerta(sesion)
        
        # Crear mensaje
        duracion = sesion.get_duracion()
        horas = int(duracion.total_seconds() // 3600)
        minutos = int((duracion.total_seconds() % 3600) // 60)
        
        asunto = f"⚠️ Cronómetro Olvidado - {sesion.tecnico.get_nombre_completo()}"
        mensaje = f"""
        <h2>⚠️ Cronómetro Olvidado</h2>
        <p><strong>ATENCIÓN:</strong> El técnico {sesion.tecnico.get_nombre_completo()} tiene un cronómetro activo por más de 4 horas.</p>
        <p><strong>Actividad:</strong> {sesion.actividad.nombre}</p>
        <p><strong>Duración actual:</strong> {horas}h {minutos}m</p>
        <p><strong>Inicio:</strong> {sesion.hora_inicio.strftime('%d/%m/%Y %H:%M')}</p>
        """
        
        if sesion.servicio:
            mensaje += f"<p><strong>Servicio:</strong> {sesion.servicio}</p>"
        
        mensaje += f"""
        <p><strong>Sucursal:</strong> {sesion.tecnico.sucursal.nombre}</p>
        <p><em>Por favor, verificar si el técnico olvidó detener el cronómetro.</em></p>
        """
        
        return cls.objects.create(
            sesion=sesion,
            tipo_alerta='CRONOMETRO_OLVIDADO',
            destinatarios=destinatarios,
            asunto=asunto,
            mensaje=mensaje
        )
    
    @classmethod
    def _obtener_destinatarios_alerta(cls, sesion):
        """Obtiene la lista de destinatarios para las alertas"""
        from django.conf import settings
        
        destinatarios = []
        
        # 1. Email del técnico
        if sesion.tecnico.email:
            destinatarios.append(sesion.tecnico.email)
        
        # 2. Emails específicos de la empresa (siempre incluidos)
        emails_empresa = [
            'maxi.caamano@patagoniamaquinarias.com',
            'repuestosrga@patagoniamaquinarias.com'
        ]
        
        for email in emails_empresa:
            if email not in destinatarios:
                destinatarios.append(email)
        
        # 3. Emails adicionales de configuración (si existen)
        if hasattr(settings, 'CC_EMAILS'):
            for email in settings.CC_EMAILS:
                if email not in destinatarios:
                    destinatarios.append(email)
        
        # 4. Filtrar emails excluidos
        emails_excluidos = [
            'carolina.fiocchi@patagoniamaquinarias.com',
            'santiago.fiocchi@patagoniamaquinarias.com',
            'hector.gonzalez@patagoniamaquinarias.com',
            'administracion@patagoniamaquinarias.com'
        ]
        
        # Remover emails excluidos
        destinatarios = [email for email in destinatarios if email not in emails_excluidos]
        
        return destinatarios
    
    def enviar_email(self):
        """Envía el email de alerta"""
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.utils.html import strip_tags
        
        try:
            email = EmailMultiAlternatives(
                self.asunto,
                strip_tags(self.mensaje),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.destinatarios
            )
            email.attach_alternative(self.mensaje, "text/html")
            email.send()
            
            self.estado = 'ENVIADA'
            self.save()
            
            return True, "Email enviado correctamente"
            
        except Exception as e:
            self.estado = 'FALLIDA'
            self.save()
            return False, f"Error al enviar email: {str(e)}"




class PermisoAusencia(models.Model):
    """
    Modelo para gestionar permisos y ausencias del personal
    """
    TIPO_PERMISO_CHOICES = [
        ('VACACIONES', 'Vacaciones'),
        ('ENFERMEDAD', 'Enfermedad'),
        ('PERSONAL', 'Personal'),
        ('MATERNIDAD', 'Maternidad'),
        ('PATERNIDAD', 'Paternidad'),
        ('CAPACITACION', 'Capacitación'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Información básica
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='permisos_ausencia')
    tipo_permiso = models.CharField(max_length=20, choices=TIPO_PERMISO_CHOICES, verbose_name="Tipo de Permiso")
    motivo = models.TextField(verbose_name="Motivo del Permiso")
    
    # Fechas
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    
    # Estado y aprobación
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    aprobado_por = models.ForeignKey(
        'Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='permisos_aprobados',
        verbose_name="Aprobado por"
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Aprobación")
    observaciones_aprobacion = models.TextField(blank=True, verbose_name="Observaciones de Aprobación")
    
    # Documentación
    justificativo = models.FileField(
        upload_to='permisos/justificativos/', 
        blank=True, 
        null=True, 
        verbose_name="Justificativo"
    )
    descripcion_justificativo = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Descripción del Justificativo"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Permiso de Ausencia"
        verbose_name_plural = "Permisos de Ausencia"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['usuario', 'estado']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
            models.Index(fields=['estado', 'fecha_solicitud']),
        ]
    
    def __str__(self):
        return f"{self.usuario.get_nombre_completo()} - {self.get_tipo_permiso_display()} ({self.fecha_inicio} a {self.fecha_fin})"
    
    def save(self, *args, **kwargs):
        # Si el estado cambia a APROBADO, establecer fecha_aprobacion
        if self.estado == 'APROBADO' and not self.fecha_aprobacion:
            from django.utils import timezone
            self.fecha_aprobacion = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def dias_solicitados(self):
        """Calcula los días solicitados (excluyendo fines de semana)"""
        from datetime import timedelta
        dias = 0
        fecha_actual = self.fecha_inicio
        while fecha_actual <= self.fecha_fin:
            if fecha_actual.weekday() < 5:  # 0-4 = Lunes a Viernes
                dias += 1
            fecha_actual += timedelta(days=1)
        return dias
    
    @property
    def esta_activo(self):
        """Verifica si el permiso está activo (fechas actuales)"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return self.fecha_inicio <= hoy <= self.fecha_fin and self.estado == 'APROBADO'
    
    @property
    def esta_vencido(self):
        """Verifica si el permiso ya pasó"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return self.fecha_fin < hoy
    
    @property
    def puede_ser_aprobado(self):
        """Verifica si el permiso puede ser aprobado"""
        return self.estado == 'PENDIENTE'
    
    @property
    def puede_ser_rechazado(self):
        """Verifica si el permiso puede ser rechazado"""
        return self.estado in ['PENDIENTE', 'APROBADO']
    
    def aprobar(self, aprobado_por, observaciones=""):
        """Aprueba el permiso"""
        from django.utils import timezone
        self.estado = 'APROBADO'
        self.aprobado_por = aprobado_por
        self.fecha_aprobacion = timezone.now()
        self.observaciones_aprobacion = observaciones
        self.save()
    
    def rechazar(self, rechazado_por, observaciones=""):
        """Rechaza el permiso"""
        from django.utils import timezone
        self.estado = 'RECHAZADO'
        self.aprobado_por = rechazado_por
        self.fecha_aprobacion = timezone.now()
        self.observaciones_aprobacion = observaciones
        self.save()
    
    def cancelar(self, cancelado_por, observaciones=""):
        """Cancela el permiso"""
        from django.utils import timezone
        self.estado = 'CANCELADO'
        self.aprobado_por = cancelado_por
        self.fecha_aprobacion = timezone.now()
        self.observaciones_aprobacion = observaciones
        self.save()



