#!/usr/bin/env python3
"""
Script para exportar clientes y equipos desde la base de datos de Render
"""

import os
import sys
import django
from datetime import datetime
import pandas as pd

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

from clientes.models import Cliente, ContactoCliente, Equipo, TipoEquipo, ModeloEquipo, ModeloMotor
from recursosHumanos.models import Sucursal, Provincia, Ciudad

def exportar_clientes_equipos():
    """
    Exporta todos los clientes y equipos a un archivo Excel
    """
    
    print("🔄 Exportando clientes y equipos...")
    
    # Obtener todos los clientes con sus equipos
    clientes = Cliente.objects.select_related(
        'sucursal', 'ciudad', 'provincia'
    ).prefetch_related(
        'equipos__modelo__tipo_equipo',
        'equipos__modelo_motor',
        'contactos'
    ).filter(activo=True)
    
    datos_exportacion = []
    
    for cliente in clientes:
        print(f"📋 Procesando cliente: {cliente.razon_social}")
        
        # Obtener contacto principal
        contacto_principal = cliente.contactos.filter(es_contacto_principal=True).first()
        if not contacto_principal:
            contacto_principal = cliente.contactos.filter(activo=True).first()
        
        # Si no hay equipos, crear una fila solo con datos del cliente
        if not cliente.equipos.exists():
            datos_exportacion.append({
                # Información del Cliente
                'TIPO_CLIENTE': cliente.tipo,
                'SUCURSAL': cliente.sucursal.nombre if cliente.sucursal else '',
                'RAZON_SOCIAL': cliente.razon_social,
                'NOMBRE_FANTASIA': cliente.nombre_fantasia or '',
                'CUIT': cliente.cuit,
                'EMAIL': cliente.email,
                'TELEFONO': cliente.telefono,
                'DIRECCION': cliente.direccion,
                'CODIGO_POSTAL': cliente.codigo_postal,
                'CIUDAD': cliente.ciudad.nombre if cliente.ciudad else '',
                'PROVINCIA': cliente.provincia.nombre if cliente.provincia else '',
                'OBSERVACIONES_CLIENTE': cliente.observaciones or '',
                
                # Información de Contacto
                'NOMBRE_CONTACTO': contacto_principal.nombre if contacto_principal else '',
                'APELLIDO_CONTACTO': contacto_principal.apellido if contacto_principal else '',
                'ROL_CONTACTO': contacto_principal.rol if contacto_principal else '',
                'EMAIL_CONTACTO': contacto_principal.email if contacto_principal else '',
                'TELEFONO_FIJO_CONTACTO': contacto_principal.telefono_fijo if contacto_principal else '',
                'TELEFONO_CELULAR_CONTACTO': contacto_principal.telefono_celular if contacto_principal else '',
                'ES_CONTACTO_PRINCIPAL': 'TRUE' if contacto_principal and contacto_principal.es_contacto_principal else 'FALSE',
                
                # Información del Equipo (vacío)
                'TIPO_EQUIPO': '',
                'MODELO_EQUIPO': '',
                'MARCA_EQUIPO': '',
                'NUMERO_SERIE': '',
                'MODELO_MOTOR': '',
                'NUMERO_SERIE_MOTOR': '',
                'AÑO_FABRICACION': '',
                'FECHA_VENTA': '',
                'NOTAS_EQUIPO': '',
                'HOROMETRO_ACTUAL': '',
            })
        
        # Procesar cada equipo del cliente
        for equipo in cliente.equipos.filter(activo=True):
            datos_exportacion.append({
                # Información del Cliente
                'TIPO_CLIENTE': cliente.tipo,
                'SUCURSAL': cliente.sucursal.nombre if cliente.sucursal else '',
                'RAZON_SOCIAL': cliente.razon_social,
                'NOMBRE_FANTASIA': cliente.nombre_fantasia or '',
                'CUIT': cliente.cuit,
                'EMAIL': cliente.email,
                'TELEFONO': cliente.telefono,
                'DIRECCION': cliente.direccion,
                'CODIGO_POSTAL': cliente.codigo_postal,
                'CIUDAD': cliente.ciudad.nombre if cliente.ciudad else '',
                'PROVINCIA': cliente.provincia.nombre if cliente.provincia else '',
                'OBSERVACIONES_CLIENTE': cliente.observaciones or '',
                
                # Información de Contacto
                'NOMBRE_CONTACTO': contacto_principal.nombre if contacto_principal else '',
                'APELLIDO_CONTACTO': contacto_principal.apellido if contacto_principal else '',
                'ROL_CONTACTO': contacto_principal.rol if contacto_principal else '',
                'EMAIL_CONTACTO': contacto_principal.email if contacto_principal else '',
                'TELEFONO_FIJO_CONTACTO': contacto_principal.telefono_fijo if contacto_principal else '',
                'TELEFONO_CELULAR_CONTACTO': contacto_principal.telefono_celular if contacto_principal else '',
                'ES_CONTACTO_PRINCIPAL': 'TRUE' if contacto_principal and contacto_principal.es_contacto_principal else 'FALSE',
                
                # Información del Equipo
                'TIPO_EQUIPO': equipo.modelo.tipo_equipo.nombre if equipo.modelo and equipo.modelo.tipo_equipo else '',
                'MODELO_EQUIPO': equipo.modelo.nombre if equipo.modelo else '',
                'MARCA_EQUIPO': equipo.modelo.marca if equipo.modelo else '',
                'NUMERO_SERIE': equipo.numero_serie,
                'MODELO_MOTOR': equipo.modelo_motor.nombre if equipo.modelo_motor else '',
                'NUMERO_SERIE_MOTOR': equipo.numero_serie_motor or '',
                'AÑO_FABRICACION': str(equipo.año_fabricacion) if equipo.año_fabricacion else '',
                'FECHA_VENTA': equipo.fecha_venta.strftime('%Y-%m-%d') if equipo.fecha_venta else '',
                'NOTAS_EQUIPO': equipo.notas or '',
                'HOROMETRO_ACTUAL': str(equipo.ultima_hora_registrada) if equipo.ultima_hora_registrada else '',
            })
    
    # Crear DataFrame
    df = pd.DataFrame(datos_exportacion)
    
    # Crear archivo Excel
    nombre_archivo = f'exportacion_clientes_equipos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        # Hoja principal con datos
        df.to_excel(writer, sheet_name='DATOS_EXPORTADOS', index=False)
        
        # Hoja de resumen
        crear_hoja_resumen(writer.book, clientes)
        
        # Hoja de catálogos
        crear_hoja_catalogos(writer.book)
    
    print(f"✅ Exportación completada: {nombre_archivo}")
    print(f"📊 Total de registros exportados: {len(datos_exportacion)}")
    print(f"👥 Total de clientes: {clientes.count()}")
    print(f"🔧 Total de equipos: {Equipo.objects.filter(activo=True).count()}")
    
    return nombre_archivo

def crear_hoja_resumen(workbook, clientes):
    """Crea hoja con resumen de la exportación"""
    
    worksheet = workbook.create_sheet("RESUMEN")
    
    # Estadísticas generales
    total_clientes = clientes.count()
    total_equipos = Equipo.objects.filter(activo=True).count()
    total_contactos = ContactoCliente.objects.filter(activo=True).count()
    
    # Estadísticas por tipo de cliente
    clientes_empresa = clientes.filter(tipo='EMPRESA').count()
    clientes_particular = clientes.filter(tipo='PARTICULAR').count()
    clientes_publico = clientes.filter(tipo='ORGANISMO_PUBLICO').count()
    
    # Estadísticas por sucursal
    sucursales_stats = {}
    for cliente in clientes:
        sucursal = cliente.sucursal.nombre if cliente.sucursal else 'Sin sucursal'
        if sucursal not in sucursales_stats:
            sucursales_stats[sucursal] = 0
        sucursales_stats[sucursal] += 1
    
    resumen = [
        ["RESUMEN DE EXPORTACIÓN"],
        [""],
        ["ESTADÍSTICAS GENERALES:"],
        [f"• Total de clientes: {total_clientes}"],
        [f"• Total de equipos: {total_equipos}"],
        [f"• Total de contactos: {total_contactos}"],
        [""],
        ["CLIENTES POR TIPO:"],
        [f"• Empresas: {clientes_empresa}"],
        [f"• Particulares: {clientes_particular}"],
        [f"• Organismos públicos: {clientes_publico}"],
        [""],
        ["CLIENTES POR SUCURSAL:"],
    ]
    
    for sucursal, cantidad in sucursales_stats.items():
        resumen.append([f"• {sucursal}: {cantidad}"])
    
    resumen.extend([
        [""],
        ["INFORMACIÓN DE LA EXPORTACIÓN:"],
        [f"• Fecha de exportación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"],
        [f"• Archivo generado: exportacion_clientes_equipos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"],
        [""],
        ["NOTAS:"],
        ["• Solo se exportan clientes y equipos activos"],
        ["• Los contactos principales se marcan con TRUE"],
        ["• Los campos vacíos se dejan en blanco"],
        ["• Las fechas están en formato YYYY-MM-DD"],
    ])
    
    for i, linea in enumerate(resumen, 1):
        worksheet.cell(row=i, column=1, value=linea[0])
    
    # Ajustar ancho de columna
    worksheet.column_dimensions['A'].width = 60

def crear_hoja_catalogos(workbook):
    """Crea hoja con catálogos del sistema"""
    
    worksheet = workbook.create_sheet("CATÁLOGOS_SISTEMA")
    
    # Obtener catálogos del sistema
    sucursales = Sucursal.objects.all()
    provincias = Provincia.objects.all()
    ciudades = Ciudad.objects.all()
    tipos_equipo = TipoEquipo.objects.filter(activo=True)
    modelos_equipo = ModeloEquipo.objects.filter(activo=True)
    modelos_motor = ModeloMotor.objects.filter(activo=True)
    
    catalogos = [
        ["CATÁLOGOS DEL SISTEMA"],
        [""],
        ["SUCURSALES:"],
    ]
    
    for sucursal in sucursales:
        catalogos.append([f"• {sucursal.nombre}"])
    
    catalogos.extend([
        [""],
        ["PROVINCIAS:"],
    ])
    
    for provincia in provincias:
        catalogos.append([f"• {provincia.nombre}"])
    
    catalogos.extend([
        [""],
        ["CIUDADES:"],
    ])
    
    for ciudad in ciudades:
        catalogos.append([f"• {ciudad.nombre} ({ciudad.provincia.nombre})"])
    
    catalogos.extend([
        [""],
        ["TIPOS DE EQUIPO:"],
    ])
    
    for tipo in tipos_equipo:
        catalogos.append([f"• {tipo.nombre}"])
    
    catalogos.extend([
        [""],
        ["MODELOS DE EQUIPO:"],
    ])
    
    for modelo in modelos_equipo:
        catalogos.append([f"• {modelo.nombre} ({modelo.marca}) - Tipo: {modelo.tipo_equipo.nombre}"])
    
    catalogos.extend([
        [""],
        ["MODELOS DE MOTOR:"],
    ])
    
    for motor in modelos_motor:
        catalogos.append([f"• {motor.nombre}"])
    
    for i, catalogo in enumerate(catalogos, 1):
        worksheet.cell(row=i, column=1, value=catalogo[0])
    
    # Ajustar ancho de columna
    worksheet.column_dimensions['A'].width = 80

if __name__ == "__main__":
    try:
        archivo = exportar_clientes_equipos()
        print(f"\n🎉 ¡Exportación exitosa!")
        print(f"📁 Archivo: {archivo}")
        print(f"📍 Ubicación: {os.path.abspath(archivo)}")
    except Exception as e:
        print(f"❌ Error en la exportación: {str(e)}")
        sys.exit(1) 