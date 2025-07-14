#!/usr/bin/env bash

# Configurar variables de entorno si no están definidas
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-Proyecto.PatagoniaMaquinarias.settings_render}
export DEBUG=${DEBUG:-False}
export PORT=${PORT:-8000}

# Mostrar variables de entorno para debugging (sin mostrar valores sensibles)
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DEBUG: $DEBUG"
echo "PORT: $PORT"
echo "DATABASE_URL está definida: $([ -n "$DATABASE_URL" ] && echo "SÍ" || echo "NO")"
echo "SECRET_KEY está definida: $([ -n "$SECRET_KEY" ] && echo "SÍ" || echo "NO")"

# Verificar que las variables críticas estén definidas
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL no está definida"
    echo "Variables de entorno disponibles:"
    env | grep -E "(DATABASE|SECRET|DJANGO)" || echo "No se encontraron variables relacionadas"
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo "Error: SECRET_KEY no está definida"
    exit 1
fi

# Ejecutar migraciones si es necesario
python Proyecto/manage.py migrate --noinput

# Iniciar la aplicación
exec gunicorn --bind 0.0.0.0:$PORT Proyecto.PatagoniaMaquinarias.wsgi:application 