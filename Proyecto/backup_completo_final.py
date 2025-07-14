#!/usr/bin/env python3
"""
Script completo para hacer backup de TODA la base de datos local
Incluye todos los modelos de todas las apps en el orden correcto
"""

import os
import sys
import django
import json
from datetime import datetime
from django.core import serializers
from django.apps import apps

# Configurar Django para usar settings locales (MySQL)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

def backup_completo_final():
    """Backup completo de toda la base de datos"""
    
    # Crear directorio de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups_completos_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    print("🚀 Iniciando backup completo de toda la base de datos")
    print("=" * 60)
    
    # Definir todos los modelos en orden de dependencias
    # (los que no dependen de otros van primero)
    modelos_orden = [
        # 1. RECURSOS HUMANOS (ya migrados, pero incluimos todos)
        ('recursosHumanos', 'Provincia'),
        ('recursosHumanos', 'Ciudad'), 
        ('recursosHumanos', 'Sucursal'),
        ('recursosHumanos', 'TarifaManoObra'),
        ('recursosHumanos', 'ActividadTrabajo'),
        ('recursosHumanos', 'Competencia'),
        ('recursosHumanos', 'CertificacionJD'),
        ('recursosHumanos', 'CertificacionTecnico'),
        ('recursosHumanos', 'CompetenciaTecnico'),
        ('recursosHumanos', 'EvaluacionSistema'),
        ('recursosHumanos', 'RevisionHerramientas'),
        ('recursosHumanos', 'HerramientaEspecial'),
        ('recursosHumanos', 'PrestamoHerramienta'),
        ('recursosHumanos', 'RegistroHorasTecnico'),
        
        # 2. CLIENTES
        ('clientes', 'TipoEquipo'),
        ('clientes', 'ModeloEquipo'),
        ('clientes', 'ModeloMotor'),
        ('clientes', 'Cliente'),
        ('clientes', 'ContactoCliente'),
        ('clientes', 'Equipo'),
        ('clientes', 'RegistroHorometro'),
        
        # 3. OPERATIONS CENTER
        ('operationsCenter', 'OperationsCenterConfig'),
        ('operationsCenter', 'Machine'),
        ('operationsCenter', 'MachineLocation'),
        ('operationsCenter', 'MachineEngineHours'),
        ('operationsCenter', 'MachineAlert'),
        ('operationsCenter', 'MachineHoursOfOperation'),
        ('operationsCenter', 'DeviceStateReport'),
        ('operationsCenter', 'TelemetryReport'),
        ('operationsCenter', 'TelemetryReportMachine'),
        
        # 4. CENTRO SOLUCIONES
        ('centroSoluciones', 'CodigoAlerta'),
        ('centroSoluciones', 'AlertaEquipo'),
        ('centroSoluciones', 'LeadJohnDeere'),
        ('centroSoluciones', 'AsignacionAlerta'),
        
        # 5. CRM
        ('crm', 'Campania'),
        ('crm', 'Contacto'),
        ('crm', 'PotencialCompraModelo'),
        ('crm', 'AnalisisCliente'),
        ('crm', 'PaqueteServicio'),
        ('crm', 'ClientePaquete'),
        ('crm', 'Campana'),
        ('crm', 'EmbudoVentas'),
        ('crm', 'ContactoCliente'),
        ('crm', 'SugerenciaMejora'),
        
        # 6. VENTA MAQUINARIAS
        ('ventaMaquinarias', 'EquipoStock'),
        ('ventaMaquinarias', 'Certificado'),
        ('ventaMaquinarias', 'MovimientoStockCertificado'),
        ('ventaMaquinarias', 'VentaEquipo'),
        ('ventaMaquinarias', 'ChecklistProcesosJD'),
        ('ventaMaquinarias', 'TransferenciaEquipo'),
        
        # 7. GESTION DE TALLER (más complejo, con muchas dependencias)
        ('gestionDeTaller', 'Servicio'),
        ('gestionDeTaller', 'Repuesto'),
        ('gestionDeTaller', 'PreOrden'),
        ('gestionDeTaller', 'PedidoRepuestosTerceros'),
        ('gestionDeTaller', 'GastoAsistencia'),
        ('gestionDeTaller', 'VentaRepuesto'),
        ('gestionDeTaller', 'Revision5S'),
        ('gestionDeTaller', 'EvidenciaRevision5S'),
        ('gestionDeTaller', 'PlanAccion5S'),
        ('gestionDeTaller', 'EvidenciaPlanAccion5S'),
        ('gestionDeTaller', 'CostoPersonalTaller'),
        ('gestionDeTaller', 'AnalisisTaller'),
        ('gestionDeTaller', 'Evidencia'),
        ('gestionDeTaller', 'ChecklistSalidaCampo'),
        ('gestionDeTaller', 'EncuestaServicio'),
        ('gestionDeTaller', 'RespuestaEncuesta'),
        ('gestionDeTaller', 'InsatisfaccionCliente'),
        ('gestionDeTaller', 'LogCambioServicio'),
        ('gestionDeTaller', 'LogCambioInforme'),
        ('gestionDeTaller', 'ObservacionServicio'),
        ('gestionDeTaller', 'HerramientaEspecial'),
        ('gestionDeTaller', 'ReservaHerramienta'),
        ('gestionDeTaller', 'LogHerramienta'),
        ('gestionDeTaller', 'HerramientaPersonal'),
        ('gestionDeTaller', 'ItemHerramientaPersonal'),
        ('gestionDeTaller', 'AsignacionHerramientaPersonal'),
        ('gestionDeTaller', 'AuditoriaHerramientaPersonal'),
        ('gestionDeTaller', 'LogCambioItemHerramienta'),
        ('gestionDeTaller', 'DetalleAuditoriaHerramienta'),
    ]
    
    total_modelos = len(modelos_orden)
    exitosos = 0
    fallidos = 0
    resumen = []
    
    print(f"📊 Total de modelos a respaldar: {total_modelos}")
    print()
    
    for i, (app_label, model_name) in enumerate(modelos_orden, 1):
        try:
            # Obtener el modelo
            model = apps.get_model(app_label, model_name)
            if not model:
                print(f"❌ {i:2d}/{total_modelos} - {app_label}.{model_name}: Modelo no encontrado")
                fallidos += 1
                continue
            
            # Contar registros
            count = model.objects.count()
            
            if count == 0:
                print(f"⚠️  {i:2d}/{total_modelos} - {app_label}.{model_name}: Sin datos")
                resumen.append({
                    'app': app_label,
                    'modelo': model_name,
                    'registros': 0,
                    'archivo': None,
                    'estado': 'sin_datos'
                })
                continue
            
            # Crear nombre de archivo
            filename = f"{i:02d}_{app_label}_{model_name.lower()}.json"
            filepath = os.path.join(backup_dir, filename)
            
            # Serializar datos
            data = serializers.serialize('json', model.objects.all())
            
            # Guardar archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data)
            
            # Verificar que se guardó correctamente
            file_size = os.path.getsize(filepath)
            
            print(f"✅ {i:2d}/{total_modelos} - {app_label}.{model_name}: {count:,} registros ({file_size:,} bytes)")
            
            resumen.append({
                'app': app_label,
                'modelo': model_name,
                'registros': count,
                'archivo': filename,
                'estado': 'exitoso',
                'tamaño': file_size
            })
            
            exitosos += 1
            
        except Exception as e:
            print(f"❌ {i:2d}/{total_modelos} - {app_label}.{model_name}: Error - {str(e)}")
            resumen.append({
                'app': app_label,
                'modelo': model_name,
                'registros': 0,
                'archivo': None,
                'estado': 'error',
                'error': str(e)
            })
            fallidos += 1
    
    # Crear archivo de resumen
    resumen_data = {
        'fecha_backup': timestamp,
        'total_modelos': total_modelos,
        'exitosos': exitosos,
        'fallidos': fallidos,
        'sin_datos': len([r for r in resumen if r['estado'] == 'sin_datos']),
        'detalles': resumen
    }
    
    resumen_file = os.path.join(backup_dir, 'RESUMEN_BACKUP_COMPLETO.json')
    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(resumen_data, f, indent=2, ensure_ascii=False)
    
    # Mostrar resumen final
    print()
    print("=" * 60)
    print("📋 RESUMEN DEL BACKUP COMPLETO")
    print("=" * 60)
    print(f"📁 Directorio: {backup_dir}/")
    print(f"📊 Total de modelos: {total_modelos}")
    print(f"✅ Exitosos: {exitosos}")
    print(f"❌ Fallidos: {fallidos}")
    print(f"⚠️  Sin datos: {len([r for r in resumen if r['estado'] == 'sin_datos'])}")
    print()
    
    # Mostrar modelos con más datos
    modelos_con_datos = [r for r in resumen if r['estado'] == 'exitoso' and r['registros'] > 0]
    if modelos_con_datos:
        print("🏆 TOP 10 - Modelos con más registros:")
        modelos_con_datos.sort(key=lambda x: x['registros'], reverse=True)
        for i, modelo in enumerate(modelos_con_datos[:10], 1):
            print(f"   {i:2d}. {modelo['app']}.{modelo['modelo']}: {modelo['registros']:,} registros")
    
    print()
    print("🎉 Backup completo finalizado!")
    print(f"📁 Archivos guardados en: {backup_dir}/")
    print(f"📋 Resumen detallado: {resumen_file}")
    
    return backup_dir, resumen_data

if __name__ == '__main__':
    backup_completo_final() 