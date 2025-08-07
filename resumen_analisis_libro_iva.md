# 📊 ANÁLISIS DEL LIBRO IVA - JULIO 2025

## 📋 RESUMEN EJECUTIVO

### 📈 Datos Generales
- **Total de registros**: 298 facturas
- **Período**: Julio 2025
- **Moneda principal**: USD
- **Total de ventas**: $19,618,489.07

### 📄 Tipos de Comprobantes
- **Factura A**: 246 registros (82.6%)
- **Nota de Crédito A**: 17 registros (5.7%)
- **Nota de Débito A**: 15 registros (5.0%)
- **Factura B**: 11 registros (3.7%)
- **Otros**: 9 registros (3.0%)

## 🏷️ CATEGORIZACIÓN DE VENTAS

### 🔧 REPUESTOS (RE)
- **Registros identificados**: 0
- **Observación**: No se encontraron patrones claros de repuestos en los nombres de clientes
- **Sugerencia**: Revisar si hay códigos específicos o descripciones en otros campos

### 🚜 MAQUINARIAS (MN)
- **Registros identificados**: 1
- **Monto total**: $146.53
- **Cliente**: MAQUINARIAS DEL SUR S. R. L.
- **Porcentaje del total**: 0.0%

### 🔧 SERVICIOS (SE)
- **Registros identificados**: 20
- **Monto total**: $2,213,068.73
- **Promedio por factura**: $110,653.44
- **Clientes únicos**: 7
- **Porcentaje del total**: 11.3%

#### Top 5 Clientes de Servicios:
1. **IBEROAMERICANA DE SERVICIOS S.A**: $890,395.27
2. **MONTAJES INDUSTRIALES OBRAS Y SERVICIOS**: $522,730.21
3. **ON TRANSPORTES Y SERVICIOS S.R.L**: $431,201.53
4. **OHM SERVICIOS GENERALES PETROLEROS S.R.L**: $211,482.16
5. **COOPERATIVA COOP LTDA DE PROVISION DE SE**: $156,439.80

### 👥 TOP 10 CLIENTES POR VOLUMEN
1. **MUNICIPALIDAD DE PICO TRUNCADO O. P.**: $4,671,405.80
2. **NACION SEGUROS SOCIEDAD ANONIMA**: $3,176,205.00
3. **GOLDWIND ARGENTINA S.A.**: $1,641,927.82
4. **CABALLERO DAIANA BELEN CRISTINA**: $1,200,000.00
5. **SAVIO INGENIERIA S.R.L.**: $1,124,401.56
6. **IBEROAMERICANA DE SERVICIOS S.A**: $890,395.27
7. **NELSON OLIVA SRL**: $618,965.20
8. **MONTAJES INDUSTRIALES OBRAS Y SERVICIOS**: $522,730.21
9. **DALMAS S.R.L.**: $521,065.15
10. **ON TRANSPORTES Y SERVICIOS S.R.L**: $431,201.53

## 📅 ANÁLISIS TEMPORAL
- **Días con ventas**: 26 días
- **Promedio diario**: $754,557.27
- **Día de mayor venta**: 24/07/2025 ($4,733,535.62)
- **Día de menor venta**: 01/07/2025 ($2,628.99)

## 🎯 ESTRATEGIA DE IMPLEMENTACIÓN

### 1. MODELO DE DATOS SUGERIDO

```python
class LibroIva(models.Model):
    fecha = models.DateField()
    tipo_comprobante = models.CharField(max_length=50)
    punto_venta = models.IntegerField()
    numero_desde = models.IntegerField()
    cod_autorizacion = models.CharField(max_length=50)
    tipo_doc_receptor = models.CharField(max_length=20)
    nro_doc_receptor = models.CharField(max_length=20)
    denominacion_receptor = models.CharField(max_length=200)
    tipo_cambio = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)
    imp_neto_gravado = models.DecimalField(max_digits=15, decimal_places=2)
    imp_neto_no_gravado = models.DecimalField(max_digits=15, decimal_places=2)
    imp_op_exentas = models.DecimalField(max_digits=15, decimal_places=2)
    iva = models.DecimalField(max_digits=15, decimal_places=2)
    imp_total = models.DecimalField(max_digits=15, decimal_places=2)
    categoria = models.CharField(max_length=10, choices=[
        ('RE', 'Repuestos'),
        ('MN', 'Maquinarias'),
        ('SE', 'Servicios'),
        ('OT', 'Otros')
    ])
    mes = models.IntegerField()
    año = models.IntegerField()
    
    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['categoria']),
            models.Index(fields=['mes', 'año']),
        ]
```

### 2. FUNCIÓN DE IMPORTACIÓN

```python
def importar_libro_iva(archivo_excel, mes, año):
    '''Importa datos del Libro IVA desde Excel'''
    
    # Leer archivo Excel
    df = pd.read_excel(archivo_excel)
    
    # Categorizar automáticamente
    df['categoria'] = df['Denominación Receptor'].apply(categorizar_venta)
    
    # Guardar en base de datos
    for _, row in df.iterrows():
        LibroIva.objects.create(
            fecha=row['Fecha'],
            tipo_comprobante=row['Tipo'],
            punto_venta=row['Punto de Venta'],
            numero_desde=row['Número Desde'],
            cod_autorizacion=row['Cód. Autorización'],
            tipo_doc_receptor=row['Tipo Doc. Receptor'],
            nro_doc_receptor=row['Nro. Doc. Receptor'],
            denominacion_receptor=row['Denominación Receptor'],
            tipo_cambio=row['Tipo Cambio'],
            moneda=row['Moneda'],
            imp_neto_gravado=row['Imp. Neto Gravado'],
            imp_neto_no_gravado=row['Imp. Neto No Gravado'],
            imp_op_exentas=row['Imp. Op. Exentas'],
            iva=row['IVA'],
            imp_total=row['Imp. Total'],
            categoria=row['categoria'],
            mes=mes,
            año=año
        )
    
    return len(df)
```

### 3. FUNCIÓN DE CATEGORIZACIÓN

```python
def categorizar_venta(denominacion):
    '''Categoriza automáticamente una venta'''
    
    patrones_repuestos = [
        'REPUESTO', 'FILTRO', 'ACEITE', 'BATERIA', 'FRENO', 'EMBRAGUE',
        'NEUMATICO', 'LUBRICANTE', 'MOTOR', 'TRANSMISION', 'HIDRAULICO'
    ]
    patrones_maquinarias = [
        'MAQUINA', 'TRACTOR', 'EXCAVADORA', 'CARGADOR', 'MARTILLO',
        'COMPRESOR', 'GENERADOR', 'SOLDADORA', 'MOTOSIERRA', 'EQUIPO'
    ]
    patrones_servicios = [
        'SERVICIO', 'MANTENIMIENTO', 'REPARACION', 'INSTALACION',
        'MONTAJE', 'DIAGNOSTICO', 'REVISION', 'CALIBRACION'
    ]
    
    denominacion_upper = denominacion.upper()
    
    if any(patron in denominacion_upper for patron in patrones_repuestos):
        return 'RE'
    elif any(patron in denominacion_upper for patron in patrones_maquinarias):
        return 'MN'
    elif any(patron in denominacion_upper for patron in patrones_servicios):
        return 'SE'
    else:
        return 'OT'
```

## 📊 FUNCIONALIDADES SUGERIDAS

### 1. Dashboard de Ventas
- **Ventas por categoría** (RE, MN, SE, OT)
- **Top clientes** por volumen
- **Tendencias mensuales**
- **Análisis de rentabilidad**

### 2. Reportes Específicos
- **Reporte de repuestos** vendidos
- **Reporte de maquinarias** comercializadas
- **Reporte de servicios** prestados
- **Análisis de clientes** más frecuentes

### 3. Funcionalidades Avanzadas
- **Importación automática** mensual
- **Categorización inteligente** con IA
- **Alertas de ventas** bajas
- **Comparativas** entre meses

## 🔍 OBSERVACIONES IMPORTANTES

### ❌ Limitaciones Identificadas
1. **Categorización limitada**: Solo se identificaron 21 registros categorizados (7% del total)
2. **Patrones de nombres**: Los nombres de clientes no siempre reflejan el tipo de venta
3. **Falta de códigos**: No hay códigos específicos RE/MN/SE en los datos

### ✅ Oportunidades de Mejora
1. **Códigos específicos**: Agregar códigos de categoría en el sistema de gestión
2. **Descripción de productos**: Incluir descripción detallada de productos/servicios
3. **Categorización manual**: Permitir categorización manual de registros no identificados
4. **Machine Learning**: Implementar IA para categorización automática

## 🚀 PRÓXIMOS PASOS

### 1. Implementación Inmediata
- [ ] Crear modelo `LibroIva`
- [ ] Implementar función de importación
- [ ] Crear dashboard básico de ventas
- [ ] Agregar filtros por fecha y categoría

### 2. Mejoras Futuras
- [ ] Implementar categorización manual
- [ ] Agregar códigos específicos en sistema de gestión
- [ ] Desarrollar reportes avanzados
- [ ] Integrar con dashboard existente

### 3. Optimizaciones
- [ ] Implementar cache para consultas frecuentes
- [ ] Agregar índices para mejor rendimiento
- [ ] Crear API para acceso externo
- [ ] Implementar exportación de datos

## 💡 RECOMENDACIONES FINALES

1. **Comenzar con implementación básica** del modelo y importación
2. **Revisar sistema de gestión** para agregar códigos de categoría
3. **Implementar categorización manual** para registros no identificados
4. **Desarrollar dashboard específico** para análisis de ventas
5. **Considerar integración** con el dashboard de gerente existente

---

*Análisis realizado el: $(date)*
*Archivo analizado: LIBRO IVA 07-2025.xlsx* 