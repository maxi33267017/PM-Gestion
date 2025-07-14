# Django loaddata - Sintaxis Correcta

## Problema
Cuando intentas usar `python manage.py loaddata` con archivos JSON, Django puede dar el error:
```
CommandError: No fixture named 'nombre_archivo' found.
```

## Solución

### Opción 1: Usar ruta completa (Recomendado)
```bash
# ✅ CORRECTO - Incluir la ruta completa y la extensión .json
python manage.py loaddata fixtures/01_provincias.json

# ✅ CORRECTO - Múltiples archivos
python manage.py loaddata fixtures/01_provincias.json fixtures/02_ciudades.json
```

### Opción 2: Mover archivos a directorio estándar
```bash
# Crear directorio fixtures (si no existe)
mkdir -p fixtures

# Copiar archivos
cp backups_20250714_174234/*.json fixtures/

# Usar solo el nombre sin extensión
python manage.py loaddata 01_provincias
```

### Opción 3: Usar script personalizado
```bash
# Usar el script que maneja las rutas automáticamente
python loaddata_simple.py
```

## ¿Por qué falla?

Django busca fixtures en:
1. Directorios `fixtures/` dentro de cada app
2. Directorio `fixtures/` en el proyecto raíz
3. Rutas especificadas en `FIXTURE_DIRS` en settings

Si el archivo no está en estos lugares, debes especificar la ruta completa.

## Ejemplos de Uso

### Cargar un solo archivo
```bash
python manage.py loaddata fixtures/01_provincias.json
```

### Cargar múltiples archivos en orden
```bash
python manage.py loaddata fixtures/01_provincias.json fixtures/02_ciudades.json fixtures/03_sucursales.json fixtures/04_usuarios.json
```

### Cargar todos los archivos de un directorio
```bash
# Primero copiar a fixtures/
cp backups_20250714_174234/*.json fixtures/

# Luego cargar
python manage.py loaddata 01_provincias 02_ciudades 03_sucursales 04_usuarios
```

## Scripts Disponibles

1. **`loaddata_simple.py`** - Script simple que usa rutas completas
2. **`cargar_datos_loaddata.py`** - Script más complejo con manejo de errores

## Notas Importantes

- Siempre usar `DJANGO_SETTINGS_MODULE=PatagoniaMaquinarias.settings_render` en producción
- Los archivos deben estar en formato JSON válido de Django
- El orden de carga es importante para mantener las relaciones entre modelos 