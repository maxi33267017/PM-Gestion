from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Provincia, Ciudad, Sucursal, TarifaManoObra, RegistroHorasTecnico, Competencia, CompetenciaTecnico, CertificacionJD, CertificacionTecnico, EvaluacionSistema, RevisionHerramientas, HerramientaEspecial, PrestamoHerramienta


@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'nombre', 'apellido', 'sucursal', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellido', 'sucursal', 'rol')}),
        ('Permisos', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'nombre', 'apellido', 'sucursal', 'rol', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'nombre', 'apellido')
    ordering = ('email',)


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    model = Provincia
    list_display = ('nombre',)

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    model = Ciudad
    list_display = ('nombre',)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    model = Sucursal
    list_display = ('nombre', 'direccion', 'ciudad', 'provincia')

@admin.register(TarifaManoObra)
class TarifaManoObraAdmin(admin.ModelAdmin):
    model = TarifaManoObra
    list_display = ('tipo', 'tipo_servicio', 'valor_hora', 'fecha_vigencia')



@admin.register(RegistroHorasTecnico)
class RegistroHorasTecnicoAdmin(admin.ModelAdmin):
    model = RegistroHorasTecnico
    list_display = ('tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'tipo_hora', 'servicio', 'descripcion', 'aprobado')

@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    model = Competencia
    list_display = ('nombre',)

@admin.register(CertificacionJD)
class CertificacionJDAdmin(admin.ModelAdmin):
    model = CertificacionJD
    list_display = ('nombre', 'codigo_curso', 'level')

@admin.register(CertificacionTecnico)
class CertificacionTecnicoAdmin(admin.ModelAdmin):
    model = CertificacionTecnico
    list_display = ('tecnico', 'certificacion')

@admin.register(CompetenciaTecnico)
class CompetenciaTecnicoAdmin(admin.ModelAdmin):
    model = CompetenciaTecnico
    list_display = ('tecnico', 'competencia', 'nivel', 'fecha_evaluacion', 'evaluador')


@admin.register(EvaluacionSistema)
class EvaluacionSistemaAdmin(admin.ModelAdmin):
    model = EvaluacionSistema
    list_display = ('usuario', 'fecha_evaluacion')

@admin.register(RevisionHerramientas)
class RevisionHerramientasAdmin(admin.ModelAdmin):
    model = RevisionHerramientas
    list_display = ('tecnico', 'fecha_revision')

@admin.register(HerramientaEspecial)
class HerramientaEspecialAdmin(admin.ModelAdmin):
    model = HerramientaEspecial
    list_display = ('codigo', 'nombre', 'ubicacion', 'disponible')

@admin.register(PrestamoHerramienta)
class PrestamoHerramientaAdmin(admin.ModelAdmin):
    model = PrestamoHerramienta
    list_display = ('herramienta', 'usuario')

from django.contrib import admin
from recursosHumanos.models import ActividadTrabajo

@admin.register(ActividadTrabajo)
class ActividadTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)  # Muestra el nombre y el tipo de hora
    search_fields = ('nombre',)  # Permite buscar por nombre o categoría



