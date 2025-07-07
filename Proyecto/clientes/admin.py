from django.contrib import admin
from .models import Equipo, ModeloEquipo, TipoEquipo, Usuario, Cliente, ContactoCliente, ModeloMotor, RegistroHorometro

@admin.register(ModeloEquipo)
class ModeloEquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca']
    search_fields = ['nombre', 'marca']

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'modelo', 'cliente']
    list_filter = ['modelo']
    search_fields = ['numero_serie', 'cliente__nombre']

@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    list_filter = ['nombre']
    search_fields = ['nombre']


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
    list_display = ['nombre',]
    list_filter = ['nombre']
    search_fields = ['nombre',]

@admin.register(RegistroHorometro)
class RegistroHorometroAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'horas', 'origen']
    list_filter = ['equipo', 'origen']
    search_fields = ['equipo',]