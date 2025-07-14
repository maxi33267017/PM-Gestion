# Guía Completa de Migración de Base de Datos

## 📋 Resumen
Esta guía te ayudará a migrar **TODA** la información de tu base de datos local (MySQL) a la base de datos online (PostgreSQL en Render.com).

## 🎯 Estado Actual
✅ **Ya migrado:**
- Usuarios (10 registros)
- Provincias (3 registros)
- Ciudades (5 registros)
- Sucursales (2 registros)

❌ **Pendiente de migrar:**
- Clientes y equipos
- Operations Center
- Centro Soluciones
- CRM
- Venta Maquinarias
- Gestión de Taller
- Recursos Humanos (datos adicionales)

## 🚀 Proceso de Migración Completa

### Paso 1: Backup Completo Local
```bash
# En tu máquina local (con MySQL)
cd /ruta/a/tu/proyecto
python backup_completo_final.py
```

Este script creará un directorio `backups_completos_YYYYMMDD_HHMMSS/` con:
- Archivos JSON para cada modelo (70+ modelos)
- Resumen detallado del backup
- Orden correcto de dependencias

### Paso 2: Subir Archivos al Servidor
```bash
# Opción A: Usar scp/rsync
scp -r backups_completos_* usuario@servidor:/app/Proyecto/

# Opción B: Usar git (si tienes repositorio)
git add backups_completos_*
git commit -m "Backup completo para migración"
git push

# Opción C: Subir manualmente por interfaz web
```

### Paso 3: Cargar Datos en Render.com
```bash
# En el servidor de Render.com
cd /app/Proyecto

# Cargar todo de una vez
python cargar_completo_online.py

# O cargar por app específica
python cargar_completo_online.py --app clientes
python cargar_completo_online.py --app operationsCenter
python cargar_completo_online.py --app gestionDeTaller
```

## 📊 Modelos por App

### 1. Recursos Humanos (14 modelos)
- Provincia, Ciudad, Sucursal ✅
- TarifaManoObra, ActividadTrabajo
- Competencia, CertificacionJD, CertificacionTecnico
- EvaluacionSistema, RevisionHerramientas
- HerramientaEspecial, PrestamoHerramienta
- RegistroHorasTecnico

### 2. Clientes (7 modelos)
- TipoEquipo, ModeloEquipo, ModeloMotor
- Cliente, ContactoCliente
- Equipo, RegistroHorometro

### 3. Operations Center (9 modelos)
- OperationsCenterConfig, Machine
- MachineLocation, MachineEngineHours
- MachineAlert, MachineHoursOfOperation
- DeviceStateReport, TelemetryReport
- TelemetryReportMachine

### 4. Centro Soluciones (4 modelos)
- CodigoAlerta, AlertaEquipo
- LeadJohnDeere, AsignacionAlerta

### 5. CRM (10 modelos)
- Campania, Contacto, PotencialCompraModelo
- AnalisisCliente, PaqueteServicio, ClientePaquete
- Campana, EmbudoVentas, ContactoCliente
- SugerenciaMejora

### 6. Venta Maquinarias (6 modelos)
- EquipoStock, Certificado
- MovimientoStockCertificado, VentaEquipo
- ChecklistProcesosJD, TransferenciaEquipo

### 7. Gestión de Taller (25 modelos)
- Servicio, Repuesto, PreOrden
- PedidoRepuestosTerceros, GastoAsistencia
- VentaRepuesto, Revision5S
- EvidenciaRevision5S, PlanAccion5S
- EvidenciaPlanAccion5S, CostoPersonalTaller
- AnalisisTaller, Evidencia
- ChecklistSalidaCampo, EncuestaServicio
- RespuestaEncuesta, InsatisfaccionCliente
- LogCambioServicio, LogCambioInforme
- ObservacionServicio, HerramientaEspecial
- ReservaHerramienta, LogHerramienta
- HerramientaPersonal, ItemHerramientaPersonal
- AsignacionHerramientaPersonal
- AuditoriaHerramientaPersonal
- LogCambioItemHerramienta
- DetalleAuditoriaHerramienta

## 🔧 Scripts Disponibles

### Para Backup (Local)
- `backup_completo_final.py` - Backup completo de todos los modelos
- `backup_database.py` - Backup básico (solo datos esenciales)

### Para Carga (Render.com)
- `cargar_completo_online.py` - Cargar todo el backup completo
- `cargar_datos_loaddata.py` - Cargar datos básicos
- `loaddata_simple.py` - Script simple para loaddata

## ⚠️ Consideraciones Importantes

### 1. Orden de Dependencias
Los modelos se cargan en un orden específico para respetar las relaciones:
- Primero: Modelos independientes (Provincia, Ciudad, etc.)
- Después: Modelos que dependen de otros (Cliente, Equipo, etc.)

### 2. Tamaño de Archivos
- Algunos modelos pueden tener miles de registros
- Los archivos grandes pueden tardar más en cargar
- Si un archivo falla, puedes cargarlo individualmente

### 3. Errores Comunes
- **Claves duplicadas**: Si ya existen registros, usar `--ignorenonexistent`
- **Relaciones faltantes**: Asegurar que los modelos padre se carguen primero
- **Formato de datos**: Verificar que las fechas y campos especiales sean compatibles

### 4. Verificación Post-Migración
```bash
# Verificar que los datos se cargaron
python manage.py shell
```
```python
from django.contrib.auth import get_user_model
from clientes.models import Cliente
from gestionDeTaller.models import Servicio

User = get_user_model()
print(f"Usuarios: {User.objects.count()}")
print(f"Clientes: {Cliente.objects.count()}")
print(f"Servicios: {Servicio.objects.count()}")
```

## 🚨 Troubleshooting

### Error: "No fixture named..."
```bash
# Usar ruta completa
python manage.py loaddata backups_completos_*/01_recursoshumanos_provincia.json
```

### Error: "Duplicate key value violates unique constraint"
```bash
# Los datos ya existen, usar --ignorenonexistent
python manage.py loaddata archivo.json --ignorenonexistent
```

### Error: "Foreign key constraint failed"
- Verificar que los modelos padre se cargaron primero
- Revisar el orden en el script de backup

### Error: "CSRF verification failed"
- Ya solucionado en settings_render.py
- Asegurar acceso por HTTPS en Render.com

## 📈 Monitoreo del Proceso

### Durante la Carga
- El script muestra progreso en tiempo real
- Indica cuántos registros se cargan por archivo
- Muestra errores específicos si fallan archivos

### Después de la Carga
- Revisar el resumen final
- Verificar que todos los archivos se cargaron
- Probar funcionalidades críticas del sistema

## 🎉 Resultado Final
Después de completar la migración tendrás:
- ✅ Toda la información de clientes y equipos
- ✅ Historial completo de servicios y mantenimientos
- ✅ Datos de ventas y stock
- ✅ Información de recursos humanos
- ✅ Configuraciones de operations center
- ✅ Datos de CRM y marketing

¡Tu sistema estará completamente funcional en Render.com! 