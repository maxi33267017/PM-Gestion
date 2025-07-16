#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install -r Proyecto/requirements.txt

# Configurar variables de entorno para el build
export DJANGO_SETTINGS_MODULE=PatagoniaMaquinarias.settings_render
export DEBUG=False

# Cambiar al directorio del proyecto
cd Proyecto

# Verificar que Django puede iniciar
echo "Verificando configuración de Django..."
python -c "import django; django.setup(); print('✅ Django configurado correctamente')"

# Limpiar directorio de archivos estáticos si existe
echo "Limpiando directorio de archivos estáticos..."
rm -rf staticfiles/

# Recolectar archivos estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Verificar que los archivos se recolectaron correctamente
echo "Verificando archivos estáticos recolectados..."
ls -la staticfiles/ || echo "⚠️  Directorio staticfiles no encontrado"
ls -la staticfiles/css/ || echo "⚠️  Directorio css no encontrado" 