# 📊 Guía de Migración de Datos

## 🎯 **Objetivo**

Migrar todos los datos de la aplicación local a la base de datos online en Render.com de manera organizada y segura.

## ✅ **Backup Completado**

### **Primera Fase - Datos Básicos (COMPLETADO)**
- ✅ **Provincias**: 3 registros
- ✅ **Ciudades**: 5 registros  
- ✅ **Sucursales**: 2 registros
- ✅ **Usuarios**: 10 registros

**Archivos generados:**
- `backups_20250714_174234/01_provincias.json`
- `backups_20250714_174234/02_ciudades.json`
- `backups_20250714_174234/03_sucursales.json`
- `backups_20250714_174234/04_usuarios.json`
- `backups_20250714_174234/RESUMEN_BACKUP.json`

## 🚀 **Próximos Pasos**

### **1. Migrar Datos Básicos a Online**
```bash
cd /app/Proyecto
python migrate_to_online.py
```

### **2. Hacer Backup Completo**
```bash
cd /app/Proyecto
python backup_complete.py
```

### **3. Verificar Migración**
- Acceder a https://pm-gestion.onrender.com
- Probar login con usuarios migrados
- Verificar que provincias, ciudades y sucursales estén correctas

## 📋 **Estructura de Migración**

### **Fase 1: Datos Básicos (COMPLETADO)**
1. 🌍 Provincias
2. 🏙️ Ciudades  
3. 🏢 Sucursales
4. 👥 Usuarios

### **Fase 2: Recursos Humanos**
5. 💰 Tarifas de mano de obra
6. ⏰ Registro de horas técnico
7. 📋 Actividades de trabajo
8. 🎯 Competencias
9. 📊 Competencias de técnicos
10. 🏆 Certificaciones de técnicos
11. 🏆 Certificaciones JD
12. 📈 Evaluaciones del sistema
13. 🔧 Herramientas especiales
14. 📦 Préstamos de herramientas
15. 🔍 Revisiones de herramientas

### **Fase 3: Clientes**
16. 👤 Clientes
17. 📞 Contactos de clientes
18. 🚜 Equipos
19. 📐 Modelos de equipos
20. 🔧 Modelos de motores
21. 🏷️ Tipos de equipos
22. 📊 Registros de horómetro

### **Fase 4: Gestión de Taller**
23. 🔧 Servicios
24. 📋 Pre-órdenes
25. 📸 Evidencias
26. 📦 Pedidos de repuestos
27. 📊 Encuestas de servicio
28. ✅ Respuestas de encuesta
29. 🔩 Repuestos
30. 💰 Ventas de repuestos
31. 💸 Gastos de asistencia
32. 📝 Observaciones de servicio
33. 📝 Logs de cambios de servicio
34. 📝 Logs de cambios de informe
35. 🔍 Revisiones 5S
36. 📋 Planes de acción 5S
37. ✅ Checklists de salida
38. 😞 Insatisfacciones de cliente
39. 🔧 Herramientas personal
40. 📦 Items de herramientas personal
41. 👥 Asignaciones de herramientas
42. 🔍 Auditorías de herramientas
43. 📋 Detalles de auditorías
44. 📝 Logs de cambios de items
45. 📝 Logs de herramientas
46. 📅 Reservas de herramientas
47. 💰 Costos de personal
48. 📊 Análisis de taller

### **Fase 5: CRM**
49. 📞 Contactos CRM
50. 👤 Contactos de clientes CRM
51. 📢 Campañas
52. 📦 Paquetes de servicio
53. 👥 Clientes paquetes
54. 📊 Análisis de clientes
55. 📈 Embudos de ventas
56. 🎯 Potenciales de compra
57. 💡 Sugerencias de mejora

### **Fase 6: Venta de Maquinarias**
58. 📦 Equipos en stock
59. 💰 Ventas de equipos
60. 🏆 Certificados
61. ✅ Checklists de procesos
62. 📊 Movimientos de stock
63. 🔄 Transferencias de equipos

### **Fase 7: Operations Center**
64. 🖥️ Máquinas
65. ⚠️ Alertas de máquinas
66. ⏰ Horas de motor
67. ⏰ Horas de operación
68. 📍 Ubicaciones de máquinas
69. ⚙️ Configuración del centro
70. 📊 Reportes de estado
71. 📡 Reportes de telemetría
72. 📡 Telemetría de máquinas

### **Fase 8: Centro de Soluciones**
73. ⚠️ Alertas de equipos
74. 👥 Asignaciones de alertas
75. 🔢 Códigos de alerta
76. 🎯 Leads John Deere

## 🔧 **Scripts Disponibles**

### **1. backup_database.py**
- Backup de las 4 tablas básicas
- Uso: `python backup_database.py`

### **2. backup_complete.py**
- Backup de todas las tablas (76 archivos)
- Uso: `python backup_complete.py`

### **3. migrate_to_online.py**
- Migrar datos básicos a la base de datos online
- Uso: `python migrate_to_online.py`

## 📊 **Estadísticas del Backup**

### **Datos Básicos (Completado)**
- **Provincias**: 3 registros
- **Ciudades**: 5 registros
- **Sucursales**: 2 registros
- **Usuarios**: 10 registros
- **Total**: 20 registros

### **Backup Completo (Pendiente)**
- **Tablas**: 76 archivos JSON
- **Registros**: Variable (depende de los datos)
- **Tamaño**: Variable

## ⚠️ **Consideraciones Importantes**

### **Antes de Migrar**
1. ✅ Verificar que la base de datos online esté vacía
2. ✅ Tener backup de la base de datos online
3. ✅ Probar la conexión a la base de datos online
4. ✅ Verificar que las migraciones de Django estén aplicadas

### **Durante la Migración**
1. 🔄 Migrar en el orden especificado
2. 🔄 Verificar cada fase antes de continuar
3. 🔄 Mantener logs de la migración
4. 🔄 Hacer pausas entre fases grandes

### **Después de la Migración**
1. ✅ Verificar integridad de los datos
2. ✅ Probar funcionalidades críticas
3. ✅ Verificar relaciones entre tablas
4. ✅ Probar login de usuarios
5. ✅ Verificar permisos y roles

## 🎯 **Orden Recomendado de Migración**

1. **Datos Básicos** (ya completado)
2. **Recursos Humanos** (dependencias básicas)
3. **Clientes** (datos maestros)
4. **Gestión de Taller** (operaciones principales)
5. **CRM** (datos comerciales)
6. **Venta de Maquinarias** (ventas)
7. **Operations Center** (telemetría)
8. **Centro de Soluciones** (alertas)

## 📝 **Comandos de Verificación**

```bash
# Verificar conexión a base de datos online
cd /app/Proyecto
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render'); import django; django.setup(); from recursosHumanos.models import Provincia; print(f'Provincias online: {Provincia.objects.count()}')"

# Verificar datos migrados
python manage.py shell --settings=PatagoniaMaquinarias.settings_render
```

## 🎉 **Resultado Esperado**

Al finalizar la migración completa:
- ✅ Todos los datos locales en la base de datos online
- ✅ Aplicación funcionando correctamente en https://pm-gestion.onrender.com
- ✅ Usuarios pueden hacer login
- ✅ Todas las funcionalidades operativas
- ✅ Datos históricos preservados 