#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno para el build
export DJANGO_SETTINGS_MODULE=PatagoniaMaquinarias.settings_render

# Cambiar al directorio del proyecto
cd Proyecto

# Recolectar archivos estáticos
python manage.py collectstatic --noinput 