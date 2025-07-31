#!/usr/bin/env python3
"""
Script para exportar datos directamente desde PostgreSQL
"""

import os
import sys
import psycopg2
import pandas as pd
from datetime import datetime

def exportar_desde_postgresql():
    """
    Exporta datos directamente desde PostgreSQL
    """
    
    # Configuración de la base de datos (desde variables de entorno)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL no está configurada")
        return None
    
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Conexión a PostgreSQL establecida")
        
        # Query para obtener clientes con equipos
        query = """
        SELECT 
            -- Información del Cliente
            c.tipo as TIPO_CLIENTE,
            s.nombre as SUCURSAL,
            c.razon_social as RAZON_SOCIAL,
            c.nombre_fantasia as NOMBRE_FANTASIA,
            c.cuit as CUIT,
            c.email as EMAIL,
            c.telefono as TELEFONO,
            c.direccion as DIRECCION,
            c.codigo_postal as CODIGO_POSTAL,
            ci.nombre as CIUDAD,
            p.nombre as PROVINCIA,
            c.observaciones as OBSERVACIONES_CLIENTE,
            
            -- Información de Contacto
            cc.nombre as NOMBRE_CONTACTO,
            cc.apellido as APELLIDO_CONTACTO,
            cc.rol as ROL_CONTACTO,
            cc.email as EMAIL_CONTACTO,
            cc.telefono_fijo as TELEFONO_FIJO_CONTACTO,
            cc.telefono_celular as TELEFONO_CELULAR_CONTACTO,
            CASE WHEN cc.es_contacto_principal THEN 'TRUE' ELSE 'FALSE' END as ES_CONTACTO_PRINCIPAL,
            
            -- Información del Equipo
            te.nombre as TIPO_EQUIPO,
            me.nombre as MODELO_EQUIPO,
            me.marca as MARCA_EQUIPO,
            e.numero_serie as NUMERO_SERIE,
            mm.nombre as MODELO_MOTOR,
            e.numero_serie_motor as NUMERO_SERIE_MOTOR,
            e.año_fabricacion as AÑO_FABRICACION,
            e.fecha_venta as FECHA_VENTA,
            e.notas as NOTAS_EQUIPO,
            e.ultima_hora_registrada as HOROMETRO_ACTUAL
            
        FROM clientes_cliente c
        LEFT JOIN recursosHumanos_sucursal s ON c.sucursal_id = s.id
        LEFT JOIN recursosHumanos_ciudad ci ON c.ciudad_id = ci.id
        LEFT JOIN recursosHumanos_provincia p ON c.provincia_id = p.id
        LEFT JOIN clientes_contactocliente cc ON c.id = cc.cliente_id AND cc.activo = true
        LEFT JOIN clientes_equipo e ON c.id = e.cliente_id AND e.activo = true
        LEFT JOIN clientes_modeloequipo me ON e.modelo_id = me.id
        LEFT JOIN clientes_tipoequipo te ON me.tipo_equipo_id = te.id
        LEFT JOIN clientes_modelomotor mm ON e.modelo_motor_id = mm.id
        WHERE c.activo = true
        ORDER BY c.razon_social, e.numero_serie
        """
        
        # Ejecutar query y obtener datos
        df = pd.read_sql_query(query, conn)
        
        # Crear archivo Excel
        nombre_archivo = f'exportacion_postgresql_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
            # Hoja principal
            df.to_excel(writer, sheet_name='DATOS_EXPORTADOS', index=False)
            
            # Hoja de estadísticas
            crear_estadisticas_postgresql(writer.book, conn)
        
        conn.close()
        
        print(f"✅ Exportación PostgreSQL completada: {nombre_archivo}")
        print(f"📊 Total de registros: {len(df)}")
        
        return nombre_archivo
        
    except Exception as e:
        print(f"❌ Error en la exportación PostgreSQL: {str(e)}")
        return None

def crear_estadisticas_postgresql(workbook, conn):
    """Crea hoja con estadísticas de PostgreSQL"""
    
    worksheet = workbook.create_sheet("ESTADÍSTICAS_POSTGRESQL")
    
    # Estadísticas generales
    stats_queries = [
        ("Total de clientes", "SELECT COUNT(*) FROM clientes_cliente WHERE activo = true"),
        ("Total de equipos", "SELECT COUNT(*) FROM clientes_equipo WHERE activo = true"),
        ("Total de contactos", "SELECT COUNT(*) FROM clientes_contactocliente WHERE activo = true"),
        ("Clientes por tipo", """
            SELECT tipo, COUNT(*) 
            FROM clientes_cliente 
            WHERE activo = true 
            GROUP BY tipo
        """),
        ("Equipos por tipo", """
            SELECT te.nombre, COUNT(*) 
            FROM clientes_equipo e
            JOIN clientes_modeloequipo me ON e.modelo_id = me.id
            JOIN clientes_tipoequipo te ON me.tipo_equipo_id = te.id
            WHERE e.activo = true
            GROUP BY te.nombre
        """),
    ]
    
    row = 1
    for titulo, query in stats_queries:
        worksheet.cell(row=row, column=1, value=titulo)
        row += 1
        
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            for result in results:
                worksheet.cell(row=row, column=1, value=str(result))
                row += 1
            
            cursor.close()
        except Exception as e:
            worksheet.cell(row=row, column=1, value=f"Error: {str(e)}")
            row += 1
        
        row += 1  # Espacio entre estadísticas
    
    # Ajustar ancho de columna
    worksheet.column_dimensions['A'].width = 60

if __name__ == "__main__":
    archivo = exportar_desde_postgresql()
    if archivo:
        print(f"\n🎉 ¡Exportación PostgreSQL exitosa!")
        print(f"📁 Archivo: {archivo}")
        print(f"📍 Ubicación: {os.path.abspath(archivo)}")
    else:
        print("❌ La exportación PostgreSQL falló")
        sys.exit(1) 