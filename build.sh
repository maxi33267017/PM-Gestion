#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno para el build
export DJANGO_SETTINGS_MODULE=Proyecto.PatagoniaMaquinarias.settings_render

# Recolectar archivos estáticos
python Proyecto/manage.py collectstatic --noinput

# Ejecutar migraciones
python Proyecto/manage.py migrate 