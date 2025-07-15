#!/usr/bin/env python
"""
Parser mejorado para el archivo de repuestos de John Deere
Formato: AR.DMS.DWNLD.V2
"""

import os
import sys
import re
from datetime import datetime
from decimal import Decimal

class ParserRepuestosJDV2:
    """Parser mejorado para archivos de repuestos de John Deere"""
    
    def __init__(self):
        # Analizar mejor la estructura basada en los resultados anteriores
        self.estructura_campos = {
            'codigo': (0, 15),           # Código del repuesto
            'descripcion': (15, 80),     # Descripción del repuesto
            'precio_lista': (80, 100),   # Precio de lista
            'precio_neto': (100, 120),   # Precio neto
            'dimensiones': (120, 140),   # Dimensiones
            'peso': (140, 150),          # Peso
            'fecha_actualizacion': (150, 158),  # Fecha de actualización
            'indicadores': (158, 180),   # Indicadores varios
            'moneda': (180, 183),        # Moneda
        }
    
    def parse_linea(self, linea):
        """Parsea una línea del archivo con análisis más detallado"""
        linea = linea.rstrip('\n\r')
        
        if len(linea) < 183:
            return None
        
        repuesto = {}
        
        # Extraer campos según la estructura definida
        for campo, (inicio, fin) in self.estructura_campos.items():
            valor = linea[inicio:fin].strip()
            repuesto[campo] = valor
        
        # Procesar campos específicos
        repuesto = self.procesar_campos(repuesto)
        
        return repuesto
    
    def procesar_campos(self, repuesto):
        """Procesa y limpia los campos extraídos"""
        
        # Limpiar descripción
        if 'descripcion' in repuesto:
            desc = repuesto['descripcion']
            # Remover "PARNAN" del inicio si existe
            if desc.startswith('PARNAN'):
                desc = desc[6:]
            # Remover números al final de la descripción
            desc = re.sub(r'\d+\.\d+.*$', '', desc)
            # Remover espacios múltiples
            desc = ' '.join(desc.split())
            repuesto['descripcion'] = desc
        
        # Procesar precios con mejor extracción
        if 'precio_lista' in repuesto:
            precio_lista = self.extraer_precio_mejorado(repuesto['precio_lista'])
            repuesto['precio_lista_decimal'] = precio_lista
        
        if 'precio_neto' in repuesto:
            precio_neto = self.extraer_precio_mejorado(repuesto['precio_neto'])
            repuesto['precio_neto_decimal'] = precio_neto
        
        # Procesar fecha con mejor detección
        if 'fecha_actualizacion' in repuesto:
            fecha = self.extraer_fecha(repuesto['fecha_actualizacion'])
            repuesto['fecha_actualizacion_parsed'] = fecha
        
        # Procesar dimensiones
        if 'dimensiones' in repuesto:
            dims = self.extraer_dimensiones_mejorado(repuesto['dimensiones'])
            repuesto['dimensiones_parsed'] = dims
        
        # Procesar peso
        if 'peso' in repuesto:
            peso = self.extraer_peso_mejorado(repuesto['peso'])
            repuesto['peso_decimal'] = peso
        
        # Procesar moneda
        if 'moneda' in repuesto:
            moneda = self.extraer_moneda(repuesto['moneda'])
            repuesto['moneda_parsed'] = moneda
        
        return repuesto
    
    def extraer_precio_mejorado(self, precio_str):
        """Extrae el precio con mejor lógica"""
        # Buscar patrones de precio más específicos
        # Patrón: números seguidos de punto y más números
        matches = re.findall(r'(\d+\.\d+)', precio_str)
        if matches:
            # Tomar el primer precio válido
            for match in matches:
                try:
                    precio = Decimal(match)
                    if 0 < precio < 100000:  # Rango razonable para precios
                        return precio
                except:
                    continue
        return None
    
    def extraer_fecha(self, fecha_str):
        """Extrae la fecha con mejor detección"""
        # Buscar patrones de fecha YYYYMMDD
        matches = re.findall(r'(\d{8})', fecha_str)
        for match in matches:
            try:
                # Verificar que sea una fecha válida
                fecha = datetime.strptime(match, '%Y%m%d')
                # Verificar que esté en un rango razonable (2000-2030)
                if 2000 <= fecha.year <= 2030:
                    return fecha
            except:
                continue
        return None
    
    def extraer_dimensiones_mejorado(self, dims_str):
        """Extrae las dimensiones con mejor lógica"""
        # Buscar números decimales en el string
        numeros = re.findall(r'(\d+\.\d+)', dims_str)
        if len(numeros) >= 3:
            try:
                return {
                    'largo': Decimal(numeros[0]),
                    'ancho': Decimal(numeros[1]),
                    'alto': Decimal(numeros[2])
                }
            except:
                pass
        return None
    
    def extraer_peso_mejorado(self, peso_str):
        """Extrae el peso con mejor lógica"""
        matches = re.findall(r'(\d+\.\d+)', peso_str)
        if matches:
            try:
                peso = Decimal(matches[0])
                if 0 < peso < 10000:  # Rango razonable para peso
                    return peso
            except:
                pass
        return None
    
    def extraer_moneda(self, moneda_str):
        """Extrae la moneda"""
        # Buscar códigos de moneda comunes
        monedas_validas = ['USD', 'ARS', 'EUR']
        for moneda in monedas_validas:
            if moneda in moneda_str:
                return moneda
        return None
    
    def parse_archivo(self, archivo_path, max_lineas=None):
        """Parsea todo el archivo"""
        repuestos = []
        errores = []
        
        print(f"🔍 Parsing archivo: {archivo_path}")
        
        with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, linea in enumerate(f, 1):
                if max_lineas and i > max_lineas:
                    break
                
                try:
                    repuesto = self.parse_linea(linea)
                    if repuesto and repuesto.get('codigo'):
                        repuestos.append(repuesto)
                except Exception as e:
                    errores.append({
                        'linea': i,
                        'error': str(e),
                        'contenido': linea[:100]
                    })
                
                # Mostrar progreso cada 10000 líneas
                if i % 10000 == 0:
                    print(f"  Procesadas {i:,} líneas...")
        
        print(f"✅ Parsing completado:")
        print(f"  Repuestos válidos: {len(repuestos):,}")
        print(f"  Errores: {len(errores)}")
        
        return repuestos, errores
    
    def generar_resumen(self, repuestos):
        """Genera un resumen de los repuestos parseados"""
        if not repuestos:
            return
        
        print(f"\n📊 Resumen de repuestos parseados:")
        print(f"  Total: {len(repuestos):,}")
        
        # Estadísticas de precios
        precios_lista = [r['precio_lista_decimal'] for r in repuestos if r.get('precio_lista_decimal')]
        precios_neto = [r['precio_neto_decimal'] for r in repuestos if r.get('precio_neto_decimal')]
        
        if precios_lista:
            print(f"  Precios de lista válidos: {len(precios_lista):,}")
            print(f"  Rango precios lista: ${min(precios_lista)} - ${max(precios_lista)}")
        
        if precios_neto:
            print(f"  Precios netos válidos: {len(precios_neto):,}")
            print(f"  Rango precios neto: ${min(precios_neto)} - ${max(precios_neto)}")
        
        # Fechas de actualización
        fechas = [r['fecha_actualizacion_parsed'] for r in repuestos if r.get('fecha_actualizacion_parsed')]
        if fechas:
            print(f"  Fechas válidas: {len(fechas):,}")
            print(f"  Rango fechas: {min(fechas).strftime('%Y-%m-%d')} - {max(fechas).strftime('%Y-%m-%d')}")
        
        # Monedas
        monedas = set(r['moneda_parsed'] for r in repuestos if r.get('moneda_parsed'))
        print(f"  Monedas encontradas: {monedas}")
        
        # Ejemplos de repuestos
        print(f"\n📝 Ejemplos de repuestos:")
        for i, repuesto in enumerate(repuestos[:5]):
            print(f"  {i+1}. {repuesto['codigo']} - {repuesto['descripcion']}")
            if repuesto.get('precio_lista_decimal'):
                print(f"     Precio lista: ${repuesto['precio_lista_decimal']}")
            if repuesto.get('precio_neto_decimal'):
                print(f"     Precio neto: ${repuesto['precio_neto_decimal']}")

def main():
    """Función principal para testing"""
    archivo = "AR.DMS.DWNLD.V2-2025-06-05"
    
    if not os.path.exists(archivo):
        print(f"❌ Error: El archivo {archivo} no existe")
        return
    
    parser = ParserRepuestosJDV2()
    
    # Parsear solo las primeras 100 líneas para testing
    repuestos, errores = parser.parse_archivo(archivo, max_lineas=100)
    
    # Generar resumen
    parser.generar_resumen(repuestos)
    
    # Mostrar algunos ejemplos detallados
    print(f"\n🔍 Ejemplos detallados:")
    for i, repuesto in enumerate(repuestos[:3]):
        print(f"\n--- Repuesto {i+1} ---")
        for key, value in repuesto.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main() 