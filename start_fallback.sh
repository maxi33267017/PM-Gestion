#!/usr/bin/env bash

# Configurar variables de entorno con valores por defecto
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-PatagoniaMaquinarias.settings_render}
export DEBUG=${DEBUG:-False}
export PORT=${PORT:-8000}

# Configurar variables de entorno para la base de datos
export DB_NAME="patagonia_81l3"
export DB_USER="patagonia"
export DB_PASSWORD="MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7"
export DB_HOST="dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com"
export DB_PORT="5432"

# Configurar SECRET_KEY si no está definida
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="django-insecure-rr%o!9z(2r-o&l-#ca0fddq38*583@b%m@+wfwgcvyyu)4_4k&"
    echo "SECRET_KEY configurada con valor por defecto"
fi

# Mostrar configuración
echo "=== Configuración de la aplicación ==="
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DEBUG: $DEBUG"
echo "PORT: $PORT"
echo "DB_HOST: $DB_HOST"
echo "DB_NAME: $DB_NAME"
echo "SECRET_KEY: ${SECRET_KEY:0:20}..."      # Mostrar solo los primeros 20 caracteres

# Cambiar al directorio del proyecto
cd Proyecto

# Ejecutar migraciones
echo "=== Ejecutando migraciones ==="
python manage.py migrate --noinput

# Iniciar la aplicación
echo "=== Iniciando aplicación ==="
exec gunicorn --bind 0.0.0.0:$PORT PatagoniaMaquinarias.wsgi:application 