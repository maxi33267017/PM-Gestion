#!/usr/bin/env python3
"""
Script para actualizar todos los templates de horas para usar el filtro personalizado hours_format
"""

import os
import re

def update_template_file(file_path):
    """Actualiza un template para usar el filtro hours_format"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Agregar la carga del filtro personalizado si no está presente
    if '{% load reportes_filters %}' not in content:
        content = content.replace('{% load static %}', '{% load static %}\n{% load reportes_filters %}')
    
    # Reemplazar floatformat:1 con hours_format para campos de horas
    hour_fields = [
        'total_horas',
        'horas_disponibles', 
        'horas_no_disponibles',
        'horas_generan_ingreso',
        'horas_aprobadas',
        'horas_pendientes',
        'promedio_por_dia',
        'promedio_por_tecnico',
        'promedio_productivo_por_dia',
        'promedio_por_sucursal'
    ]
    
    for field in hour_fields:
        pattern = f'{{{{[^}}]*{field}[^}}]*\\|floatformat:1[^}}]*}}}}'
        replacement = f'{{{{ \\1|hours_format }}}}'
        content = re.sub(pattern, replacement, content)
    
    # Reemplazos específicos
    replacements = [
        ('{{ item.total_horas|floatformat:1 }}h', '{{ item.total_horas|hours_format }}h'),
        ('{{ item.horas_disponibles|floatformat:1 }}h', '{{ item.horas_disponibles|hours_format }}h'),
        ('{{ item.horas_no_disponibles|floatformat:1 }}h', '{{ item.horas_no_disponibles|hours_format }}h'),
        ('{{ item.horas_generan_ingreso|floatformat:1 }}h', '{{ item.horas_generan_ingreso|hours_format }}h'),
        ('{{ item.horas_aprobadas|floatformat:1 }}h', '{{ item.horas_aprobadas|hours_format }}h'),
        ('{{ item.horas_pendientes|floatformat:1 }}h', '{{ item.horas_pendientes|hours_format }}h'),
        ('{{ item.promedio_por_dia|floatformat:1 }}h', '{{ item.promedio_por_dia|hours_format }}h'),
        ('{{ item.promedio_productivo_por_dia|floatformat:1 }}h', '{{ item.promedio_productivo_por_dia|hours_format }}h'),
        ('{{ total_general_horas|floatformat:1 }}h', '{{ total_general_horas|hours_format }}h'),
        ('{{ promedio_horas_tecnico|floatformat:1 }}h', '{{ promedio_horas_tecnico|hours_format }}h'),
        ('{{ horas_no_disponibles|floatformat:1 }}h', '{{ horas_no_disponibles|hours_format }}h'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Actualizado: {file_path}")

def main():
    """Función principal"""
    templates_dir = "templates/reportes/horas"
    
    if not os.path.exists(templates_dir):
        print(f"Directorio no encontrado: {templates_dir}")
        return
    
    template_files = [
        "por_tecnico.html",
        "por_sucursal.html", 
        "productividad.html",
        "eficiencia.html",
        "desempeno.html"
    ]
    
    for template_file in template_files:
        file_path = os.path.join(templates_dir, template_file)
        if os.path.exists(file_path):
            update_template_file(file_path)
        else:
            print(f"Archivo no encontrado: {file_path}")

if __name__ == "__main__":
    main() 