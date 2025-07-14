#!/usr/bin/env python3
"""
Script simple para actualizar URLs de archivos media usando modelos de Django
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def actualizar_urls_simple():
    """Actualizar URLs de archivos media usando modelos de Django"""
    
    print("🔄 Actualizando URLs de archivos media")
    print("=" * 50)
    
    total_actualizados = 0
    
    try:
        # Importar modelos
        from gestionDeTaller.models import HerramientaEspecial, EvidenciaRevision5S, EvidenciaPlanAccion5S, Evidencia
        from recursosHumanos.models import HerramientaEspecial as HerramientaEspecialRH, PrestamoHerramienta
        
        # 1. Herramientas Especiales (Gestión de Taller)
        print("\n📋 Actualizando herramientas especiales (Gestión de Taller)...")
        herramientas = HerramientaEspecial.objects.filter(foto__contains='/media/')
        for herramienta in herramientas:
            if herramienta.foto and '/media/' in herramienta.foto:
                herramienta.foto = herramienta.foto.replace('/media/', '/static/')
                herramienta.save()
                total_actualizados += 1
                print(f"   ✅ {herramienta.nombre}: {herramienta.foto}")
        
        print(f"   📊 Actualizadas: {herramientas.count()}")
        
        # 2. Evidencias de Revisión 5S
        print("\n📋 Actualizando evidencias de revisión 5S...")
        evidencias = EvidenciaRevision5S.objects.filter(imagen__contains='/media/')
        for evidencia in evidencias:
            if evidencia.imagen and '/media/' in evidencia.imagen:
                evidencia.imagen = evidencia.imagen.replace('/media/', '/static/')
                evidencia.save()
                total_actualizados += 1
                print(f"   ✅ ID {evidencia.id}: {evidencia.imagen}")
        
        print(f"   📊 Actualizadas: {evidencias.count()}")
        
        # 3. Evidencias de Plan de Acción 5S
        print("\n📋 Actualizando evidencias de plan de acción 5S...")
        evidencias_plan = EvidenciaPlanAccion5S.objects.filter(imagen__contains='/media/')
        for evidencia in evidencias_plan:
            if evidencia.imagen and '/media/' in evidencia.imagen:
                evidencia.imagen = evidencia.imagen.replace('/media/', '/static/')
                evidencia.save()
                total_actualizados += 1
                print(f"   ✅ ID {evidencia.id}: {evidencia.imagen}")
        
        print(f"   📊 Actualizadas: {evidencias_plan.count()}")
        
        # 4. Evidencias generales
        print("\n📋 Actualizando evidencias generales...")
        evidencias_gen = Evidencia.objects.filter(imagen__contains='/media/')
        for evidencia in evidencias_gen:
            if evidencia.imagen and '/media/' in evidencia.imagen:
                evidencia.imagen = evidencia.imagen.replace('/media/', '/static/')
                evidencia.save()
                total_actualizados += 1
                print(f"   ✅ ID {evidencia.id}: {evidencia.imagen}")
        
        print(f"   📊 Actualizadas: {evidencias_gen.count()}")
        
        # 5. Herramientas Especiales (Recursos Humanos)
        print("\n📋 Actualizando herramientas especiales (Recursos Humanos)...")
        herramientas_rh = HerramientaEspecialRH.objects.filter(foto__contains='/media/')
        for herramienta in herramientas_rh:
            if herramienta.foto and '/media/' in herramienta.foto:
                herramienta.foto = herramienta.foto.replace('/media/', '/static/')
                herramienta.save()
                total_actualizados += 1
                print(f"   ✅ {herramienta.nombre}: {herramienta.foto}")
        
        print(f"   📊 Actualizadas: {herramientas_rh.count()}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    print(f"\n🎉 Actualización completada!")
    print(f"📊 Total de registros actualizados: {total_actualizados}")
    
    return total_actualizados

def verificar_urls():
    """Verificar que las URLs se actualizaron correctamente"""
    
    print("\n🔍 Verificando URLs actualizadas:")
    print("=" * 40)
    
    try:
        from gestionDeTaller.models import HerramientaEspecial, EvidenciaRevision5S
        
        # Verificar herramientas especiales
        herramientas = HerramientaEspecial.objects.filter(foto__contains='/static/')[:5]
        print(f"📋 Herramientas especiales con URLs /static/: {herramientas.count()}")
        
        for herramienta in herramientas:
            print(f"   🔧 {herramienta.nombre}: {herramienta.foto}")
        
        # Verificar evidencias 5S
        evidencias = EvidenciaRevision5S.objects.filter(imagen__contains='/static/')[:3]
        print(f"\n📋 Evidencias 5S con URLs /static/: {evidencias.count()}")
        
        for evidencia in evidencias:
            print(f"   📸 ID {evidencia.id}: {evidencia.imagen}")
            
    except Exception as e:
        print(f"❌ Error verificando: {str(e)}")

if __name__ == '__main__':
    actualizar_urls_simple()
    verificar_urls() 