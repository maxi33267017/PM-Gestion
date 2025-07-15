from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def auto_reload_script():
    """
    Template tag para incluir el script de auto-recarga.
    Uso: {% auto_reload_script %}
    """
    script_html = f'''
    <script src="{settings.STATIC_URL}js/auto-reload.js"></script>
    '''
    return mark_safe(script_html)

@register.simple_tag
def auto_reload_script_inline():
    """
    Template tag para incluir el script de auto-recarga inline.
    Uso: {% auto_reload_script_inline %}
    """
    script_html = '''
    <script>
    // Auto-reload script - Recarga la página cada 10 minutos
    (function() {
        'use strict';
        
        // Configuración
        const RELOAD_INTERVAL = 10 * 60 * 1000; // 10 minutos en milisegundos
        const WARNING_TIME = 30 * 1000; // 30 segundos antes de recargar
        
        let reloadTimer;
        let warningTimer;
        let isReloading = false;
        
        // Función para recargar la página
        function reloadPage() {
            if (!isReloading) {
                isReloading = true;
                console.log('Auto-reloading page...');
                window.location.reload();
            }
        }
        
        // Función para mostrar advertencia
        function showWarning() {
            // Crear notificación de advertencia
            const warningDiv = document.createElement('div');
            warningDiv.id = 'auto-reload-warning';
            warningDiv.innerHTML = `
                <div style="
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #f39c12;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 9999;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    max-width: 300px;
                    animation: slideIn 0.3s ease-out;
                ">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <i class="bi bi-clock" style="font-size: 18px;"></i>
                        <div>
                            <strong>Recarga automática</strong><br>
                            La página se recargará en 30 segundos
                        </div>
                    </div>
                    <button onclick="cancelAutoReload()" style="
                        background: rgba(255,255,255,0.2);
                        border: none;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 4px;
                        margin-top: 10px;
                        cursor: pointer;
                        font-size: 12px;
                    ">Cancelar</button>
                </div>
            `;
            
            // Agregar estilos CSS
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
            document.body.appendChild(warningDiv);
            
            // Remover la advertencia después de 30 segundos
            setTimeout(() => {
                const warning = document.getElementById('auto-reload-warning');
                if (warning) {
                    warning.remove();
                }
            }, 30000);
        }
        
        // Función para cancelar la auto-recarga
        window.cancelAutoReload = function() {
            if (reloadTimer) {
                clearTimeout(reloadTimer);
                reloadTimer = null;
            }
            if (warningTimer) {
                clearTimeout(warningTimer);
                warningTimer = null;
            }
            
            // Remover advertencia si existe
            const warning = document.getElementById('auto-reload-warning');
            if (warning) {
                warning.remove();
            }
            
            // Mostrar mensaje de cancelación
            const cancelDiv = document.createElement('div');
            cancelDiv.innerHTML = `
                <div style="
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #27ae60;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 9999;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    animation: slideIn 0.3s ease-out;
                ">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <i class="bi bi-check-circle" style="font-size: 18px;"></i>
                        <div>Auto-recarga cancelada</div>
                    </div>
                </div>
            `;
            document.body.appendChild(cancelDiv);
            
            // Remover mensaje después de 3 segundos
            setTimeout(() => {
                cancelDiv.remove();
            }, 3000);
            
            console.log('Auto-reload cancelled');
        };
        
        // Función para iniciar la auto-recarga
        function startAutoReload() {
            console.log('Auto-reload started. Page will reload in 10 minutes.');
            
            // Programar advertencia 30 segundos antes
            warningTimer = setTimeout(() => {
                showWarning();
            }, RELOAD_INTERVAL - WARNING_TIME);
            
            // Programar recarga
            reloadTimer = setTimeout(() => {
                reloadPage();
            }, RELOAD_INTERVAL);
        }
        
        // Iniciar auto-recarga cuando el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', startAutoReload);
        } else {
            startAutoReload();
        }
        
        // Pausar auto-recarga cuando la página no esté visible
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                // Pausar timers cuando la página no esté visible
                if (reloadTimer) {
                    clearTimeout(reloadTimer);
                    reloadTimer = null;
                }
                if (warningTimer) {
                    clearTimeout(warningTimer);
                    warningTimer = null;
                }
            } else {
                // Reanudar cuando la página vuelva a estar visible
                if (!reloadTimer && !isReloading) {
                    startAutoReload();
                }
            }
        });
        
        // Exponer funciones globalmente para debugging
        window.autoReload = {
            start: startAutoReload,
            cancel: window.cancelAutoReload,
            reload: reloadPage
        };
        
    })();
    </script>
    '''
    return mark_safe(script_html)

@register.simple_tag
def disable_auto_reload():
    """
    Template tag para deshabilitar el auto-reload en páginas específicas.
    Uso: {% disable_auto_reload %}
    """
    script_html = '''
    <script>
    // Deshabilitar auto-reload
    if (window.autoReload) {
        window.autoReload.cancel();
        console.log('Auto-reload disabled for this page');
    }
    </script>
    '''
    return mark_safe(script_html) 