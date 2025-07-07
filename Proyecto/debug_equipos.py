#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario

print("=== VERIFICACIÓN DE CLIENTES Y EQUIPOS ===")
print()

# Verificar clientes con equipos activos
clientes_con_equipos = Cliente.objects.filter(equipos__activo=True).distinct()
print(f"Total de clientes con equipos activos: {clientes_con_equipos.count()}")

if clientes_con_equipos.exists():
    print("\nPrimeros 5 clientes con equipos:")
    for cliente in clientes_con_equipos[:5]:
        equipos_activos = cliente.equipos.filter(activo=True)
        print(f"- {cliente.razon_social} (ID: {cliente.id}) - Equipos activos: {equipos_activos.count()}")
        
        # Mostrar detalles de los equipos
        for equipo in equipos_activos[:3]:
            print(f"  * {equipo.numero_serie} - {equipo.modelo}")
else:
    print("No hay clientes con equipos activos")

print("\n=== VERIFICACIÓN DE LA VISTA ===")
print()

# Probar la vista directamente
from gestionDeTaller.views import equipos_por_cliente
from django.test import RequestFactory

# Crear un request falso
factory = RequestFactory()
request = factory.get('/equipos-por-cliente/1/')

# Crear un usuario falso
user = Usuario.objects.first()
if user:
    request.user = user
    
    # Probar con el primer cliente que tenga equipos
    if clientes_con_equipos.exists():
        cliente_test = clientes_con_equipos.first()
        print(f"Probando con cliente ID: {cliente_test.id}")
        
        try:
            response = equipos_por_cliente(request, cliente_test.id)
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.content.decode()}")
        except Exception as e:
            print(f"Error en la vista: {e}")
    else:
        print("No hay clientes para probar")
else:
    print("No hay usuarios en la base de datos") 