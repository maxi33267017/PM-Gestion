# Sistema de Alertas de Cronómetros

Este documento describe el sistema de alertas implementado para monitorear cronómetros activos por largos períodos de tiempo.

## Características

- **Alertas automáticas**: Se envían cuando un cronómetro está activo por más de 2 horas
- **Notificaciones por email**: Al técnico y equipo de gestión central específico
- **Destinatarios fijos**: maxi.caamano@patagoniamaquinarias.com y repuestosrga@patagoniamaquinarias.com
- **Emails excluidos**: Gerentes y administrativos de sucursal (carolina.fiocchi, santiago.fiocchi, hector.gonzalez, administracion)
- **Dashboard de alertas**: Interfaz web para gestionar alertas
- **Tarea programada**: Verificación automática cada 30 minutos
- **Prevención de spam**: No se envían alertas duplicadas en un período de 2 horas

## Componentes

### 1. Modelo de Datos

- `AlertaCronometro`: Registra todas las alertas enviadas
- Campos: hora_tecnica, tipo_alerta, descripcion, fecha_creacion, enviada

### 2. Funciones de Utilidad

- `_obtener_destinatarios_alerta()`: Obtiene lista de destinatarios (técnico y emails corporativos específicos)
- `enviar_email()`: Envía el email de alerta a todos los destinatarios

### 3. Plantillas de Email

- `alerta_cronometro_tecnico.html`: Email para técnicos
- `alerta_cronometro_gerente.html`: Email para gerentes

### 4. Comando de Gestión

- `verificar_cronometros_activos`: Comando Django para verificar y enviar alertas
- Opción `--dry-run` para pruebas sin enviar emails

### 5. Dashboard Web

- Vista: `dashboard_alertas`
- URL: `/recursosHumanos/alertas/`
- Template: `dashboard_alertas.html`

## Configuración

### 1. Configuración de Email

Asegúrate de que las siguientes variables estén configuradas en tu entorno:

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_password_de_aplicacion
DEFAULT_FROM_EMAIL=tu_email@gmail.com
```

### 2. Configuración de Tarea Programada

#### Opción A: Usando el script automático

```bash
# Ejecutar como root o con sudo
sudo ./setup_cron.sh
```

#### Opción B: Configuración manual

```bash
# Editar crontab
crontab -e

# Agregar esta línea (ajustar la ruta según tu proyecto):
*/30 * * * * cd /ruta/a/tu/proyecto && python manage.py verificar_cronometros_activos >> /var/log/cronometros_alertas.log 2>&1
```

### 3. Configuración en Render.com

Para el despliegue en Render.com, agrega estas variables de entorno:

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_password_de_aplicacion
DEFAULT_FROM_EMAIL=tu_email@gmail.com
```

Y configura una tarea programada en Render.com:

```bash
# Comando para la tarea programada
python manage.py verificar_cronometros_activos

# Frecuencia: cada 30 minutos
```

## Uso

### 1. Pruebas Manuales

```bash
# Probar sin enviar emails
python manage.py verificar_cronometros_activos --dry-run

# Ejecutar realmente
python manage.py verificar_cronometros_activos
```

### 2. Acceso al Dashboard

- URL: `http://tu-dominio.com/recursosHumanos/alertas/`
- Solo accesible para gerentes y administradores
- Muestra todas las alertas activas y su estado

### 3. Verificación de Logs

```bash
# Ver logs de la tarea programada
tail -f /var/log/cronometros_alertas.log

# Ver logs de Django
tail -f /var/log/django.log
```

## Personalización

### 1. Cambiar el Tiempo de Alerta

Para cambiar el tiempo después del cual se envían las alertas (actualmente 2 horas):

1. Editar `verificar_cronometros_activos.py` línea 32:
   ```python
   tiempo_limite = timezone.now() - timedelta(hours=2)  # Cambiar 2 por el número deseado
   ```

2. Editar las plantillas de email para reflejar el nuevo tiempo

### 2. Cambiar la Frecuencia de Verificación

Para cambiar la frecuencia de verificación (actualmente cada 30 minutos):

1. Editar `setup_cron.sh` línea 20:
   ```bash
   CRON_JOB="*/30 * * * * ..."  # Cambiar */30 por la frecuencia deseada
   ```

2. En Render.com, cambiar la configuración de la tarea programada

### 3. Agregar Nuevos Tipos de Alerta

1. Agregar nuevas opciones en el modelo `AlertaCronometro.tipo_alerta`
2. Crear nuevas plantillas de email
3. Modificar la lógica en `verificar_cronometros_activos.py`

## Troubleshooting

### 1. Emails No Se Envían

- Verificar configuración de email en settings.py
- Verificar credenciales de Gmail
- Revisar logs de Django para errores de SMTP

### 2. Tarea Programada No Funciona

- Verificar que cron esté instalado y ejecutándose
- Verificar permisos del script
- Revisar logs en `/var/log/cronometros_alertas.log`

### 3. Alertas Duplicadas

- Verificar que no haya múltiples instancias del comando ejecutándose
- Revisar la lógica de prevención de duplicados en el código

## Seguridad

- Las alertas solo se envían a usuarios autenticados
- El dashboard solo es accesible para gerentes y administradores
- Los emails contienen enlaces seguros al sistema
- No se almacenan contraseñas en los logs

## Mantenimiento

### Limpieza de Alertas Antiguas

Para limpiar alertas antiguas (más de 30 días):

```python
# Comando Django personalizado
python manage.py shell
>>> from recursosHumanos.models import AlertaCronometro
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> AlertaCronometro.objects.filter(
...     fecha_creacion__lt=timezone.now() - timedelta(days=30)
... ).delete()
```

### Backup de Alertas

```bash
# Exportar alertas a JSON
python manage.py dumpdata recursosHumanos.AlertaCronometro --indent=2 > alertas_backup.json
``` 