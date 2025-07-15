"""
Tareas en segundo plano para procesamiento de importaciones
"""
import time
import threading
from django.db import transaction
from .models import Repuesto
from .parser_repuestos_jd_v2 import ParserRepuestosJDV2
import tempfile
import os

class ImportacionRepuestosTask:
    """Clase para manejar la importación de repuestos en segundo plano"""
    
    def __init__(self):
        self.resultado = {
            'success': False,
            'creados': 0,
            'actualizados': 0,
            'errores': 0,
            'total_parseados': 0,
            'error': None,
            'completado': False
        }
        self._thread = None
    
    def procesar_archivo(self, archivo_path, modo_importacion, categoria_default, proveedor_default, usuario, max_lineas=None):
        """Procesa el archivo en un hilo separado"""
        self._thread = threading.Thread(
            target=self._procesar_archivo_thread,
            args=(archivo_path, modo_importacion, categoria_default, proveedor_default, usuario, max_lineas)
        )
        self._thread.daemon = True
        self._thread.start()
        return self.resultado
    
    def _procesar_archivo_thread(self, archivo_path, modo_importacion, categoria_default, proveedor_default, usuario, max_lineas):
        """Método que se ejecuta en el hilo separado"""
        try:
            # Parsear el archivo
            parser = ParserRepuestosJDV2()
            repuestos_parseados, errores_parseo = parser.parse_archivo(archivo_path, max_lineas)
            
            if not repuestos_parseados:
                self.resultado['error'] = 'No se pudieron parsear repuestos del archivo'
                self.resultado['completado'] = True
                return
            
            self.resultado['total_parseados'] = len(repuestos_parseados)
            
            # Procesar repuestos en lotes muy pequeños
            creados = 0
            actualizados = 0
            errores = 0
            lote_size = 100  # Lotes más pequeños para evitar timeout
            
            # Dividir en lotes
            lotes = [repuestos_parseados[i:i + lote_size] for i in range(0, len(repuestos_parseados), lote_size)]
            
            for i, lote in enumerate(lotes):
                try:
                    with transaction.atomic():
                        for repuesto_data in lote:
                            try:
                                codigo = repuesto_data['codigo']
                                descripcion = repuesto_data['descripcion']
                                precio_lista = repuesto_data.get('precio_lista_decimal')
                                
                                if not codigo or not descripcion:
                                    errores += 1
                                    continue
                                
                                # Buscar si ya existe
                                repuesto_existente = Repuesto.objects.filter(codigo=codigo).first()
                                
                                if repuesto_existente:
                                    if modo_importacion in ['actualizar_existentes', 'crear_y_actualizar']:
                                        # Actualizar repuesto existente
                                        if precio_lista:
                                            repuesto_existente.precio_venta = precio_lista
                                        if categoria_default:
                                            repuesto_existente.categoria = categoria_default
                                        if proveedor_default:
                                            repuesto_existente.proveedor = proveedor_default
                                        repuesto_existente.save()
                                        actualizados += 1
                                else:
                                    if modo_importacion in ['crear_nuevos', 'crear_y_actualizar']:
                                        # Crear nuevo repuesto
                                        nuevo_repuesto = Repuesto(
                                            codigo=codigo,
                                            descripcion=descripcion,
                                            precio_venta=precio_lista or 0,
                                            categoria=categoria_default,
                                            proveedor=proveedor_default,
                                            creado_por=usuario
                                        )
                                        nuevo_repuesto.save()
                                        creados += 1
                                        
                            except Exception as e:
                                errores += 1
                                continue
                    
                    # Pausa entre lotes para no sobrecargar
                    time.sleep(0.05)
                    
                except Exception as e:
                    errores += len(lote)
                    continue
            
            # Actualizar resultado final
            self.resultado.update({
                'success': True,
                'creados': creados,
                'actualizados': actualizados,
                'errores': errores,
                'completado': True
            })
            
        except Exception as e:
            self.resultado.update({
                'error': str(e),
                'completado': True
            })
    
    def obtener_estado(self):
        """Retorna el estado actual de la tarea"""
        return self.resultado.copy()
    
    def esta_completada(self):
        """Verifica si la tarea está completada"""
        return self.resultado['completado']

# Diccionario global para almacenar tareas activas
tareas_activas = {}

def iniciar_importacion(archivo_path, modo_importacion, categoria_default, proveedor_default, usuario, max_lineas=None):
    """Inicia una nueva tarea de importación"""
    import uuid
    
    task_id = str(uuid.uuid4())
    tarea = ImportacionRepuestosTask()
    tarea.procesar_archivo(archivo_path, modo_importacion, categoria_default, proveedor_default, usuario, max_lineas)
    
    tareas_activas[task_id] = tarea
    return task_id

def obtener_estado_importacion(task_id):
    """Obtiene el estado de una tarea de importación"""
    if task_id not in tareas_activas:
        return None
    
    tarea = tareas_activas[task_id]
    estado = tarea.obtener_estado()
    
    # Si la tarea está completada, limpiarla después de un tiempo
    if tarea.esta_completada():
        # Programar limpieza después de 5 minutos
        def limpiar_tarea():
            time.sleep(300)  # 5 minutos
            if task_id in tareas_activas:
                del tareas_activas[task_id]
        
        cleanup_thread = threading.Thread(target=limpiar_tarea)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    return estado 