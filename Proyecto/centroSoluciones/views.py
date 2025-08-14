from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import AlertaEquipo, LeadJohnDeere, AsignacionAlerta, CodigoAlerta
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario, Sucursal
from crm.models import EmbudoVentas, ContactoCliente
import os

# Create your views here.

def limpiar_valor_numerico(valor):
    """Convertir valores NaN a None para campos DecimalField"""
    import math
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    return valor

def procesar_datos_utilizacion(archivo, df):
    """Procesar datos de utilización del archivo Analizador_de_máquina"""
    from .models import DatosUtilizacionMensual
    from clientes.models import Equipo
    from datetime import datetime
    from django.utils import timezone
    
    print(f"DEBUG: Procesando archivo {archivo.nombre_archivo}")
    print(f"DEBUG: Columnas disponibles: {list(df.columns)}")
    print(f"DEBUG: Primera fila: {df.iloc[0].to_dict()}")
    
    registros_procesados = 0
    
    for index, row in df.iterrows():
        try:
            # Extraer datos básicos - usar nombres exactos de columnas
            maquina = row.get('Máquina', '')
            modelo = row.get('Modelo', '')
            tipo = row.get('Tipo', '')
            numero_serie = row.get('Número de serie de la máquina', '')
            organizacion = row.get('Organización', '')
            identificador_org = str(row.get('Identificador de organización', ''))
            
            # Procesar fechas
            fecha_inicio_str = row.get('Fecha de inicio', '')
            fecha_fin_str = row.get('Fecha de terminación', '')
            
            fecha_inicio = None
            fecha_fin = None
            
            if fecha_inicio_str and str(fecha_inicio_str) != 'nan':
                try:
                    fecha_inicio = datetime.strptime(str(fecha_inicio_str).split()[0], '%d/%m/%Y').date()
                except:
                    pass
            
            if fecha_fin_str and str(fecha_fin_str) != 'nan':
                try:
                    fecha_fin = datetime.strptime(str(fecha_fin_str).split()[0], '%d/%m/%Y').date()
                except:
                    pass
            
            # Buscar equipo por número de serie
            equipo = None
            if numero_serie and str(numero_serie) != 'nan':
                try:
                    equipo = Equipo.objects.get(numero_serie=numero_serie)
                except Equipo.DoesNotExist:
                    pass
            
            # Crear registro de datos de utilización
            datos_utilizacion = DatosUtilizacionMensual(
                archivo=archivo,
                equipo=equipo,
                maquina=maquina,
                modelo=modelo,
                tipo=tipo,
                numero_serie=numero_serie,
                organizacion=organizacion,
                identificador_organizacion=identificador_org,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                
                # Datos de combustible
                combustible_consumido_periodo=limpiar_valor_numerico(row.get('Combustible consumido Período (l)', 0)),
                consumo_promedio_periodo=limpiar_valor_numerico(row.get('Consumo promedio de combustible Período (l/h)', 0)),
                combustible_funcionamiento=limpiar_valor_numerico(row.get('Combustible en funcionamiento Período (l)', 0)),
                combustible_ralenti=limpiar_valor_numerico(row.get('Combustible en ralentí Período (l)', 0)),
                
                # Datos de motor
                horas_trabajo_motor_periodo=limpiar_valor_numerico(row.get('Horas de trabajo del motor Período (h)', 0)),
                horas_trabajo_motor_vida_util=limpiar_valor_numerico(row.get('Horas de trabajo del motor Vida útil (h)', 0)),
                
                # Datos de temperatura
                temp_max_aceite_transmision=limpiar_valor_numerico(row.get('Temperatura máxima de aceite de transmisión Período (°C)', 0)),
                temp_max_aceite_hidraulico=limpiar_valor_numerico(row.get('Temperatura máxima de aceite hidráulico Período (°C)', 0)),
                temp_max_refrigerante=limpiar_valor_numerico(row.get('Temperatura máxima de refrigerante Período (°C)', 0)),
                
                # Datos de modo ECO
                modo_eco_activado_porcentaje=limpiar_valor_numerico(row.get('Modo ECO Activado (%)', 0)),
                modo_eco_activado_horas=limpiar_valor_numerico(row.get('Modo ECO Activado (h)', 0)),
                modo_eco_desactivado_horas=limpiar_valor_numerico(row.get('Modo ECO Desactivado (h)', 0)),
                
                # Datos de utilización (C&F)
                utilizacion_alta_horas=limpiar_valor_numerico(row.get('Utilización (C&F) Alta (h)', 0)),
                utilizacion_media_horas=limpiar_valor_numerico(row.get('Utilización (C&F) Media (h)', 0)),
                utilizacion_baja_horas=limpiar_valor_numerico(row.get('Utilización (C&F) Baja (h)', 0)),
                utilizacion_ralenti_horas=limpiar_valor_numerico(row.get('Utilización (C&F) Ralentí (h)', 0)),
                
                # Datos de tiempo en marcha
                tiempo_avan_1=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 1 (h)', 0)),
                tiempo_avan_2=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 2 (h)', 0)),
                tiempo_avan_3=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 3 (h)', 0)),
                tiempo_avan_4=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 4 (h)', 0)),
                tiempo_avan_5=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 5 (h)', 0)),
                tiempo_avan_6=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 6 (h)', 0)),
                tiempo_avan_7=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 7 (h)', 0)),
                tiempo_avan_8=limpiar_valor_numerico(row.get('Tiempo en marcha Avan 8 (h)', 0)),
                tiempo_estacionamiento=limpiar_valor_numerico(row.get('Tiempo en marcha Estacionamiento (h)', 0)),
                tiempo_punto_muerto=limpiar_valor_numerico(row.get('Tiempo en marcha Punto muerto (h)', 0)),
                tiempo_ret_1=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 1 (h)', 0)),
                tiempo_ret_2=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 2 (h)', 0)),
                tiempo_ret_3=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 3 (h)', 0)),
                tiempo_ret_4=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 4 (h)', 0)),
                tiempo_ret_5=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 5 (h)', 0)),
                tiempo_ret_6=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 6 (h)', 0)),
                tiempo_ret_7=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 7 (h)', 0)),
                tiempo_ret_8=limpiar_valor_numerico(row.get('Tiempo en marcha Ret 8 (h)', 0)),
                
                # Datos adicionales
                nivel_tanque_combustible=limpiar_valor_numerico(row.get('Nivel del tanque de combustible (%)', 0)),
                odometro_vida_util=limpiar_valor_numerico(row.get('Odómetro Vida útil (km)', 0)),
                ano_modelo=limpiar_valor_numerico(row.get('Año del modelo', '')),
                estado_maquina=row.get('Estado de máquina', ''),
                ultima_latitud=limpiar_valor_numerico(row.get('Última latitud conocida', 0)),
                ultima_longitud=limpiar_valor_numerico(row.get('Última longitud conocida', 0)),
                
                # Datos originales
                datos_originales=row.to_dict()
            )
            
            datos_utilizacion.save()
            registros_procesados += 1
            
            if registros_procesados % 50 == 0:
                print(f"DEBUG: Procesados {registros_procesados} registros...")
            
        except Exception as e:
            print(f"ERROR procesando fila {index}: {str(e)}")
            continue
    
    print(f"DEBUG: Total registros procesados: {registros_procesados}")
    
    # Actualizar archivo
    archivo.total_registros = len(df)
    archivo.registros_procesados = registros_procesados
    archivo.periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}" if fecha_inicio and fecha_fin else ""
    archivo.log_procesamiento = f"Procesados {registros_procesados} de {len(df)} registros"
    archivo.save()

def procesar_archivo_excel(archivo_id):
    """Procesar archivo Excel en segundo plano"""
    from .models import ArchivoDatosMensual, DatosUtilizacionMensual, NotificacionMensual
    from clientes.models import Equipo
    import pandas as pd
    from datetime import datetime
    import traceback
    
    print(f"DEBUG: Iniciando procesamiento del archivo ID: {archivo_id}")
    
    try:
        archivo = ArchivoDatosMensual.objects.get(id=archivo_id)
        print(f"DEBUG: Archivo encontrado: {archivo.nombre_archivo}")
        print(f"DEBUG: Tipo: {archivo.tipo}")
        print(f"DEBUG: Estado actual: {archivo.estado}")
        
        archivo.estado = 'PROCESANDO'
        archivo.save()
        print(f"DEBUG: Estado cambiado a PROCESANDO")
        
        print(f"DEBUG: Ruta del archivo: {archivo.archivo.path}")
        print(f"DEBUG: Archivo existe: {os.path.exists(archivo.archivo.path)}")
        
        # Leer el archivo Excel
        print(f"DEBUG: Leyendo archivo Excel...")
        df = pd.read_excel(archivo.archivo.path)
        print(f"DEBUG: Archivo leído exitosamente")
        print(f"DEBUG: Dimensiones del DataFrame: {df.shape}")
        print(f"DEBUG: Columnas: {list(df.columns)}")
        
        if archivo.tipo == 'UTILIZACION':
            print(f"DEBUG: Procesando como UTILIZACION")
            procesar_datos_utilizacion(archivo, df)
        elif archivo.tipo == 'NOTIFICACIONES':
            print(f"DEBUG: Procesando como NOTIFICACIONES")
            procesar_notificaciones(archivo, df)
        else:
            print(f"ERROR: Tipo de archivo no reconocido: {archivo.tipo}")
            raise Exception(f"Tipo de archivo no reconocido: {archivo.tipo}")
        
        archivo.estado = 'COMPLETADO'
        archivo.fecha_procesamiento = timezone.now()
        archivo.save()
        
        print(f"DEBUG: Archivo procesado exitosamente: {archivo.nombre_archivo}")
        
    except Exception as e:
        print(f"ERROR procesando archivo {archivo_id}: {str(e)}")
        print(f"ERROR traceback: {traceback.format_exc()}")
        
        try:
            archivo = ArchivoDatosMensual.objects.get(id=archivo_id)
            archivo.estado = 'ERROR'
            archivo.errores = f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            archivo.save()
            print(f"DEBUG: Estado cambiado a ERROR")
        except Exception as save_error:
            print(f"ERROR guardando estado de error: {str(save_error)}")

def procesar_notificaciones(archivo, df):
    """Procesar notificaciones del archivo Notificaciones"""
    from .models import NotificacionMensual
    from clientes.models import Equipo
    from datetime import datetime
    
    registros_procesados = 0
    
    for index, row in df.iterrows():
        try:
            # Extraer datos básicos
            nombre_organizacion = row.get('Nombre de organización', '')
            nombre = row.get('Nombre', '')
            pin_maquina = row.get('PIN de máquina', '')
            marca_maquina = row.get('Marca de máquina', '')
            tipo_maquina = row.get('Tipo de máquina', '')
            modelo_maquina = row.get('Modelo de máquina', '')
            
            # Procesar fecha y hora
            fecha_str = row.get('Fecha', '')
            codigo_hora_str = row.get('Código de hora', '')
            
            fecha = None
            codigo_hora = None
            
            if fecha_str and str(fecha_str) != 'nan':
                try:
                    fecha = datetime.strptime(str(fecha_str), '%Y/%m/%d').date()
                except:
                    pass
            
            if codigo_hora_str and str(codigo_hora_str) != 'nan':
                try:
                    codigo_hora = datetime.strptime(str(codigo_hora_str), '%H:%M:%S').time()
                except:
                    pass
            
            # Buscar equipo por PIN
            equipo = None
            if pin_maquina and str(pin_maquina) != 'nan':
                try:
                    equipo = Equipo.objects.get(numero_serie=pin_maquina)
                except Equipo.DoesNotExist:
                    pass
            
            # Crear registro de notificación
            notificacion = NotificacionMensual(
                archivo=archivo,
                equipo=equipo,
                nombre_organizacion=nombre_organizacion,
                nombre=nombre,
                fecha=fecha,
                codigo_hora=codigo_hora,
                pin_maquina=pin_maquina,
                marca_maquina=marca_maquina,
                tipo_maquina=tipo_maquina,
                modelo_maquina=modelo_maquina,
                severidad=row.get('Severidad', ''),
                categoria=row.get('Categoría', ''),
                codigos_diagnostico=row.get('Códigos de diagnóstico', ''),
                descripcion=row.get('Descripción', ''),
                texto=row.get('Texto', ''),
                latitud=limpiar_valor_numerico(row.get('Latitud', 0)),
                longitud=limpiar_valor_numerico(row.get('Longitud', 0)),
                incidencias=row.get('Incidencias', ''),
                duracion=row.get('Duración', ''),
                horas_trabajo_motor=limpiar_valor_numerico(row.get('Horas de trabajo del motor', 0)),
                resuelta=False,
                datos_originales=row.to_dict()
            )
            
            notificacion.save()
            registros_procesados += 1
            
        except Exception as e:
            print(f"ERROR procesando notificación fila {index}: {str(e)}")
            continue
    
    # Actualizar archivo
    archivo.total_registros = len(df)
    archivo.registros_procesados = registros_procesados
    archivo.log_procesamiento = f"Procesadas {registros_procesados} de {len(df)} notificaciones"
    archivo.save()

@login_required
def dashboard(request):
    """Vista principal del Centro de Soluciones Conectadas"""
    from .models import ArchivoDatosMensual
    
    # Obtener estadísticas según el rol del usuario
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        # Para gerentes/administrativos: ver todas las alertas de su sucursal
        alertas_pendientes = AlertaEquipo.objects.filter(
            estado='PENDIENTE',
            sucursal=request.user.sucursal
        ).count()
        alertas_asignadas = AlertaEquipo.objects.filter(
            estado__in=['ASIGNADA', 'EN_PROCESO'],
            sucursal=request.user.sucursal
        ).count()
        leads_nuevos = LeadJohnDeere.objects.filter(
            estado='NUEVO',
            sucursal=request.user.sucursal
        ).count()
    else:
        # Para técnicos: ver solo sus alertas asignadas
        alertas_pendientes = AlertaEquipo.objects.filter(
            tecnico_asignado=request.user,
            estado='ASIGNADA'
        ).count()
        alertas_asignadas = AlertaEquipo.objects.filter(
            tecnico_asignado=request.user,
            estado='EN_PROCESO'
        ).count()
        leads_nuevos = 0  # Los técnicos no ven leads
    
    # Estadísticas de archivos mensuales
    total_archivos_mensuales = ArchivoDatosMensual.objects.count()
    
    context = {
        'alertas_pendientes': alertas_pendientes,
        'alertas_asignadas': alertas_asignadas,
        'leads_nuevos': leads_nuevos,
        'total_archivos_mensuales': total_archivos_mensuales,
    }
    
    return render(request, 'centroSoluciones/dashboard.html', context)

@login_required
def alertas_list(request):
    """Lista de alertas con filtros según el rol del usuario"""
    
    # Filtrar alertas según el rol
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        # Gerentes/Administrativos ven todas las alertas de su sucursal
        alertas = AlertaEquipo.objects.filter(sucursal=request.user.sucursal)
    else:
        # Técnicos ven solo sus alertas asignadas
        alertas = AlertaEquipo.objects.filter(tecnico_asignado=request.user)
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    clasificacion = request.GET.get('clasificacion')
    search = request.GET.get('search')
    
    if estado:
        # Manejar múltiples estados separados por comas
        estados = [e.strip() for e in estado.split(',')]
        if len(estados) == 1:
            alertas = alertas.filter(estado=estado)
        else:
            alertas = alertas.filter(estado__in=estados)
    if clasificacion:
        alertas = alertas.filter(clasificacion=clasificacion)
    if search:
        alertas = alertas.filter(
            Q(cliente__razon_social__icontains=search) |
            Q(pin_equipo__icontains=search) |
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Ordenar por fecha (más recientes primero)
    alertas = alertas.order_by('-fecha')
    
    # Paginación
    paginator = Paginator(alertas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filtro': estado,
        'clasificacion_filtro': clasificacion,
        'search_filtro': search,
        'es_admin': request.user.rol in ['GERENTE', 'ADMINISTRATIVO'],
    }
    
    return render(request, 'centroSoluciones/alertas_list.html', context)

@login_required
def alerta_detail(request, alerta_id):
    """Detalle de una alerta específica"""
    
    # Obtener la alerta
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, sucursal=request.user.sucursal)
    else:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, tecnico_asignado=request.user)
    
    # Calcular horas para los tiempos
    tiempo_pendiente_horas = 0
    tiempo_resolucion_horas = 0
    
    if alerta.tiempo_pendiente:
        tiempo_pendiente_horas = round(alerta.tiempo_pendiente.seconds / 3600, 1)
    
    if alerta.tiempo_resolucion:
        tiempo_resolucion_horas = round(alerta.tiempo_resolucion.seconds / 3600, 1)
    
    context = {
        'alerta': alerta,
        'es_admin': request.user.rol in ['GERENTE', 'ADMINISTRATIVO'],
        'tiempo_pendiente_horas': tiempo_pendiente_horas,
        'tiempo_resolucion_horas': tiempo_resolucion_horas,
    }
    
    return render(request, 'centroSoluciones/alerta_detail.html', context)

@login_required
def procesar_alerta(request, alerta_id):
    """Vista para que los técnicos y gerentes procesen alertas con conexión SAR y oportunidades CRM"""
    
    if request.user.rol not in ['TECNICO', 'GERENTE']:
        messages.error(request, 'Solo los técnicos y gerentes pueden procesar alertas.')
        return redirect('centroSoluciones:alertas_list')
    
    # Los técnicos solo pueden procesar sus alertas asignadas, los gerentes pueden procesar cualquier alerta
    if request.user.rol == 'TECNICO':
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, tecnico_asignado=request.user)
    else:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id)
    
    if request.method == 'POST':
        # Procesar el formulario
        estado = request.POST.get('estado')
        observaciones = request.POST.get('observaciones_tecnico')
        conexion_sar_realizada = request.POST.get('conexion_sar_realizada') == 'on'
        resultado_conexion_sar = request.POST.get('resultado_conexion_sar', '')
        crear_oportunidad = request.POST.get('crear_oportunidad') == 'on'
        tipo_oportunidad = request.POST.get('tipo_oportunidad', '')
        descripcion_oportunidad = request.POST.get('descripcion_oportunidad', '')
        valor_estimado = request.POST.get('valor_estimado', '')
        
        # Actualizar alerta
        alerta.estado = estado
        alerta.observaciones_tecnico = observaciones
        alerta.conexion_sar_realizada = conexion_sar_realizada
        alerta.resultado_conexion_sar = resultado_conexion_sar
        
        # Crear oportunidad CRM si se solicita
        if crear_oportunidad and tipo_oportunidad and descripcion_oportunidad:
            try:
                # Crear embudo de ventas
                embudo = EmbudoVentas.objects.create(
                    cliente=alerta.cliente,
                    etapa='CONTACTO_INICIAL',
                    valor_estimado=float(valor_estimado) if valor_estimado else None,
                    origen='ALERTA_EQUIPO',
                    alerta_equipo=alerta,
                    descripcion_negocio=descripcion_oportunidad,
                    observaciones=f"Oportunidad creada desde alerta {alerta.codigo}. Tipo: {tipo_oportunidad}",
                    creado_por=request.user
                )
                
                # Crear contacto inicial
                ContactoCliente.objects.create(
                    cliente=alerta.cliente,
                    tipo_contacto='VISITA',
                    descripcion=f"Contacto inicial por alerta {alerta.codigo}. {descripcion_oportunidad}",
                    resultado='EXITOSO',
                    observaciones=f"Técnico realizó conexión SAR y identificó oportunidad de {tipo_oportunidad}",
                    responsable=request.user,
                    embudo_ventas=embudo
                )
                
                alerta.oportunidad_crm_creada = True
                messages.success(request, f'Oportunidad CRM creada exitosamente para {tipo_oportunidad}.')
                
            except Exception as e:
                messages.error(request, f'Error al crear oportunidad CRM: {str(e)}')
        
        alerta.save()
        
        messages.success(request, f'Alerta {alerta.codigo} procesada correctamente.')
        return redirect('centroSoluciones:alerta_detail', alerta_id=alerta.id)
    
    # Calcular horas del tiempo pendiente para el template
    tiempo_pendiente_seconds_hours = 0
    if alerta.tiempo_pendiente:
        tiempo_pendiente_seconds_hours = int(alerta.tiempo_pendiente.total_seconds() // 3600)
    
    context = {
        'alerta': alerta,
        'alerta_tiempo_pendiente_seconds_hours': tiempo_pendiente_seconds_hours,
    }
    
    return render(request, 'centroSoluciones/procesar_alerta.html', context)

@login_required
@require_http_methods(["POST"])
def crear_alerta(request):
    """Vista para crear una nueva alerta desde un modal"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear alertas'})
    
    try:
        # Obtener datos del formulario
        cliente_id = request.POST.get('cliente')
        pin_equipo = request.POST.get('pin_equipo')
        clasificacion = request.POST.get('clasificacion')
        codigo = request.POST.get('codigo')
        descripcion = request.POST.get('descripcion')
        tecnico_id = request.POST.get('tecnico_asignado')
        
        # Validar datos requeridos
        if not all([cliente_id, pin_equipo, clasificacion, codigo, descripcion]):
            return JsonResponse({'success': False, 'message': 'Todos los campos son obligatorios'})
        
        # Obtener objetos relacionados
        cliente = get_object_or_404(Cliente, id=cliente_id)
        tecnico = None
        if tecnico_id:
            tecnico = get_object_or_404(Usuario, id=tecnico_id, rol='TECNICO')
        
        # Crear la alerta
        alerta = AlertaEquipo.objects.create(
            cliente=cliente,
            pin_equipo=pin_equipo,
            clasificacion=clasificacion,
            codigo=codigo,
            descripcion=descripcion,
            sucursal=request.user.sucursal,
            tecnico_asignado=tecnico,
            creado_por=request.user
        )
        
        # Si se asignó un técnico, actualizar estado
        if tecnico:
            alerta.estado = 'ASIGNADA'
            alerta.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Alerta {alerta.codigo} creada exitosamente',
            'alerta_id': alerta.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al crear la alerta: {str(e)}'})

@login_required
@require_http_methods(["POST"])
def crear_lead(request):
    """Vista para crear un nuevo lead desde un modal"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear leads'})
    
    try:
        # Obtener datos del formulario
        cliente_id = request.POST.get('cliente')
        equipo_id = request.POST.get('equipo')
        clasificacion = request.POST.get('clasificacion')
        descripcion = request.POST.get('descripcion')
        valor_estimado = request.POST.get('valor_estimado')
        
        # Validar datos requeridos
        if not all([cliente_id, equipo_id, clasificacion, descripcion]):
            return JsonResponse({'success': False, 'message': 'Todos los campos son obligatorios'})
        
        # Obtener objetos relacionados
        cliente = get_object_or_404(Cliente, id=cliente_id)
        equipo = get_object_or_404(Equipo, id=equipo_id)
        
        # Convertir valor estimado
        valor = None
        if valor_estimado:
            try:
                valor = float(valor_estimado)
            except ValueError:
                return JsonResponse({'success': False, 'message': 'El valor estimado debe ser un número válido'})
        
        # Crear el lead
        lead = LeadJohnDeere.objects.create(
            cliente=cliente,
            equipo=equipo,
            clasificacion=clasificacion,
            descripcion=descripcion,
            valor_estimado=valor,
            sucursal=request.user.sucursal,
            creado_por=request.user
        )
        
        # Crear embudo de ventas automáticamente
        try:
            embudo = EmbudoVentas.objects.create(
                cliente=cliente,
                etapa='CONTACTO_INICIAL',
                origen='LEAD_JD',
                valor_estimado=valor,
                # Sin probabilidad de cierre
                descripcion_negocio=f"Lead John Deere: {descripcion}",
                observaciones=f"Lead creado automáticamente desde Centro de Soluciones. Clasificación: {dict(LeadJohnDeere.CLASIFICACION_CHOICES)[clasificacion]}",
                lead_jd=lead,
                creado_por=request.user
            )
            
            # Crear contacto inicial automático
            ContactoCliente.objects.create(
                cliente=cliente,
                tipo_contacto='VISITA',
                descripcion=f"Lead John Deere recibido: {descripcion}",
                resultado='EXITOSO',
                observaciones=f"Lead automático creado desde Centro de Soluciones. Equipo: {equipo.numero_serie}",
                responsable=request.user,
                embudo_ventas=embudo
            )
            
        except Exception as e:
            # Si falla la creación del embudo, no fallar el lead
            print(f"Error al crear embudo de ventas: {str(e)}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Lead creado exitosamente para {cliente.razon_social}',
            'lead_id': lead.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al crear el lead: {str(e)}'})

@login_required
def obtener_equipos_cliente(request):
    """Vista para obtener equipos de un cliente específico (AJAX)"""
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse({'success': False, 'message': 'ID de cliente requerido'})
    
    try:
        equipos = Equipo.objects.filter(cliente_id=cliente_id).values('id', 'numero_serie', 'modelo__nombre')
        return JsonResponse({
            'success': True,
            'equipos': list(equipos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener equipos: {str(e)}'})

@login_required
def obtener_pins_equipos_cliente(request):
    """Vista para obtener PINs de equipos de un cliente específico (AJAX)"""
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse({'success': False, 'message': 'ID de cliente requerido'})
    
    try:
        equipos = Equipo.objects.filter(cliente_id=cliente_id).values('numero_serie')
        pins = [{'pin': equipo['numero_serie']} for equipo in equipos]
        return JsonResponse({
            'success': True,
            'pins': pins
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener PINs: {str(e)}'})

@login_required
def obtener_tecnicos(request):
    """Vista para obtener técnicos disponibles (AJAX)"""
    try:
        tecnicos = Usuario.objects.filter(
            rol='TECNICO',
            sucursal=request.user.sucursal,
            is_active=True
        ).values('id', 'first_name', 'last_name')
        return JsonResponse({
            'success': True,
            'tecnicos': list(tecnicos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener técnicos: {str(e)}'})

@login_required
def obtener_clientes(request):
    """Vista para obtener clientes disponibles (AJAX)"""
    try:
        clientes = Cliente.objects.filter(
            sucursal=request.user.sucursal
        ).values('id', 'razon_social', 'cuit')
        return JsonResponse({
            'success': True,
            'clientes': list(clientes)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener clientes: {str(e)}'})

@login_required
def leads_list(request):
    """Lista de leads con filtros según el rol del usuario"""
    
    # Solo gerentes y administrativos pueden ver leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para ver leads.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Filtrar leads por sucursal
    leads = LeadJohnDeere.objects.filter(sucursal=request.user.sucursal)
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    clasificacion = request.GET.get('clasificacion')
    search = request.GET.get('search')
    
    if estado:
        leads = leads.filter(estado=estado)
    if clasificacion:
        leads = leads.filter(clasificacion=clasificacion)
    if search:
        leads = leads.filter(
            Q(cliente__razon_social__icontains=search) |
            Q(equipo__numero_serie__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Ordenar por fecha (más recientes primero)
    leads = leads.order_by('-fecha')
    
    # Paginación
    paginator = Paginator(leads, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filtro': estado,
        'clasificacion_filtro': clasificacion,
        'search_filtro': search,
    }
    
    return render(request, 'centroSoluciones/leads_list.html', context)

@login_required
def lead_detail(request, lead_id):
    """Detalle de un lead específico"""
    
    # Solo gerentes y administrativos pueden ver leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para ver leads.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Obtener el lead
    lead = get_object_or_404(LeadJohnDeere, id=lead_id, sucursal=request.user.sucursal)
    
    # Obtener embudo de ventas asociado
    embudo = None
    try:
        embudo = EmbudoVentas.objects.filter(lead_jd=lead).first()
    except:
        pass
    
    context = {
        'lead': lead,
        'embudo': embudo,
    }
    
    return render(request, 'centroSoluciones/lead_detail.html', context)

@login_required
def lead_edit(request, lead_id):
    """Vista para editar un lead"""
    
    # Solo gerentes y administrativos pueden editar leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para editar leads.')
        return redirect('centroSoluciones:leads_list')
    
    # Obtener el lead
    lead = get_object_or_404(LeadJohnDeere, id=lead_id, sucursal=request.user.sucursal)
    
    if request.method == 'POST':
        # Procesar el formulario
        estado = request.POST.get('estado')
        clasificacion = request.POST.get('clasificacion')
        descripcion = request.POST.get('descripcion')
        observaciones_contacto = request.POST.get('observaciones_contacto', '')
        valor_estimado = request.POST.get('valor_estimado', '')
        
        # Actualizar lead
        lead.estado = estado
        lead.clasificacion = clasificacion
        lead.descripcion = descripcion
        lead.observaciones_contacto = observaciones_contacto
        
        # Convertir valor estimado
        if valor_estimado:
            try:
                lead.valor_estimado = float(valor_estimado)
            except ValueError:
                messages.error(request, 'El valor estimado debe ser un número válido.')
                return redirect('centroSoluciones:lead_edit', lead_id=lead.id)
        else:
            lead.valor_estimado = None
        
        lead.save()
        
        # Actualizar embudo de ventas asociado si existe
        try:
            embudo = EmbudoVentas.objects.filter(lead_jd=lead).first()
            if embudo:
                embudo.valor_estimado = lead.valor_estimado
                embudo.descripcion_negocio = f"Lead John Deere: {lead.descripcion}"
                embudo.observaciones = f"Lead actualizado desde Centro de Soluciones. Clasificación: {lead.get_clasificacion_display()}"
                embudo.save()
        except Exception as e:
            print(f"Error al actualizar embudo de ventas: {str(e)}")
        
        messages.success(request, f'Lead actualizado correctamente.')
        return redirect('centroSoluciones:lead_detail', lead_id=lead.id)
    
    context = {
        'lead': lead,
    }
    
    return render(request, 'centroSoluciones/lead_edit.html', context)

@login_required
def obtener_codigo_alerta(request):
    """Vista para obtener información de un código de alerta específico (AJAX)"""
    codigo = request.GET.get('codigo')
    modelo_equipo = request.GET.get('modelo_equipo')
    
    if not codigo:
        return JsonResponse({'success': False, 'message': 'Código de alerta requerido'})
    
    try:
        # Buscar el código de alerta
        codigo_alerta = CodigoAlerta.objects.filter(
            codigo=codigo,
            activo=True
        ).first()
        
        if codigo_alerta:
            # Si se especifica modelo, verificar que coincida
            if modelo_equipo and codigo_alerta.modelo_equipo != modelo_equipo:
                # Buscar una versión específica para ese modelo
                codigo_especifico = CodigoAlerta.objects.filter(
                    codigo=codigo,
                    modelo_equipo=modelo_equipo,
                    activo=True
                ).first()
                if codigo_especifico:
                    codigo_alerta = codigo_especifico
            
            return JsonResponse({
                'success': True,
                'codigo_alerta': {
                    'codigo': codigo_alerta.codigo,
                    'modelo_equipo': codigo_alerta.modelo_equipo,
                    'descripcion': codigo_alerta.descripcion,
                    'clasificacion': codigo_alerta.clasificacion,
                    'instrucciones_resolucion': codigo_alerta.instrucciones_resolucion,
                    'repuestos_comunes': codigo_alerta.repuestos_comunes,
                    'tiempo_estimado_resolucion': codigo_alerta.tiempo_estimado_resolucion,
                }
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': f'Código de alerta {codigo} no encontrado en la base de datos'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al buscar código de alerta: {str(e)}'})

@login_required
def obtener_modelos_equipos(request):
    """Vista para obtener modelos de equipos disponibles (AJAX)"""
    try:
        from clientes.models import ModeloEquipo
        modelos = ModeloEquipo.objects.values('id', 'nombre').order_by('nombre')
        return JsonResponse({
            'success': True,
            'modelos': list(modelos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener modelos: {str(e)}'})

@login_required
def gestionar_codigos_alerta(request):
    """Vista para gestionar códigos de alerta"""
    
    # Solo gerentes y administrativos pueden gestionar códigos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para gestionar códigos de alerta.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Obtener códigos con filtros
    codigos = CodigoAlerta.objects.all()
    
    # Aplicar filtros
    search = request.GET.get('search')
    clasificacion = request.GET.get('clasificacion')
    modelo = request.GET.get('modelo')
    activo = request.GET.get('activo')
    
    if search:
        codigos = codigos.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(modelo_equipo__icontains=search)
        )
    
    if clasificacion:
        codigos = codigos.filter(clasificacion=clasificacion)
    
    if modelo:
        codigos = codigos.filter(modelo_equipo__icontains=modelo)
    
    if activo is not None:
        codigos = codigos.filter(activo=activo == 'true')
    
    # Ordenar por código
    codigos = codigos.order_by('codigo')
    
    # Paginación
    paginator = Paginator(codigos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener modelos únicos para el filtro
    modelos_unicos = CodigoAlerta.objects.values_list('modelo_equipo', flat=True).distinct().order_by('modelo_equipo')
    
    context = {
        'page_obj': page_obj,
        'search_filtro': search,
        'clasificacion_filtro': clasificacion,
        'modelo_filtro': modelo,
        'activo_filtro': activo,
        'modelos_unicos': modelos_unicos,
        'clasificaciones': CodigoAlerta.CLASIFICACION_CHOICES,
    }
    
    return render(request, 'centroSoluciones/gestionar_codigos_alerta.html', context)

@login_required
def crear_codigo_alerta(request):
    """Vista para crear un nuevo código de alerta"""
    
    # Solo gerentes y administrativos pueden crear códigos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear códigos de alerta.'})
    
    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            modelo_equipo = request.POST.get('modelo_equipo')
            descripcion = request.POST.get('descripcion')
            clasificacion = request.POST.get('clasificacion')
            instrucciones = request.POST.get('instrucciones_resolucion', '')
            repuestos = request.POST.get('repuestos_comunes', '')
            tiempo_estimado = request.POST.get('tiempo_estimado_resolucion')
            
            # Validaciones
            if not all([codigo, modelo_equipo, descripcion, clasificacion]):
                return JsonResponse({'success': False, 'message': 'Todos los campos obligatorios deben estar completos.'})
            
            # Verificar si el código ya existe
            if CodigoAlerta.objects.filter(codigo=codigo).exists():
                return JsonResponse({'success': False, 'message': f'El código {codigo} ya existe en la base de datos.'})
            
            # Crear el código
            nuevo_codigo = CodigoAlerta(
                codigo=codigo,
                modelo_equipo=modelo_equipo,
                descripcion=descripcion,
                clasificacion=clasificacion,
                instrucciones_resolucion=instrucciones,
                repuestos_comunes=repuestos,
                tiempo_estimado_resolucion=tiempo_estimado if tiempo_estimado else None,
                creado_por=request.user
            )
            nuevo_codigo.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Código {codigo} creado exitosamente.',
                'codigo_id': nuevo_codigo.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error al crear el código: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

@login_required
def obtener_lista_codigos_alerta(request):
    """Vista API para obtener lista de códigos de alerta (AJAX)"""
    try:
        codigos = CodigoAlerta.objects.filter(activo=True).values(
            'codigo', 'modelo_equipo', 'descripcion', 'clasificacion'
        ).order_by('codigo')
        
        return JsonResponse({
            'success': True,
            'codigos': list(codigos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener códigos: {str(e)}'})

# Vistas para archivos mensuales
@login_required
def archivos_mensuales(request):
    """Lista de archivos mensuales cargados"""
    from .models import ArchivoDatosMensual
    
    # Solo gerentes y administrativos pueden ver archivos mensuales
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    archivos = ArchivoDatosMensual.objects.all().order_by('-fecha_carga')
    
    # Estadísticas
    total_archivos = archivos.count()
    archivos_completados = archivos.filter(estado='COMPLETADO').count()
    archivos_procesando = archivos.filter(estado='PROCESANDO').count()
    archivos_error = archivos.filter(estado='ERROR').count()
    archivos_pendientes = archivos.filter(estado='PENDIENTE').count()
    
    # Paginación
    paginator = Paginator(archivos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_archivos': total_archivos,
        'archivos_completados': archivos_completados,
        'archivos_procesando': archivos_procesando,
        'archivos_error': archivos_error,
        'archivos_pendientes': archivos_pendientes,
    }
    
    return render(request, 'centroSoluciones/archivos_mensuales.html', context)

@login_required
def cargar_archivos_mensuales(request):
    """Vista para cargar archivos mensuales"""
    from .models import ArchivoDatosMensual
    
    # Solo gerentes y administrativos pueden cargar archivos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para cargar archivos.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    if request.method == 'POST':
        try:
            archivo_excel = request.FILES.get('archivo')
            tipo_archivo = request.POST.get('tipo')
            
            print(f"DEBUG: Archivo recibido: {archivo_excel}")
            print(f"DEBUG: Tipo recibido: {tipo_archivo}")
            
            if not archivo_excel:
                messages.error(request, 'Debe seleccionar un archivo.')
                return redirect('centroSoluciones:cargar_archivos_mensuales')
            
            if not tipo_archivo:
                messages.error(request, 'Debe seleccionar el tipo de archivo.')
                return redirect('centroSoluciones:cargar_archivos_mensuales')
            
            # Validar extensión
            if not archivo_excel.name.endswith('.xlsx'):
                messages.error(request, 'Solo se permiten archivos Excel (.xlsx).')
                return redirect('centroSoluciones:cargar_archivos_mensuales')
            
            print(f"DEBUG: Creando registro del archivo...")
            # Crear registro del archivo
            archivo_registro = ArchivoDatosMensual(
                nombre_archivo=archivo_excel.name,
                tipo=tipo_archivo,
                archivo=archivo_excel,
                cargado_por=request.user,
                estado='PENDIENTE'
            )
            archivo_registro.save()
            print(f"DEBUG: Registro creado con ID: {archivo_registro.id}")
            
            print(f"DEBUG: Iniciando procesamiento...")
            # Procesar el archivo
            procesar_archivo_excel(archivo_registro.id)
            print(f"DEBUG: Procesamiento completado")
            
            messages.success(request, f'Archivo {archivo_excel.name} cargado y procesado exitosamente.')
            return redirect('centroSoluciones:archivos_mensuales')
            
        except Exception as e:
            messages.error(request, f'Error al cargar el archivo: {str(e)}')
            return redirect('centroSoluciones:cargar_archivos_mensuales')
    
    return render(request, 'centroSoluciones/cargar_archivos_mensuales.html')

@login_required
def detalle_archivo_mensual(request, archivo_id):
    """Detalle de un archivo mensual específico"""
    from .models import ArchivoDatosMensual, DatosUtilizacionMensual, NotificacionMensual
    
    # Solo gerentes y administrativos pueden ver detalles
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    archivo = get_object_or_404(ArchivoDatosMensual, id=archivo_id)
    
    # Obtener datos procesados según el tipo
    if archivo.tipo == 'UTILIZACION':
        datos = DatosUtilizacionMensual.objects.filter(archivo=archivo).order_by('-fecha_inicio')
    elif archivo.tipo == 'NOTIFICACIONES':
        datos = NotificacionMensual.objects.filter(archivo=archivo).order_by('-fecha', '-codigo_hora')
    else:
        datos = []
    
    context = {
        'archivo': archivo,
        'datos': datos,
        'tipo_datos': archivo.tipo,
    }
    
    return render(request, 'centroSoluciones/detalle_archivo_mensual.html', context)

@login_required
def reprocesar_archivo_mensual(request, archivo_id):
    """Reprocesar un archivo mensual"""
    from .models import ArchivoDatosMensual
    
    # Solo gerentes y administrativos pueden reprocesar archivos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para reprocesar archivos.')
        return redirect('centroSoluciones:archivos_mensuales')
    
    archivo = get_object_or_404(ArchivoDatosMensual, id=archivo_id)
    
    try:
        # Cambiar estado a PENDIENTE para permitir reprocesamiento
        archivo.estado = 'PENDIENTE'
        archivo.errores = ''
        archivo.log_procesamiento = ''
        archivo.registros_procesados = 0
        archivo.save()
        
        # Reprocesar el archivo
        procesar_archivo_excel(archivo.id)
        
        messages.success(request, f'Archivo {archivo.nombre_archivo} reprocesado exitosamente.')
        
    except Exception as e:
        messages.error(request, f'Error al reprocesar el archivo: {str(e)}')
    
    return redirect('centroSoluciones:detalle_archivo_mensual', archivo_id=archivo_id)

@login_required
def cambiar_estado_archivo_mensual(request, archivo_id):
    """Cambiar manualmente el estado de un archivo mensual"""
    from .models import ArchivoDatosMensual
    
    # Solo gerentes y administrativos pueden cambiar estados
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para cambiar estados de archivos.')
        return redirect('centroSoluciones:archivos_mensuales')
    
    archivo = get_object_or_404(ArchivoDatosMensual, id=archivo_id)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    if nuevo_estado in ['PENDIENTE', 'PROCESANDO', 'COMPLETADO', 'ERROR']:
        archivo.estado = nuevo_estado
        archivo.save()
        messages.success(request, f'Estado del archivo cambiado a {nuevo_estado}.')
    else:
        messages.error(request, 'Estado no válido.')
    
    return redirect('centroSoluciones:detalle_archivo_mensual', archivo_id=archivo_id)

@login_required
def reportes_mensuales(request):
    """Vista para generar reportes mensuales consolidados"""
    from .models import DatosUtilizacionMensual, NotificacionMensual
    from django.db.models import Sum, Avg, Count
    from datetime import datetime, timedelta
    
    # Solo gerentes y administrativos pueden ver reportes
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    equipo_id = request.GET.get('equipo')
    
    # Filtrar datos de utilización
    datos_utilizacion = DatosUtilizacionMensual.objects.all()
    notificaciones = NotificacionMensual.objects.all()
    
    if fecha_inicio:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            datos_utilizacion = datos_utilizacion.filter(fecha_inicio__gte=fecha_inicio)
            notificaciones = notificaciones.filter(fecha__gte=fecha_inicio)
        except:
            pass
    
    if fecha_fin:
        try:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            datos_utilizacion = datos_utilizacion.filter(fecha_fin__lte=fecha_fin)
            notificaciones = notificaciones.filter(fecha__lte=fecha_fin)
        except:
            pass
    
    if equipo_id:
        datos_utilizacion = datos_utilizacion.filter(equipo_id=equipo_id)
        notificaciones = notificaciones.filter(equipo_id=equipo_id)
    
    # Estadísticas de utilización
    stats_utilizacion = datos_utilizacion.aggregate(
        total_horas=Sum('horas_trabajo_motor_periodo'),
        total_combustible=Sum('combustible_consumido_periodo'),
        consumo_promedio=Avg('consumo_promedio_periodo'),
        equipos_analizados=Count('equipo', distinct=True)
    )
    
    # Estadísticas de notificaciones
    stats_notificaciones = notificaciones.aggregate(
        total_notificaciones=Count('id'),
        notificaciones_resueltas=Count('id', filter=Q(resuelta=True)),
        equipos_con_alertas=Count('equipo', distinct=True)
    )
    
    # Obtener equipos para el filtro
    equipos = Equipo.objects.all().order_by('numero_serie')
    
    context = {
        'stats_utilizacion': stats_utilizacion,
        'stats_notificaciones': stats_notificaciones,
        'equipos': equipos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'equipo_seleccionado': equipo_id,
    }
    
    return render(request, 'centroSoluciones/reportes_mensuales.html', context)
