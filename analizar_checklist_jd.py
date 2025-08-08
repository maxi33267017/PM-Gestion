#!/usr/bin/env python3
"""
Script para analizar la lista de verificación de JD Protect
"""

import fitz
import re

def analizar_checklist_jd():
    """Analiza el PDF de la lista de verificación de JD Protect"""
    
    print("=== ANÁLISIS DE LISTA DE VERIFICACIÓN JD PROTECT ===\n")
    
    # Abrir el PDF
    doc = fitz.open('JD PROTECT LISTA VERIFICACION.pdf')
    
    # Extraer todo el texto
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text()
    
    doc.close()
    
    print("CONTENIDO DEL PDF:")
    print("=" * 50)
    print(texto_completo)
    print("=" * 50)
    
    # Analizar la estructura
    print("\n=== ANÁLISIS DE ESTRUCTURA ===")
    
    # Buscar secciones principales
    secciones = [
        "Cabina",
        "Transmission", 
        "Sistema Hidraulico",
        "Sistema Eletrico",
        "Sistema de Frenos",
        "Motor",
        "Chassis y Estructura",
        "Sistema de Aspiracion",
        "Sistema de Combustible",
        "Sistema DEF",
        "Sistema de Refrigeracion",
        "Lantas y Carrileria"
    ]
    
    print("\nSECCIONES PRINCIPALES IDENTIFICADAS:")
    for seccion in secciones:
        if seccion in texto_completo:
            print(f"✓ {seccion}")
    
    # Buscar campos de datos del cliente
    campos_cliente = [
        "Fecha",
        "Modelo da Maquina", 
        "PIN de la Maquina",
        "Nombre de lo Cliente",
        "Horometro"
    ]
    
    print("\nCAMPOS DE DATOS DEL CLIENTE:")
    for campo in campos_cliente:
        if campo in texto_completo:
            print(f"✓ {campo}")
    
    # Buscar opciones de respuesta
    opciones = ["A", "R", "N/A"]
    print(f"\nOPCIONES DE RESPUESTA: {opciones}")
    
    # Contar elementos de verificación
    elementos_verificacion = [
        "Cinturon de Seguridad", "Operacion de transmision", "Claxon",
        "Aceite de transmision", "Vidrios", "Filtros de transmision",
        "Limpiadores", "Barra cardan y crucetas", "Espejos",
        "Lubricacion de rodamientos", "Alarma de Reversa", "Mandos finales",
        "Operacion del HVAC", "Filtros de Aire de Cabina",
        "Operacion de Sistema Hidraulico (fugas)", "Monitor de Cabina",
        "Nivel de Aceite", "DTCs", "Filtros de Aceite",
        "Actualizacion de Software", "Mangueras y tubos hidraulicos",
        "Product Improvement Programs (PIPs)", "Cilindros hidraulicos",
        "Conexão JD Link, Expert Alerts", "Neutral Safety Start",
        "Frenos de Servicio", "Motor de marcha", "Frenos de Estacionamiento",
        "Luces y direccionales", "Frenos en operacion", "Alternador",
        "Baterias", "Operacion general", "Arneses electricos",
        "Aceite de Motor", "Filtro de Aceite", "Escalones",
        "Poleas y correas", "Pasa manos", "Candados de seguridad",
        "Turbocargador", "ROPS", "Tapas y cubiertas", "Calcomanias",
        "Contrapesos", "Nivel de Anticongelante", "Cooling Package",
        "Acesorios", "Lantas/Zapatas", "Rims/Rodillos y Rueda Guia",
        "Sprockets (Si aplica)", "Notas generales"
    ]
    
    print(f"\nELEMENTOS DE VERIFICACIÓN IDENTIFICADOS: {len(elementos_verificacion)}")
    for i, elemento in enumerate(elementos_verificacion, 1):
        print(f"{i:2d}. {elemento}")
    
    print("\n=== RESUMEN ===")
    print(f"• Total de secciones principales: {len(secciones)}")
    print(f"• Total de campos de cliente: {len(campos_cliente)}")
    print(f"• Total de elementos de verificación: {len(elementos_verificacion)}")
    print(f"• Opciones de respuesta: {', '.join(opciones)}")
    
    return {
        'secciones': secciones,
        'campos_cliente': campos_cliente,
        'elementos_verificacion': elementos_verificacion,
        'opciones': opciones,
        'texto_completo': texto_completo
    }

if __name__ == "__main__":
    resultado = analizar_checklist_jd() 