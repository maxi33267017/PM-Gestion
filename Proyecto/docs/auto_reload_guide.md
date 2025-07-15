# Guía de Auto-Recarga (Auto-Reload)

## Descripción

El sistema de auto-reload permite que las páginas se recarguen automáticamente cada 10 minutos para mantener la información actualizada. Esto es especialmente útil para dashboards y páginas de monitoreo.

## Características

- **Recarga automática**: Cada 10 minutos
- **Advertencia previa**: 30 segundos antes de recargar
- **Posibilidad de cancelar**: El usuario puede cancelar la recarga
- **Pausa inteligente**: Se pausa cuando la página no está visible
- **Notificaciones visuales**: Alertas elegantes con Bootstrap Icons

## Uso

### 1. Auto-reload habilitado por defecto

El auto-reload está habilitado por defecto en todas las páginas que extienden de `base.html`. No se requiere configuración adicional.

### 2. Deshabilitar en páginas específicas

Para deshabilitar el auto-reload en una página específica:

```html
{% extends 'base.html' %}
{% load auto_reload %}

{% block content %}
    <!-- Contenido de la página -->
{% endblock %}

{% block extra_js %}
    <!-- Deshabilitar auto-reload -->
    {% disable_auto_reload %}
{% endblock %}
```

### 3. Habilitar explícitamente

Si necesitas habilitar el auto-reload explícitamente en una página:

```html
{% extends 'base.html' %}
{% load auto_reload %}

{% block content %}
    <!-- Contenido de la página -->
{% endblock %}

{% block extra_js %}
    <!-- El auto-reload ya está habilitado por defecto -->
    <!-- Puedes agregar comentarios o indicadores visuales -->
{% endblock %}
```

## Funcionalidades del Usuario

### Notificación de Recarga

30 segundos antes de la recarga, aparecerá una notificación en la esquina superior derecha:

- **Color**: Naranja (#f39c12)
- **Contenido**: Aviso de recarga automática
- **Botón**: "Cancelar" para detener la recarga

### Cancelar Auto-reload

El usuario puede cancelar la recarga de varias formas:

1. **Botón "Cancelar"** en la notificación
2. **Función JavaScript**: `cancelAutoReload()`
3. **Consola del navegador**: `window.autoReload.cancel()`

### Confirmación de Cancelación

Al cancelar, aparecerá una notificación verde confirmando que la auto-recarga ha sido cancelada.

## Comportamiento Inteligente

### Pausa cuando no está visible

El auto-reload se pausa automáticamente cuando:
- La pestaña del navegador no está activa
- La ventana del navegador está minimizada
- El usuario cambia a otra aplicación

### Reanudación automática

Cuando la página vuelve a estar visible, el auto-reload se reanuda automáticamente.

## Configuración

### Cambiar el intervalo de recarga

Para cambiar el intervalo de recarga, edita el archivo `static/js/auto-reload.js`:

```javascript
const RELOAD_INTERVAL = 10 * 60 * 1000; // 10 minutos
const WARNING_TIME = 30 * 1000; // 30 segundos de advertencia
```

### Intervalos sugeridos

- **Dashboards**: 5-10 minutos
- **Páginas de monitoreo**: 2-5 minutos
- **Páginas de configuración**: Deshabilitado
- **Formularios**: Deshabilitado

## Ejemplos de Uso

### Dashboard de Alertas (Auto-reload habilitado)

```html
{% extends 'base.html' %}
{% load auto_reload %}

{% block content %}
<div class="dashboard-header">
    <h1>Dashboard de Alertas</h1>
    <small>
        <i class="bi bi-arrow-clockwise"></i> 
        Esta página se actualiza automáticamente cada 10 minutos
    </small>
</div>
{% endblock %}
```

### Panel de Administración (Auto-reload deshabilitado)

```html
{% extends 'base.html' %}
{% load auto_reload %}

{% block content %}
<div class="admin-panel">
    <h1>Panel de Administración</h1>
    <!-- Contenido del panel -->
</div>
{% endblock %}

{% block extra_js %}
    {% disable_auto_reload %}
{% endblock %}
```

## Debugging

### Funciones disponibles en consola

```javascript
// Iniciar auto-reload manualmente
window.autoReload.start();

// Cancelar auto-reload
window.autoReload.cancel();

// Forzar recarga inmediata
window.autoReload.reload();
```

### Logs en consola

El sistema registra eventos importantes en la consola del navegador:
- "Auto-reload started. Page will reload in 10 minutes."
- "Auto-reloading page..."
- "Auto-reload cancelled"

## Consideraciones

### Rendimiento

- El auto-reload consume recursos mínimos
- Se pausa automáticamente cuando no es necesario
- No afecta el rendimiento de la aplicación

### Experiencia del usuario

- Las notificaciones son no intrusivas
- El usuario siempre puede cancelar
- La recarga es suave y rápida

### Compatibilidad

- Funciona en todos los navegadores modernos
- Compatible con Bootstrap Icons
- No requiere dependencias adicionales

## Troubleshooting

### El auto-reload no funciona

1. Verificar que el archivo `auto-reload.js` esté cargado
2. Revisar la consola del navegador para errores
3. Confirmar que no se haya deshabilitado con `{% disable_auto_reload %}`

### La página se recarga demasiado frecuentemente

1. Verificar el valor de `RELOAD_INTERVAL` en el script
2. Asegurar que no haya múltiples instancias del script

### Las notificaciones no aparecen

1. Verificar que Bootstrap Icons esté cargado
2. Revisar si hay conflictos de CSS
3. Confirmar que el z-index sea suficiente 