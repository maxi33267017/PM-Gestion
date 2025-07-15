#!/bin/bash

# Script para configurar la tarea programada de verificación de cronómetros activos
# Este script debe ejecutarse como root o con permisos de sudo

echo "Configurando tarea programada para verificación de cronómetros activos..."

# Obtener la ruta del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGE_PY="$PROJECT_DIR/manage.py"

# Verificar que manage.py existe
if [ ! -f "$MANAGE_PY" ]; then
    echo "Error: No se encontró manage.py en $PROJECT_DIR"
    exit 1
fi

# Crear el comando cron (ejecutar cada 30 minutos)
CRON_JOB="*/30 * * * * cd $PROJECT_DIR && python manage.py verificar_cronometros_activos >> /var/log/cronometros_alertas.log 2>&1"

# Agregar la tarea al crontab del usuario actual
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Tarea programada configurada exitosamente!"
echo "La verificación se ejecutará cada 30 minutos"
echo "Los logs se guardarán en /var/log/cronometros_alertas.log"
echo ""
echo "Para verificar que se configuró correctamente:"
echo "  crontab -l"
echo ""
echo "Para probar manualmente:"
echo "  cd $PROJECT_DIR && python manage.py verificar_cronometros_activos --dry-run"
echo ""
echo "Para desinstalar la tarea programada:"
echo "  crontab -e"
echo "  (eliminar la línea correspondiente)" 