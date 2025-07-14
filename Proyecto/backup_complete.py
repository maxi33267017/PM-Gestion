#!/usr/bin/env python
"""
Script completo para hacer backup de todas las tablas importantes
Migración de datos a la web online
"""

import os
import sys
import django
import json
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

from django.core import serializers
from django.db import connection

# Importar todos los modelos necesarios
from recursosHumanos.models import (
    Provincia, Ciudad, Sucursal, Usuario, TarifaManoObra, 
    RegistroHorasTecnico, ActividadTrabajo, Competencia, 
    CompetenciaTecnico, CertificacionTecnico, CertificacionJD,
    EvaluacionSistema, HerramientaEspecial, PrestamoHerramienta,
    RevisionHerramientas
)

from clientes.models import (
    Cliente, ContactoCliente, Equipo, ModeloEquipo, 
    ModeloMotor, TipoEquipo, RegistroHorometro
)

from gestionDeTaller.models import (
    Servicio, PreOrden, Evidencia, PedidoRepuestosTerceros,
    EncuestaServicio, RespuestaEncuesta, Repuesto, VentaRepuesto,
    GastoAsistencia, ObservacionServicio, LogCambioServicio,
    LogCambioInforme, Revision5S, PlanAccion5S, ChecklistSalidaCampo,
    InsatisfaccionCliente, HerramientaPersonal, ItemHerramientaPersonal,
    AsignacionHerramientaPersonal, AuditoriaHerramientaPersonal,
    DetalleAuditoriaHerramienta, LogCambioItemHerramienta,
    LogHerramienta, ReservaHerramienta, CostoPersonalTaller,
    AnalisisTaller
)

from crm.models import (
    Contacto, ContactoCliente as CRMContactoCliente, Campania,
    PaqueteServicio, ClientePaquete, AnalisisCliente,
    EmbudoVentas, PotencialCompraModelo, SugerenciaMejora
)

from ventaMaquinarias.models import (
    EquipoStock, VentaEquipo, Certificado, ChecklistProcesosJD,
    MovimientosStockCertificado, TransferenciaEquipo
)

from operationsCenter.models import (
    Machine, MachineAlert, MachineEngineHours, MachineHoursOfOperation,
    MachineLocation, OperationsCenterConfig, DeviceStateReport,
    TelemetryReport, TelemetryReportMachine
)

from centroSoluciones.models import (
    AlertaEquipo, AsignacionAlerta, CodigoAlerta, LeadJohnDeere
)

def create_backup_directory():
    """Crear directorio para los backups"""
    backup_dir = f"backup_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_table(model_class, backup_dir, filename, description=""):
    """Hacer backup de una tabla específica"""
    try:
        # Obtener todos los registros
        objects = model_class.objects.all()
        
        # Serializar a JSON
        data = serializers.serialize('json', objects, indent=2)
        
        # Guardar en archivo
        filepath = os.path.join(backup_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
        
        count = objects.count()
        print(f"✅ {filename}: {count} registros exportados {description}")
        return filepath, count
        
    except Exception as e:
        print(f"❌ Error en {filename}: {str(e)}")
        return None, 0

def main():
    """Función principal"""
    print("🚀 Iniciando backup completo de base de datos local")
    print("=" * 60)
    
    # Crear directorio de backup
    backup_dir = create_backup_directory()
    print(f"📁 Directorio de backup: {backup_dir}")
    
    results = {}
    
    # ===== RECURSOS HUMANOS =====
    print("\n👥 RECURSOS HUMANOS")
    print("-" * 30)
    
    results['provincias'] = backup_table(Provincia, backup_dir, '01_provincias.json', "(Ubicaciones)")
    results['ciudades'] = backup_table(Ciudad, backup_dir, '02_ciudades.json', "(Ubicaciones)")
    results['sucursales'] = backup_table(Sucursal, backup_dir, '03_sucursales.json', "(Organización)")
    results['usuarios'] = backup_table(Usuario, backup_dir, '04_usuarios.json', "(Personal)")
    results['tarifas_mano_obra'] = backup_table(TarifaManoObra, backup_dir, '05_tarifas_mano_obra.json', "(Costos)")
    results['registro_horas'] = backup_table(RegistroHorasTecnico, backup_dir, '06_registro_horas.json', "(Tiempos)")
    results['actividades_trabajo'] = backup_table(ActividadTrabajo, backup_dir, '07_actividades_trabajo.json', "(Actividades)")
    results['competencias'] = backup_table(Competencia, backup_dir, '08_competencias.json', "(Habilidades)")
    results['competencias_tecnicos'] = backup_table(CompetenciaTecnico, backup_dir, '09_competencias_tecnicos.json', "(Evaluaciones)")
    results['certificaciones_tecnicos'] = backup_table(CertificacionTecnico, backup_dir, '10_certificaciones_tecnicos.json', "(Certificaciones)")
    results['certificaciones_jd'] = backup_table(CertificacionJD, backup_dir, '11_certificaciones_jd.json', "(Certificaciones JD)")
    results['evaluaciones_sistema'] = backup_table(EvaluacionSistema, backup_dir, '12_evaluaciones_sistema.json', "(Evaluaciones)")
    results['herramientas_especiales'] = backup_table(HerramientaEspecial, backup_dir, '13_herramientas_especiales.json', "(Herramientas)")
    results['prestamos_herramientas'] = backup_table(PrestamoHerramienta, backup_dir, '14_prestamos_herramientas.json', "(Préstamos)")
    results['revisiones_herramientas'] = backup_table(RevisionHerramientas, backup_dir, '15_revisiones_herramientas.json', "(Revisiones)")
    
    # ===== CLIENTES =====
    print("\n👤 CLIENTES")
    print("-" * 30)
    
    results['clientes'] = backup_table(Cliente, backup_dir, '16_clientes.json', "(Clientes)")
    results['contactos_clientes'] = backup_table(ContactoCliente, backup_dir, '17_contactos_clientes.json', "(Contactos)")
    results['equipos'] = backup_table(Equipo, backup_dir, '18_equipos.json', "(Equipos)")
    results['modelos_equipos'] = backup_table(ModeloEquipo, backup_dir, '19_modelos_equipos.json', "(Modelos)")
    results['modelos_motores'] = backup_table(ModeloMotor, backup_dir, '20_modelos_motores.json', "(Motores)")
    results['tipos_equipos'] = backup_table(TipoEquipo, backup_dir, '21_tipos_equipos.json', "(Tipos)")
    results['registros_horometro'] = backup_table(RegistroHorometro, backup_dir, '22_registros_horometro.json', "(Horómetros)")
    
    # ===== GESTIÓN DE TALLER =====
    print("\n🔧 GESTIÓN DE TALLER")
    print("-" * 30)
    
    results['servicios'] = backup_table(Servicio, backup_dir, '23_servicios.json', "(Servicios)")
    results['pre_ordenes'] = backup_table(PreOrden, backup_dir, '24_pre_ordenes.json', "(Pre-órdenes)")
    results['evidencias'] = backup_table(Evidencia, backup_dir, '25_evidencias.json', "(Evidencias)")
    results['pedidos_repuestos'] = backup_table(PedidoRepuestosTerceros, backup_dir, '26_pedidos_repuestos.json', "(Pedidos)")
    results['encuestas_servicio'] = backup_table(EncuestaServicio, backup_dir, '27_encuestas_servicio.json', "(Encuestas)")
    results['respuestas_encuesta'] = backup_table(RespuestaEncuesta, backup_dir, '28_respuestas_encuesta.json', "(Respuestas)")
    results['repuestos'] = backup_table(Repuesto, backup_dir, '29_repuestos.json', "(Repuestos)")
    results['ventas_repuestos'] = backup_table(VentaRepuesto, backup_dir, '30_ventas_repuestos.json', "(Ventas)")
    results['gastos_asistencia'] = backup_table(GastoAsistencia, backup_dir, '31_gastos_asistencia.json', "(Gastos)")
    results['observaciones_servicio'] = backup_table(ObservacionServicio, backup_dir, '32_observaciones_servicio.json', "(Observaciones)")
    results['log_cambios_servicio'] = backup_table(LogCambioServicio, backup_dir, '33_log_cambios_servicio.json', "(Logs)")
    results['log_cambios_informe'] = backup_table(LogCambioInforme, backup_dir, '34_log_cambios_informe.json', "(Logs)")
    results['revisiones_5s'] = backup_table(Revision5S, backup_dir, '35_revisiones_5s.json', "(5S)")
    results['planes_accion_5s'] = backup_table(PlanAccion5S, backup_dir, '36_planes_accion_5s.json', "(5S)")
    results['checklists_salida'] = backup_table(ChecklistSalidaCampo, backup_dir, '37_checklists_salida.json', "(Checklists)")
    results['insatisfacciones_cliente'] = backup_table(InsatisfaccionCliente, backup_dir, '38_insatisfacciones_cliente.json', "(Insatisfacciones)")
    results['herramientas_personal'] = backup_table(HerramientaPersonal, backup_dir, '39_herramientas_personal.json', "(Herramientas)")
    results['items_herramientas'] = backup_table(ItemHerramientaPersonal, backup_dir, '40_items_herramientas.json', "(Items)")
    results['asignaciones_herramientas'] = backup_table(AsignacionHerramientaPersonal, backup_dir, '41_asignaciones_herramientas.json', "(Asignaciones)")
    results['auditorias_herramientas'] = backup_table(AuditoriaHerramientaPersonal, backup_dir, '42_auditorias_herramientas.json', "(Auditorías)")
    results['detalles_auditorias'] = backup_table(DetalleAuditoriaHerramienta, backup_dir, '43_detalles_auditorias.json', "(Detalles)")
    results['log_cambios_items'] = backup_table(LogCambioItemHerramienta, backup_dir, '44_log_cambios_items.json', "(Logs)")
    results['log_herramientas'] = backup_table(LogHerramienta, backup_dir, '45_log_herramientas.json', "(Logs)")
    results['reservas_herramientas'] = backup_table(ReservaHerramienta, backup_dir, '46_reservas_herramientas.json', "(Reservas)")
    results['costos_personal'] = backup_table(CostoPersonalTaller, backup_dir, '47_costos_personal.json', "(Costos)")
    results['analisis_taller'] = backup_table(AnalisisTaller, backup_dir, '48_analisis_taller.json', "(Análisis)")
    
    # ===== CRM =====
    print("\n📊 CRM")
    print("-" * 30)
    
    results['contactos_crm'] = backup_table(Contacto, backup_dir, '49_contactos_crm.json', "(Contactos)")
    results['contactos_clientes_crm'] = backup_table(CRMContactoCliente, backup_dir, '50_contactos_clientes_crm.json', "(Contactos)")
    results['campanias'] = backup_table(Campania, backup_dir, '51_campanias.json', "(Campañas)")
    results['paquetes_servicio'] = backup_table(PaqueteServicio, backup_dir, '52_paquetes_servicio.json', "(Paquetes)")
    results['clientes_paquetes'] = backup_table(ClientePaquete, backup_dir, '53_clientes_paquetes.json', "(Clientes)")
    results['analisis_clientes'] = backup_table(AnalisisCliente, backup_dir, '54_analisis_clientes.json', "(Análisis)")
    results['embudos_ventas'] = backup_table(EmbudoVentas, backup_dir, '55_embudos_ventas.json', "(Embudos)")
    results['potenciales_compra'] = backup_table(PotencialCompraModelo, backup_dir, '56_potenciales_compra.json', "(Potenciales)")
    results['sugerencias_mejora'] = backup_table(SugerenciaMejora, backup_dir, '57_sugerencias_mejora.json', "(Sugerencias)")
    
    # ===== VENTA MAQUINARIAS =====
    print("\n🚜 VENTA MAQUINARIAS")
    print("-" * 30)
    
    results['equipos_stock'] = backup_table(EquipoStock, backup_dir, '58_equipos_stock.json', "(Stock)")
    results['ventas_equipos'] = backup_table(VentaEquipo, backup_dir, '59_ventas_equipos.json', "(Ventas)")
    results['certificados'] = backup_table(Certificado, backup_dir, '60_certificados.json', "(Certificados)")
    results['checklists_procesos'] = backup_table(ChecklistProcesosJD, backup_dir, '61_checklists_procesos.json', "(Checklists)")
    results['movimientos_stock'] = backup_table(MovimientosStockCertificado, backup_dir, '62_movimientos_stock.json', "(Movimientos)")
    results['transferencias_equipos'] = backup_table(TransferenciaEquipo, backup_dir, '63_transferencias_equipos.json', "(Transferencias)")
    
    # ===== OPERATIONS CENTER =====
    print("\n🖥️ OPERATIONS CENTER")
    print("-" * 30)
    
    results['machines'] = backup_table(Machine, backup_dir, '64_machines.json', "(Máquinas)")
    results['machine_alerts'] = backup_table(MachineAlert, backup_dir, '65_machine_alerts.json', "(Alertas)")
    results['machine_engine_hours'] = backup_table(MachineEngineHours, backup_dir, '66_machine_engine_hours.json', "(Horas motor)")
    results['machine_hours_operation'] = backup_table(MachineHoursOfOperation, backup_dir, '67_machine_hours_operation.json', "(Horas operación)")
    results['machine_locations'] = backup_table(MachineLocation, backup_dir, '68_machine_locations.json', "(Ubicaciones)")
    results['operations_center_config'] = backup_table(OperationsCenterConfig, backup_dir, '69_operations_center_config.json', "(Configuración)")
    results['device_state_reports'] = backup_table(DeviceStateReport, backup_dir, '70_device_state_reports.json', "(Reportes estado)")
    results['telemetry_reports'] = backup_table(TelemetryReport, backup_dir, '71_telemetry_reports.json', "(Reportes telemetría)")
    results['telemetry_report_machines'] = backup_table(TelemetryReportMachine, backup_dir, '72_telemetry_report_machines.json', "(Telemetría máquinas)")
    
    # ===== CENTRO SOLUCIONES =====
    print("\n🔧 CENTRO SOLUCIONES")
    print("-" * 30)
    
    results['alertas_equipos'] = backup_table(AlertaEquipo, backup_dir, '73_alertas_equipos.json', "(Alertas)")
    results['asignaciones_alertas'] = backup_table(AsignacionAlerta, backup_dir, '74_asignaciones_alertas.json', "(Asignaciones)")
    results['codigos_alerta'] = backup_table(CodigoAlerta, backup_dir, '75_codigos_alerta.json', "(Códigos)")
    results['leads_johndeere'] = backup_table(LeadJohnDeere, backup_dir, '76_leads_johndeere.json', "(Leads JD)")
    
    # Crear resumen
    print("\n📋 Creando resumen del backup...")
    summary = {
        'fecha_backup': datetime.now().isoformat(),
        'directorio': backup_dir,
        'resumen': {k: {'archivo': v[0], 'registros': v[1]} for k, v in results.items() if v[0] is not None}
    }
    
    summary_file = os.path.join(backup_dir, 'RESUMEN_BACKUP_COMPLETO.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Resumen guardado en: {summary_file}")
    
    # Estadísticas finales
    total_tables = len([v for v in results.values() if v[0] is not None])
    total_records = sum([v[1] for v in results.values() if v[0] is not None])
    
    print("\n" + "=" * 60)
    print("🎉 Backup completo finalizado!")
    print(f"📁 Directorio: {backup_dir}")
    print(f"📊 Tablas exportadas: {total_tables}")
    print(f"📊 Registros totales: {total_records}")
    print("\n📋 Próximos pasos:")
    print("1. Revisar los archivos JSON generados")
    print("2. Verificar que los datos sean correctos")
    print("3. Proceder con la migración a la base de datos online")

if __name__ == '__main__':
    main() 