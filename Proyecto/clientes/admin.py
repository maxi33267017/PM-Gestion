from django.contrib import admin
from .models import Equipo, ModeloEquipo, TipoEquipo, Usuario, Cliente, ContactoCliente, ModeloMotor, RegistroHorometro

@admin.register(ModeloEquipo)
class ModeloEquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca', 'tipo_equipo', 'activo']
    list_filter = ['marca', 'tipo_equipo', 'activo']
    search_fields = ['nombre', 'marca', 'descripcion']
    list_editable = ['activo']
    ordering = ['marca', 'nombre']
    
    fieldsets = (
        ('Información del Modelo', {
            'fields': ('tipo_equipo', 'nombre', 'marca', 'descripcion', 'activo')
        }),
    )

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'modelo', 'cliente']
    list_filter = ['modelo']
    search_fields = ['numero_serie', 'cliente__nombre']

@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    ordering = ['nombre']
    
    fieldsets = (
        ('Información del Tipo', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
    )


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['id', 'razon_social', 'email', 'telefono']
    list_filter = ['razon_social']
    search_fields = ['razon_social', 'email']

@admin.register(ContactoCliente)
class ContactoClienteAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'nombre', 'apellido', 'rol']
    list_filter = ['cliente']
    search_fields = ['cliente', 'rol']


@admin.register(ModeloMotor)
class ModeloMotorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    ordering = ['nombre']
    
    fieldsets = (
        ('Información del Motor', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
    )

@admin.register(RegistroHorometro)
class RegistroHorometroAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'horas', 'origen']
    list_filter = ['equipo', 'origen']
    search_fields = ['equipo',]