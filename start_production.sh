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
echo "SECRET_KEY: ${SECRET_KEY:0:20}..."

# Cambiar al directorio del proyecto
cd Proyecto

# Verificar que Django puede iniciar
echo "=== Verificando configuración de Django ==="
python -c "import django; django.setup(); print('✅ Django configurado correctamente')" || {
    echo "❌ Error en configuración de Django"
    exit 1
}

# Intentar migraciones (opcional)
echo "=== Intentando migraciones ==="
python manage.py migrate --noinput 2>/dev/null || echo "⚠️  Migraciones omitidas (puede ser normal en primera ejecución)"

# Iniciar la aplicación
echo "=== Iniciando aplicación ==="
exec gunicorn --bind 0.0.0.0:$PORT PatagoniaMaquinarias.wsgi:application --timeout 120 --workers 2 