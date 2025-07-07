from django.contrib import admin
from .models import Campania, Contacto, AnalisisCliente

@admin.register(Campania)
class CampaniaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'fecha_inicio', 'fecha_fin', 'estado']
    list_filter = ['estado']
    search_fields = ['nombre']

@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'fecha_contacto', 'resultado']
    list_filter = ['resultado', 'fecha_contacto']
    search_fields = ['cliente__nombre']

@admin.register(AnalisisCliente)
class AnalisisClienteAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'categoria', 'ultima_actualizacion']
    list_filter = ['categoria']
    search_fields = ['cliente__nombre']