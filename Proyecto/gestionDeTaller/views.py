from django.shortcuts import render, redirect, get_object_or_404
from clientes.models import Equipo
from gestionDeTaller.models import Servicio, PreOrden, Evidencia, PedidoRepuestosTerceros, EncuestaServicio, RespuestaEncuesta
from recursosHumanos.models import TarifaManoObra, RegistroHorasTecnico, Sucursal, ActividadTrabajo
from gestionDeTaller.forms import (
    PreordenForm, ServicioForm, ServicioEditarForm, ServicioDocumentosForm,
    ServicioManoObraForm, PedidoRepuestosTercerosForm, GastoAsistenciaForm,
    VentaRepuestoForm, EditarInformeForm, EvidenciaForm, ChecklistSalidaCampoForm,
    FiltroExportacionServiciosForm, Revision5SForm, PlanAccion5SForm,
    RespuestaEncuestaForm, InsatisfaccionClienteForm
)
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, ExpressionWrapper, DurationField, Sum, Case, When, Value, Avg
from django.utils.timezone import timedelta
from django.utils import timezone
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.utils.html import mark_safe,strip_tags
from django.templatetags.static import static
import pandas as pd
import io
from datetime import datetime
import csv
from django.urls import reverse
from .models import Revision5S, PlanAccion5S
from .forms import Revision5SForm, PlanAccion5SForm, RespuestaEncuestaForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Avg, Count
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
import base64
import json
from datetime import datetime, timedelta
from .models import (
    PreOrden, Servicio, PedidoRepuestosTerceros, GastoAsistencia,
    VentaRepuesto, Revision5S, PlanAccion5S, CostoPersonalTaller,
    AnalisisTaller, Evidencia, ChecklistSalidaCampo, EncuestaServicio,
    RespuestaEncuesta, InsatisfaccionCliente, ObservacionServicio, Repuesto,
    HerramientaEspecial, ReservaHerramienta, LogHerramienta,
    HerramientaPersonal, AsignacionHerramientaPersonal, AuditoriaHerramientaPersonal,
    DetalleAuditoriaHerramienta, ItemHerramientaPersonal, LogCambioItemHerramienta
)
from recursosHumanos.models import Usuario
from .models import EvidenciaPlanAccion5S
from recursosHumanos.models import Usuario

@login_required
def equipos_por_cliente(request, cliente_id):
    equipos = Equipo.objects.filter(
        cliente_id=cliente_id, 
        activo=True
    ).select_related('modelo', 'modelo__tipo_equipo').values(
        'id', 
        'numero_serie',
        'modelo__nombre',
        'modelo__marca',
        'modelo__tipo_equipo__nombre'
    )
    
    equipos_list = []
    for equipo in equipos:
        equipos_list.append({
            'id': equipo['id'],
            'numero_serie': equipo['numero_serie'],
            'texto_completo': f"{equipo['numero_serie']} - {equipo['modelo__tipo_equipo__nombre']} {equipo['modelo__marca']} {equipo['modelo__nombre']}"
        })

    # Log para depuración
    print(f"Equipos para cliente ID {cliente_id}: {len(equipos_list)} equipos encontrados")

    return JsonResponse(equipos_list, safe=False)

@login_required
def gestion_de_taller(request):

    return render(request, 'gestionDeTaller/gestion_de_taller.html')

@login_required
def lista_servicios(request):
    usuario = request.user
    print(f"Usuario: {usuario.email}, Rol: {usuario.rol}")  # Log del usuario
    
    # Verificar que el usuario esté autenticado
    if not usuario.is_authenticated:
        messages.error(request, "Debe iniciar sesión para acceder a esta página.")
        return redirect('login')
    
    # Filtrar los servicios según el rol y sucursal del usuario
    if usuario.rol in ['ADMINISTRATIVO', 'TECNICO']:
        try:
            # Convertir usuario.sucursal en una instancia de Sucursal
            sucursal = Sucursal.objects.get(nombre=usuario.sucursal.nombre)
            servicios = Servicio.objects.filter(preorden__sucursal=sucursal)
        except Sucursal.DoesNotExist:
            servicios = Servicio.objects.none()  # Si no hay sucursal, no hay servicios
    else:
        servicios = Servicio.objects.all()  # Superusuarios u otros roles ven todo

    # Ordenar servicios por prioridad de estado (en proceso, en espera, programados primero)
    # Usar Case/When para ordenamiento personalizado
    from django.db.models import Case, When, IntegerField
    
    servicios = servicios.annotate(
        orden_estado=Case(
            When(estado='EN_PROCESO', then=1),
            When(estado='ESPERA_REPUESTOS', then=2),
            When(estado='PROGRAMADO', then=3),
            When(estado='A_FACTURAR', then=4),
            When(estado='COMPLETADO', then=5),
            default=6,
            output_field=IntegerField(),
        )
    ).order_by('orden_estado', '-fecha_servicio', '-id')

    # Procesar el formulario de filtro
    form_filtro = FiltroExportacionServiciosForm(request.POST or request.GET or None)
    fecha_inicio = None
    fecha_fin = None

    if form_filtro.is_valid():
        fecha_inicio = form_filtro.cleaned_data['fecha_inicio']
        fecha_fin = form_filtro.cleaned_data['fecha_fin']
        if fecha_inicio and fecha_fin:
            servicios = servicios.filter(fecha_servicio__range=[fecha_inicio, fecha_fin])

    # Si se solicita exportación y el usuario tiene permisos
    if request.method == 'POST':
        print(f"POST data: {request.POST}")  # Log de datos POST
        if 'exportar' in request.POST and usuario.rol in ['GERENTE', 'ADMINISTRACION']:
            print("Solicitud de exportación detectada")  # Log de exportación
            try:
                if not fecha_inicio or not fecha_fin:
                    messages.error(request, "Debe seleccionar un rango de fechas para exportar.")
                    return redirect('gestionDeTaller:lista_servicios')

                print(f"Fechas seleccionadas: {fecha_inicio} - {fecha_fin}")  # Log de fechas
                print(f"Servicios a exportar: {servicios.count()}")  # Log de cantidad de servicios
                
                # Crear un buffer para el archivo Excel
                output = io.BytesIO()
                
                # Crear un Excel writer
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Lista para almacenar los datos de todos los servicios
                    datos_servicios = []
                    
                    # Procesar cada servicio
                    for servicio in servicios:
                        # Calcular totales de manera segura
                        total_gastos = 0
                        total_repuestos = 0
                        total_mano_obra = servicio.valor_mano_obra or 0
                        
                        # Obtener gastos de asistencia
                        try:
                            total_gastos = servicio.gastos.aggregate(
                                total=Sum('monto')
                            )['total'] or 0
                        except Exception as e:
                            print(f"Error al obtener gastos de asistencia: {str(e)}")
                        
                        # Obtener ventas de repuestos
                        try:
                            total_repuestos = servicio.repuestos.aggregate(
                                total=Sum(F('precio_unitario') * F('cantidad'))
                            )['total'] or 0
                        except Exception as e:
                            print(f"Error al obtener ventas de repuestos: {str(e)}")
                        
                        # Agregar datos del servicio
                        datos_servicios.append({
                            'ID Servicio': servicio.id,
                            'Fecha': servicio.fecha_servicio,
                            'Cliente': servicio.preorden.cliente.razon_social,
                            'Equipo': servicio.preorden.equipo.numero_serie,
                            'Estado': servicio.get_estado_display(),
                            'Solicitud Cliente': servicio.preorden.solicitud_cliente,
                            'Total Gastos Asistencia': round(total_gastos, 2),
                            'Total Mano de Obra': round(total_mano_obra, 2),
                            'Total Repuestos': round(total_repuestos, 2),
                            'Total General': round(total_gastos + total_mano_obra + total_repuestos, 2)
                        })
                    
                    print(f"Datos procesados: {len(datos_servicios)} registros")  # Log de datos procesados
                    
                    if not datos_servicios:
                        messages.error(request, "No hay datos para exportar en el rango de fechas seleccionado.")
                        return redirect('gestionDeTaller:lista_servicios')
                    
                    # Crear DataFrame con los datos de los servicios
                    df_servicios = pd.DataFrame(datos_servicios)
                    
                    # Agregar fila de totales
                    totales = {
                        'ID Servicio': 'TOTALES',
                        'Fecha': '',
                        'Cliente': '',
                        'Equipo': '',
                        'Estado': '',
                        'Solicitud Cliente': '',
                        'Total Gastos Asistencia': df_servicios['Total Gastos Asistencia'].sum(),
                        'Total Mano de Obra': df_servicios['Total Mano de Obra'].sum(),
                        'Total Repuestos': df_servicios['Total Repuestos'].sum(),
                        'Total General': df_servicios['Total General'].sum()
                    }
                    df_servicios = pd.concat([df_servicios, pd.DataFrame([totales])], ignore_index=True)
                    
                    # Escribir en Excel
                    df_servicios.to_excel(writer, sheet_name='Resumen Servicios', index=False)
                    
                    # Obtener el workbook y la hoja
                    workbook = writer.book
                    worksheet = writer.sheets['Resumen Servicios']
                    
                    # Formato para moneda
                    money_format = workbook.add_format({'num_format': '$#,##0.00'})
                    
                    # Aplicar formatos
                    for col_num, value in enumerate(df_servicios.columns.values):
                        if 'Total' in value:
                            worksheet.set_column(col_num, col_num, 20, money_format)
                        elif value == 'Solicitud Cliente':
                            worksheet.set_column(col_num, col_num, 40)
                        else:
                            worksheet.set_column(col_num, col_num, 15)
                    
                    # Preparar la respuesta
                    output.seek(0)
                    response = HttpResponse(
                        output.read(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename=servicios_{fecha_inicio}_{fecha_fin}.xlsx'
                    return response
                    
            except Exception as e:
                print(f"Error al exportar: {str(e)}")
                messages.error(request, f"Error al exportar: {str(e)}")
                return redirect('gestionDeTaller:lista_servicios')

        elif 'guardar_servicio' in request.POST:
            print("Intentando guardar servicio...")  # Log de intento de guardar
            servicio_form = ServicioForm(request.POST, user=usuario)
            if servicio_form.is_valid():
                try:
                    servicio = servicio_form.save()
                    messages.success(request, "Servicio creado exitosamente.")
                    return redirect('gestionDeTaller:lista_servicios')
                except Exception as e:
                    print(f"Error al guardar el servicio: {str(e)}")  # Log de error
                    messages.error(request, f"Error al guardar el servicio: {str(e)}")
            else:
                print(f"Errores en el formulario de servicio: {servicio_form.errors}")  # Log de errores del formulario
                messages.error(request, "Por favor, corrija los errores en el formulario.")

    # Formularios con datos iniciales según el usuario y la preorden seleccionada
    preorden_form = PreordenForm(user=usuario)
    servicio_form = ServicioForm(user=usuario)

    # Calcular contadores por estado
    contadores_estado = {
        'en_proceso': servicios.filter(estado='EN_PROCESO').count(),
        'espera_repuestos': servicios.filter(estado='ESPERA_REPUESTOS').count(),
        'programado': servicios.filter(estado='PROGRAMADO').count(),
        'a_facturar': servicios.filter(estado='A_FACTURAR').count(),
        'completado': servicios.filter(estado='COMPLETADO').count(),
    }

    context = {
        'servicios': servicios,
        'form_filtro': form_filtro,
        'preorden_form': preorden_form,
        'servicio_form': servicio_form,
        'puede_exportar': usuario.rol in ['GERENTE', 'ADMINISTRACION'],
        'contadores_estado': contadores_estado,
    }

    return render(request, 'gestionDeTaller/servicios/lista_servicios.html', context)


@login_required
def calendario_preordenes(request):
    usuario = request.user
    
    if usuario.rol in ['ADMINISTRATIVO', 'TECNICO'] and usuario.sucursal:
        preordenes = PreOrden.objects.filter(sucursal=usuario.sucursal)
    else:
        preordenes = PreOrden.objects.all()
    
    return render(request, 'gestionDeTaller/preorden/calendario_preordenes.html', {'preordenes': preordenes})

@login_required
def preordenes_json(request):
    # Filtrar preórdenes por sucursal si el usuario no es gerente
    if not request.user.is_staff:
        preordenes = PreOrden.objects.filter(sucursal=request.user.sucursal)
    else:
        preordenes = PreOrden.objects.all()

    eventos = []
    for preorden in preordenes:
        # Determinar el color basado en el tipo de trabajo
        color = '#008000' if preorden.tipo_trabajo == 'PRESENCIAL_TALLER' else '#ff0000'
        
        # Formatear fecha y hora
        fecha_estimada = preorden.fecha_estimada.isoformat() if preorden.fecha_estimada else None
        hora_inicio = preorden.hora_inicio_estimada.isoformat() if preorden.hora_inicio_estimada else None
        hora_fin = preorden.hora_fin_estimada.isoformat() if preorden.hora_fin_estimada else None
        
        # Obtener los técnicos asignados
        tecnicos = preorden.tecnicos.all()
        tecnicos_str = ', '.join([f"{t.nombre} {t.apellido}" for t in tecnicos]) if tecnicos else 'No asignados'
        
        evento = {
            'title': f'Preorden #{preorden.numero} - {preorden.cliente.razon_social}',
            'start': f"{fecha_estimada}T{hora_inicio}" if hora_inicio else fecha_estimada,
            'end': f"{fecha_estimada}T{hora_fin}" if hora_fin else None,
            'url': reverse('gestionDeTaller:detalle_preorden', args=[preorden.numero]),
            'color': color,
            'extendedProps': {
                'numero': preorden.numero,
                'equipo': str(preorden.equipo),
                'tipo_trabajo': 'Taller' if preorden.tipo_trabajo == 'PRESENCIAL_TALLER' else 'Campo',
                'solicitud': preorden.solicitud_cliente,
                'tecnicos': tecnicos_str
            }
        }
        eventos.append(evento)

    return JsonResponse(eventos, safe=False)


@login_required           
def detalle_preorden(request, preorden_id):
    preorden = get_object_or_404(PreOrden, pk=preorden_id)
    evidencia = Evidencia.objects.filter(preorden=preorden)

    context = {
        'preorden': preorden,
        'evidencia': evidencia,
    }
    return render(request, 'gestionDeTaller/preorden/detalle_preorden.html', context )


@login_required
def crear_preorden(request):
    if request.method == 'POST':
        form = PreordenForm(request.POST, request.FILES, user=request.user)
        evidencia_form = EvidenciaForm()

        if form.is_valid():
            try:
                # Crear la instancia de preorden sin guardar aún
                preorden = form.save(commit=False)
                preorden.creado_por = request.user
                
                # Asegurarse de que la sucursal esté asignada
                if not preorden.sucursal:
                    if request.user.sucursal:
                        preorden.sucursal = request.user.sucursal
                    else:
                        messages.error(request, 'Debe seleccionar una sucursal.')
                        return render(request, 'gestionDeTaller/crear_preorden.html', {
                            'form': form,
                            'evidencia_form': evidencia_form
                        })
                
                preorden.save()
                form.save_m2m()  # Guardar relaciones ManyToMany

                # Procesar la firma en formato base64
                firma_data = request.POST.get("firma_cliente")
                if firma_data:
                    try:
                        format, imgstr = firma_data.split(';base64,')
                        ext = format.split('/')[-1]
                        data = ContentFile(base64.b64decode(imgstr), name=f"firma_{preorden.numero}.{ext}")
                        preorden.firma_cliente = data
                        preorden.save()  # Guardar nuevamente con la firma
                    except Exception as e:
                        print("Error al procesar la firma:", e)

                # Guardar imágenes de evidencia
                evidencia_files = request.FILES.getlist('imagen')  # Recoger todas las evidencias subidas
                for evidencia_file in evidencia_files:
                    Evidencia.objects.create(preorden=preorden, imagen=evidencia_file)

                messages.success(request, 'Preorden creada correctamente.')
                return redirect('gestionDeTaller:lista_preordenes')

            except Exception as e:
                print(f"Error al guardar la preorden o evidencias: {e}")
                messages.error(request, f'Error al crear la preorden: {str(e)}')
        else:
            print("Errores del formulario principal:", form.errors)
            messages.error(request, 'Por favor, corrija los errores en el formulario.')

    else:
        form = PreordenForm(user=request.user)
        evidencia_form = EvidenciaForm()  # Formulario vacío para evidencias

    return render(request, 'gestionDeTaller/crear_preorden.html', {
        'form': form,
        'evidencia_form': evidencia_form
    })



from recursosHumanos.models import TarifaManoObra  # Asegúrate de que esta importación esté bien para evitar problemas de circularidad.

@login_required
def detalle_servicio(request, servicio_id):
    # Obtener el servicio, preorden, cliente y contactos
    servicio = get_object_or_404(Servicio, id=servicio_id)
    cliente = servicio.preorden.cliente  # Obtener el cliente de la preorden
    contactos_cliente = cliente.contactos.all()  # Obtener contactos del cliente

    pedidos_repuestos = PedidoRepuestosTerceros.objects.filter(servicio=servicio)
    pedidos_repuestos = PedidoRepuestosTerceros.objects.filter(servicio=servicio)
    
    # Pasar el usuario a los formularios para validaciones de seguridad
    form_documentos = ServicioDocumentosForm(instance=servicio, user=request.user)
    form_editar = ServicioEditarForm(instance=servicio, user=request.user)
    form_mano_obra = ServicioManoObraForm(instance=servicio)
    form_pedido = PedidoRepuestosTercerosForm()
    form_gasto = GastoAsistenciaForm()
    form_repuesto = VentaRepuestoForm()
    checklist_existente = ChecklistSalidaCampo.objects.filter(servicio=servicio).first()
    
    if checklist_existente:
        form_checklist_campo = ChecklistSalidaCampoForm(instance=checklist_existente)
    else:
        form_checklist_campo = ChecklistSalidaCampoForm()

    # Procesar el envío de la encuesta si se solicita
    if request.method == 'POST' and 'enviar_encuesta' in request.POST:
        if servicio.estado == 'COMPLETADO' and not servicio.encuesta_enviada:
            servicio.enviar_encuesta()
            servicio.fecha_envio_encuesta = timezone.now()
            servicio.save()
            messages.success(request, "La encuesta ha sido enviada exitosamente.")
        else:
            messages.warning(request, "La encuesta ya fue enviada o el servicio no está completado.")

    # Calcular horas y valor de mano de obra
    registros = servicio.registrohorastecnico_set.annotate(
        duracion=ExpressionWrapper(
            F('hora_fin') - F('hora_inicio'),
            output_field=DurationField()
        )
    )
    total_horas_tecnicos = registros.aggregate(total=Sum('duracion'))['total'] or timedelta()
    total_horas_tecnicos_decimal = total_horas_tecnicos.total_seconds() / 3600 if total_horas_tecnicos else 0
    tecnicos_involucrados = registros.values('tecnico').distinct().count()
    tipo_tarifa = 'MULTIPLE' if tecnicos_involucrados > 1 else 'INDIVIDUAL'
    tipo_servicio = 'CAMPO' if servicio.preorden.tipo_trabajo == 'PRESENCIAL_CAMPO' else 'TALLER'

    tarifa = TarifaManoObra.objects.filter(
        tipo=tipo_tarifa,
        tipo_servicio=tipo_servicio,
        activo=True
    ).order_by('-fecha_vigencia').first()

    valor_mano_obra_calculado = (total_horas_tecnicos_decimal * tarifa.valor_hora) if tarifa else 0

    # Procesar el formulario de mano de obra si el usuario actualiza el valor
    if request.method == 'POST' and 'guardar_valor_mano_obra' in request.POST:
        form_mano_obra = ServicioManoObraForm(request.POST, instance=servicio)
        if form_mano_obra.is_valid():
            form_mano_obra.save()
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)

    # Recolectar correos electrónicos
    destinatarios_existentes = [cliente.email]  # Incluir el email del cliente
    destinatarios_existentes += [contacto.email for contacto in contactos_cliente if contacto.email]  # Correos de contactos

    # Obtener información de seguridad para el contexto
    from .security import puede_modificar_servicio, puede_modificar_informe, obtener_estados_disponibles
    
    # Debug: Imprimir información del usuario y servicio
    print(f"DEBUG - Usuario: {request.user.email}, Rol: {request.user.rol}")
    print(f"DEBUG - Servicio ID: {servicio.id}, Estado: {servicio.estado}")
    print(f"DEBUG - Tiene firma: {bool(servicio.firma_cliente)}")
    
    puede_modificar = puede_modificar_servicio(request.user, servicio)
    puede_modificar_informe_servicio = puede_modificar_informe(request.user, servicio)
    estados_disponibles = obtener_estados_disponibles(request.user, servicio)
    
    # Debug: Imprimir resultados de permisos
    print(f"DEBUG - Puede modificar servicio: {puede_modificar}")
    print(f"DEBUG - Puede modificar informe: {puede_modificar_informe_servicio}")
    print(f"DEBUG - Estados disponibles: {estados_disponibles}")

    # Obtener observaciones del servicio
    observaciones = servicio.observaciones_historial.all().order_by('-fecha_creacion')

    context = {
        'servicio': servicio,
        'cliente': cliente,
        'contactos_cliente': contactos_cliente,
        'destinatarios_existentes': destinatarios_existentes,  # Pasar los correos al contexto
        'form_editar': form_editar,
        'form_documentos': form_documentos,
        'total_horas_tecnicos': total_horas_tecnicos_decimal,
        'valor_mano_obra': servicio.valor_mano_obra or valor_mano_obra_calculado,
        'form_mano_obra': form_mano_obra,
        'form_pedido': form_pedido,
        'form_gasto': form_gasto,
        'form_repuesto': form_repuesto,
        'form_checklist_campo': form_checklist_campo,
        'checklist_existente': checklist_existente,
        'pedidos_repuestos':pedidos_repuestos,
        'estados_pedido': PedidoRepuestosTerceros.ESTADO_CHOICES,
        'observaciones': observaciones,  # Agregar observaciones al contexto
        # Información de seguridad
        'puede_modificar': puede_modificar,
        'puede_modificar_informe': puede_modificar_informe_servicio,
        'estados_disponibles': estados_disponibles,
    }
    return render(request, 'gestionDeTaller/servicios/detalle_servicio.html', context)


@login_required
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    # Verificar permisos de modificación
    from .security import puede_modificar_servicio
    if not puede_modificar_servicio(request.user, servicio):
        messages.error(request, "No puedes modificar este servicio porque está 'Finalizado a Facturar'. Solo un gerente puede hacer cambios.")
        return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    
    if request.method == 'POST':
        form = ServicioEditarForm(request.POST, instance=servicio, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Servicio actualizado exitosamente.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = ServicioEditarForm(instance=servicio, user=request.user)
    
    return render(request, 'gestionDeTaller/servicios/editar_servicio.html', {'form': form, 'servicio': servicio})




def get_preorden_horometro(request):
    preorden_id = request.GET.get('preorden_id')
    try:
        preorden = PreOrden.objects.get(numero=preorden_id)
        return JsonResponse({'horometro': preorden.horometro})
    except PreOrden.DoesNotExist:
        return JsonResponse({'horometro': None})
    

def editar_servicio_documentos(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = ServicioDocumentosForm(request.POST, request.FILES, instance=servicio, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Documentos actualizados exitosamente.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = ServicioDocumentosForm(instance=servicio, user=request.user)
    
    return render(request, 'gestionDeTaller/servicios/editar_servicio_documentos.html', {'form': form, 'servicio': servicio})

@login_required
def editar_valor_mano_obra(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == 'POST':
        form = ServicioManoObraForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = ServicioManoObraForm(instance=servicio)
    return render(request, 'gestionDeTaller/servicios/editar_valor_mano_obra.html', {'form': form, 'servicio': servicio})

@login_required
def agregar_pedido(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = PedidoRepuestosTercerosForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.servicio = servicio
            pedido.save()
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = PedidoRepuestosTercerosForm()
    
    return render(request, 'gestionDeTaller/servicios/agregar_pedido.html', {'form': form, 'servicio': servicio})


@login_required
def agregar_gasto_asistencia(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = GastoAsistenciaForm(request.POST, request.FILES)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.servicio = servicio
            gasto.save()
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = GastoAsistenciaForm()
    
    return render(request, 'gestionDeTaller/servicios/agregar_gasto.html', {'form': form, 'servicio': servicio})

@login_required
def agregar_venta_repuesto(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        # Debug: imprimir los datos recibidos
        print("Datos POST recibidos:", request.POST)
        
        form = VentaRepuestoForm(request.POST)
        print("Formulario válido:", form.is_valid())
        print("Errores del formulario:", form.errors)
        
        if form.is_valid():
            repuesto = form.save(commit=False)
            repuesto.servicio = servicio
            repuesto.save()
            messages.success(request, "Venta de repuesto agregada exitosamente.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
        else:
            # Debug: mostrar errores específicos del formulario
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            
            if error_messages:
                messages.error(request, f"Errores en el formulario: {'; '.join(error_messages)}")
            else:
                messages.error(request, "Error al guardar la venta de repuesto. Por favor verifica los datos.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    
    # Si no es POST, redirigir al detalle del servicio
    return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)


    
from django.utils.html import strip_tags
from django.contrib.staticfiles.storage import staticfiles_storage

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.templatetags.static import static
import mimetypes
from email.mime.image import MIMEImage

@login_required
def enviar_documentacion(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    cliente = servicio.preorden.cliente
    destinatarios_existentes = [cliente.email] if cliente.email else []
    contactos = cliente.contactos.all()
    destinatarios_existentes += [contacto.email for contacto in contactos if contacto.email]
    
    # Si es una solicitud POST, procesar el formulario
    if request.method == 'POST':
        emails_seleccionados = request.POST.getlist('emails[]')
        nuevo_correo = request.POST.get('nuevo_correo')
        mensaje_correo = request.POST.get('mensaje_correo', '')

        if nuevo_correo:
            emails_seleccionados.append(nuevo_correo)
        
        if emails_seleccionados:
            asunto = f"Documentación del Servicio con factura #{servicio.numero_factura}"
            email = EmailMultiAlternatives(
                asunto, 
                strip_tags(mensaje_correo), 
                to=emails_seleccionados,
                cc=settings.CC_EMAILS  # Agregar los correos en CC
            )
            email.attach_alternative(mensaje_correo, "text/html")

            if servicio.archivo_factura:
                email.attach_file(servicio.archivo_factura.path)
            if servicio.archivo_informe:
                email.attach_file(servicio.archivo_informe.path)

            email.send()
            
            # Registrar la fecha de envío de la documentación
            servicio.fecha_envio_documentacion = timezone.now()
            servicio.save()
            
            messages.success(request, "Documentación enviada con éxito.")
        
        return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio_id)

    context = {
        'servicio': servicio,
        'destinatarios_existentes': destinatarios_existentes
    }
    return render(request, 'gestionDeTaller/enviar_documentacion.html', context)


import base64
from django.core.files.base import ContentFile

@login_required
def editar_informe(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    cliente = servicio.preorden.cliente
    equipo = servicio.preorden.equipo
    solicitud_cliente = servicio.preorden.solicitud_cliente

    # Verificar permisos de modificación de informe
    from .security import puede_modificar_informe
    if not puede_modificar_informe(request.user, servicio):
        messages.error(request, "No puedes modificar este informe porque ya fue firmado por el cliente. Solo un gerente puede hacer cambios.")
        return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)

    if request.method == 'POST':
        form = EditarInformeForm(request.POST, request.FILES, instance=servicio)
        if form.is_valid():
            # Guardar valores anteriores para comparar
            valores_anteriores = {
                'causa': servicio.causa,
                'accion_correctiva': servicio.accion_correctiva,
                'ubicacion': servicio.ubicacion,
                'kilometros': servicio.kilometros,
                'observaciones': servicio.observaciones,
                'firma_cliente': servicio.firma_cliente,
                'nombre_cliente': servicio.nombre_cliente,
            }
            
            # Procesar la firma si está presente en el formulario
            firma_data = request.POST.get('firma')
            if firma_data:
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"firma_{servicio.id}.{ext}")
                servicio.firma_cliente = data
            
            # Guardar el formulario
            form.save()
            
            # Registrar cambios
            from .security import registrar_cambio_informe
            from django.utils import timezone
            
            # Obtener IP del usuario
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Comparar y registrar cambios
            for campo, valor_anterior in valores_anteriores.items():
                valor_nuevo = getattr(servicio, campo)
                if valor_anterior != valor_nuevo:
                    registrar_cambio_informe(
                        servicio=servicio,
                        usuario=request.user,
                        campo_modificado=campo,
                        valor_anterior=valor_anterior,
                        valor_nuevo=valor_nuevo,
                        motivo="Edición de informe",
                        ip_address=ip_address
                    )
            
            messages.success(request, "Informe actualizado exitosamente.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    else:
        form = EditarInformeForm(instance=servicio)

    context = {
        'form': form,
        'servicio': servicio,
        'cliente': cliente,
        'equipo': equipo,
        'trabajo': servicio.trabajo,
        'fecha_servicio': servicio.fecha_servicio,
        'solicitud_cliente': solicitud_cliente,
    }
    return render(request, 'gestionDeTaller/editar_informe.html', context)

from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import io

import os
import io
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.conf import settings
from gestionDeTaller.models import Servicio

# Función de utilidad para construir la URL absoluta de archivos estáticos
def link_callback(uri, rel):
    if uri.startswith('/static/'):
        path = os.path.join(settings.BASE_DIR, uri.replace('/static/', 'static/'))
    elif uri.startswith('/media/'):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace('/media/', ''))
    else:
        return uri
    if not os.path.isfile(path):
        raise Exception(f"El archivo {path} no se encuentra en el sistema.")
    return path

@login_required
def generar_informe_pdf(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    cliente = servicio.preorden.cliente
    equipo = servicio.preorden.equipo
    solicitud_cliente = servicio.preorden.solicitud_cliente
    # Si "tecnicos" es ManyToMany o relacionado correctamente
    tecnicos = servicio.preorden.tecnicos.all() if hasattr(servicio.preorden, 'tecnicos') else []

    context = {
        'servicio': servicio,
        'cliente': cliente,
        'equipo': equipo,
        'trabajo': servicio.trabajo,
        'fecha_servicio': servicio.fecha_servicio,
        'solicitud_cliente': solicitud_cliente,
        'tecnicos' : tecnicos,
    }

    html = render_to_string('gestionDeTaller/informe_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Informe_Servicio_{servicio.id}.pdf"'
    
    # Convertir HTML a PDF con link_callback para manejar archivos estáticos
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=response, link_callback=link_callback)
    
    # Verificar errores
    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF", status=400)

    return response


@login_required
def ver_informe(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    tecnicos_responsables = servicio.preorden.tecnicos.all()  # Supón que 'tecnicos' es una relación ManyToMany o ForeignKey

    
    # Obtener los datos necesarios para el informe
    cliente = servicio.preorden.cliente
    equipo = servicio.preorden.equipo
    trabajo = servicio.trabajo
    solicitud_cliente = servicio.preorden.solicitud_cliente
    
    context = {
        'servicio': servicio,
        'cliente': cliente,
        'equipo': equipo,
        'trabajo': trabajo,
        'solicitud_cliente': solicitud_cliente,
        'tecnicos_responsables': tecnicos_responsables,
    }
    return render(request, 'gestionDeTaller/ver_informe.html', context)


@login_required
def lista_preordenes(request):
    usuario = request.user
    
    if usuario.rol in ['ADMINISTRATIVO', 'TECNICO'] and usuario.sucursal:
        preordenes = PreOrden.objects.filter(sucursal=usuario.sucursal)
    else:
        preordenes = PreOrden.objects.all()
    return render(request, 'gestionDeTaller/lista_preordenes.html', {'preordenes': preordenes})

@login_required
def editar_preorden(request, preorden_id):
    try:
        preorden = PreOrden.objects.get(numero=preorden_id)
    except PreOrden.DoesNotExist:
        return redirect('gestionDeTaller:lista_servicios')
    
    if request.method == 'POST':
        form = PreordenForm(request.POST, request.FILES, instance=preorden, user=request.user)
        evidencia_forms = [EvidenciaForm(request.POST, request.FILES, prefix=str(i)) for i in range(len(request.FILES.getlist('imagen')))]
        
        if form.is_valid() and all([ef.is_valid() for ef in evidencia_forms]):
            try:
                # Guardar la instancia de preorden
                preorden = form.save(commit=False)
                
                # Asegurarse de que la sucursal esté asignada
                if not preorden.sucursal:
                    if request.user.sucursal:
                        preorden.sucursal = request.user.sucursal
                    else:
                        messages.error(request, 'Debe seleccionar una sucursal.')
                        return render(request, 'gestionDeTaller/editar_preorden.html', {
                            'form': form,
                            'evidencia_forms': evidencia_forms,
                            'preorden': preorden
                        })
                
                # Procesar la firma en formato base64
                firma_data = request.POST.get("firma_cliente")
                if firma_data and firma_data.startswith('data:image'):
                    try:
                        format, imgstr = firma_data.split(';base64,')
                        ext = format.split('/')[-1]
                        data = ContentFile(base64.b64decode(imgstr), name=f"firma_{preorden.numero}.{ext}")
                        preorden.firma_cliente = data
                    except Exception as e:
                        print("Error al procesar la firma:", e)
                
                preorden.save()
                form.save_m2m()  # Guardar relaciones ManyToMany
                
                # Guardar cada imagen de evidencia
                for evidencia_form in evidencia_forms:
                    if evidencia_form.is_valid() and evidencia_form.cleaned_data.get('imagen'):
                        Evidencia.objects.create(preorden=preorden, imagen=evidencia_form.cleaned_data['imagen'])
                
                messages.success(request, 'Preorden actualizada correctamente.')
                return redirect('gestionDeTaller:lista_preordenes')
                
            except Exception as e:
                print(f"Error al guardar la preorden o evidencias: {e}")
                messages.error(request, f'Error al guardar la preorden: {str(e)}')
        else:
            print("Errores del formulario principal:", form.errors)
            messages.error(request, 'Por favor, corrija los errores en el formulario.')
    else:
        form = PreordenForm(instance=preorden, user=request.user)
        evidencia_forms = [EvidenciaForm(prefix=str(i)) for i in range(3)]  # 3 formularios de evidencia por defecto
    
    return render(request, 'gestionDeTaller/editar_preorden.html', {
        'form': form,
        'evidencia_forms': evidencia_forms,
        'preorden': preorden
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Servicio, ChecklistSalidaCampo
from .forms import ChecklistSalidaCampoForm

@login_required
def crear_checklist_campo(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = ChecklistSalidaCampoForm(request.POST)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.servicio = servicio
            checklist.save()
            messages.success(request, "Checklist de salida al campo guardado exitosamente.")
            return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
        else:
            messages.error(request, "Error al guardar el checklist. Por favor, revisa el formulario.")
    
    return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def actualizar_estado_pedido(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pedido_id = data.get('id')
            nuevo_estado = data.get('estado')

            pedido = PedidoRepuestosTerceros.objects.get(id=pedido_id)
            pedido.estado = nuevo_estado
            pedido.save()

            return JsonResponse({'success': True})
        except PedidoRepuestosTerceros.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido no encontrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})




from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, F, Case, When, ExpressionWrapper, DurationField
from datetime import timedelta
from recursosHumanos.models import Usuario, RegistroHorasTecnico
from recursosHumanos.forms import FiltroExportacionHorasForm

@login_required
def tecnicos(request):
    # Verificar si el usuario es gerente (puede ver todos los técnicos)
    es_gerente = request.user.rol == 'GERENTE'
    es_superuser = request.user.is_superuser

    # Filtrar usuarios con rol "Técnico" según la sucursal del usuario o mostrar todos si es gerente/superuser
    if es_superuser or es_gerente:
        tecnicos_visibles = Usuario.objects.filter(rol='TECNICO')
    else:
        tecnicos_visibles = Usuario.objects.filter(rol='TECNICO', sucursal=request.user.sucursal)

    # Procesar el formulario de filtro si se envía
    form_filtro = FiltroExportacionHorasForm(request.GET or None)
    fecha_inicio = None
    fecha_fin = None

    if form_filtro.is_valid():
        fecha_inicio = form_filtro.cleaned_data['fecha_inicio']
        fecha_fin = form_filtro.cleaned_data['fecha_fin']

    # Si se solicita exportación
    if request.GET.get('exportar') and fecha_inicio and fecha_fin:
        try:
            return exportar_registros_horas(tecnicos_visibles, fecha_inicio, fecha_fin)
        except Exception as e:
            print(f"Error al exportar: {str(e)}")
            messages.error(request, "Error al exportar los datos. Por favor, intente nuevamente.")
            return redirect('gestionDeTaller:tecnicos')

    total_productividad = 0
    total_eficiencia = 0
    total_desempeno = 0
    total_tecnicos_con_registros = 0

    # Calcular métricas solo de los técnicos visibles
    for tecnico in tecnicos_visibles:
        registros_por_dia = RegistroHorasTecnico.objects.filter(
            tecnico=tecnico
        )
        
        if fecha_inicio and fecha_fin:
            registros_por_dia = registros_por_dia.filter(fecha__range=[fecha_inicio, fecha_fin])

        registros_por_dia = registros_por_dia.values('fecha').annotate(
            total_horas_registradas=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=DurationField()
                )
            ),
            horas_disponibles=Sum(
                Case(
                    When(tipo_hora__disponibilidad='DISPONIBLE', 
                         then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                         output_field=DurationField())),
                    default=timedelta(),
                    output_field=DurationField()
                )
            ),
            horas_generan_ingreso=Sum(
                Case(
                    When(tipo_hora__disponibilidad='DISPONIBLE',
                         tipo_hora__genera_ingreso='INGRESO',
                         then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                         output_field=DurationField())),
                    default=timedelta(),
                    output_field=DurationField()
                )
            ),
            horas_facturadas=Sum(
                Case(
                    When(tipo_hora__disponibilidad='DISPONIBLE',
                         tipo_hora__genera_ingreso='INGRESO',
                         tipo_hora__categoria_facturacion='FACTURABLE',
                         then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                         output_field=DurationField())),
                    default=timedelta(),
                    output_field=DurationField()
                )
            )
        )

        total_productividad_tecnico = 0
        total_eficiencia_tecnico = 0
        total_desempeno_tecnico = 0
        total_dias = len(registros_por_dia)

        if total_dias > 0:
            total_tecnicos_con_registros += 1

            for registro in registros_por_dia:
                horas_disponibles = registro['horas_disponibles'].total_seconds() / 3600 if registro['horas_disponibles'] else 0
                horas_generan_ingreso = registro['horas_generan_ingreso'].total_seconds() / 3600 if registro['horas_generan_ingreso'] else 0
                horas_facturadas = registro['horas_facturadas'].total_seconds() / 3600 if registro['horas_facturadas'] else 0

                # Calcular métricas para este día
                productividad = (horas_generan_ingreso / horas_disponibles) * 100 if horas_disponibles > 0 else 0
                eficiencia = (horas_facturadas / horas_generan_ingreso) * 100 if horas_generan_ingreso > 0 else 0
                desempeno = (horas_facturadas / horas_disponibles) * 100 if horas_disponibles > 0 else 0

                total_productividad_tecnico += productividad
                total_eficiencia_tecnico += eficiencia
                total_desempeno_tecnico += desempeno

            # Calcular promedios para el técnico
            tecnico.productividad = total_productividad_tecnico / total_dias
            tecnico.eficiencia = total_eficiencia_tecnico / total_dias
            tecnico.desempeno = total_desempeno_tecnico / total_dias

            total_productividad += tecnico.productividad
            total_eficiencia += tecnico.eficiencia
            total_desempeno += tecnico.desempeno

    # Calcular promedios globales
    promedio_productividad_global = total_productividad / total_tecnicos_con_registros if total_tecnicos_con_registros > 0 else 0
    promedio_eficiencia_global = total_eficiencia / total_tecnicos_con_registros if total_tecnicos_con_registros > 0 else 0
    promedio_desempeno_global = total_desempeno / total_tecnicos_con_registros if total_tecnicos_con_registros > 0 else 0

    context = {
        'tecnicos_visibles': tecnicos_visibles,
        'promedio_productividad_global': promedio_productividad_global,
        'promedio_eficiencia_global': promedio_eficiencia_global,
        'promedio_desempeno_global': promedio_desempeno_global,
        'es_gerente': es_gerente,
        'es_superuser': es_superuser,
        'form_filtro': form_filtro,
    }
    return render(request, 'gestionDeTaller/tecnicos/tecnicos.html', context)

def exportar_registros_horas(tecnicos, fecha_inicio, fecha_fin):
    try:
        # Crear un buffer para el archivo Excel
        output = io.BytesIO()
        
        # Crear un Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Lista para almacenar los datos de todos los técnicos
            datos_tecnicos = []
            
            # Procesar cada técnico
            for tecnico in tecnicos:
                registros = RegistroHorasTecnico.objects.filter(
                    tecnico=tecnico,
                    fecha__range=[fecha_inicio, fecha_fin]
                ).order_by('fecha', 'hora_inicio')
                
                # Calcular métricas
                total_horas = 0
                horas_disponibles = 0
                horas_generan_ingreso = 0
                horas_facturadas = 0
                
                # Lista para almacenar los datos detallados del técnico
                datos_detalle = []
                
                for registro in registros:
                    # Convertir hora_inicio y hora_fin a datetime completos
                    inicio = datetime.combine(registro.fecha, registro.hora_inicio)
                    fin = datetime.combine(registro.fecha, registro.hora_fin)
                    
                    # Calcular duración en horas
                    duracion = (fin - inicio).total_seconds() / 3600
                    total_horas += duracion
                    
                    if registro.tipo_hora.disponibilidad == 'DISPONIBLE':
                        horas_disponibles += duracion
                        if registro.tipo_hora.genera_ingreso == 'INGRESO':
                            horas_generan_ingreso += duracion
                            if registro.tipo_hora.categoria_facturacion == 'FACTURABLE':
                                horas_facturadas += duracion
                    
                    # Obtener el número de servicio de manera segura
                    numero_servicio = ''
                    if registro.servicio:
                        try:
                            numero_servicio = f"Servicio #{registro.servicio.id}"
                        except:
                            numero_servicio = ''
                    
                    # Agregar datos detallados del registro
                    datos_detalle.append({
                        'Fecha': registro.fecha,
                        'Hora Inicio': registro.hora_inicio,
                        'Hora Fin': registro.hora_fin,
                        'Actividad': registro.tipo_hora.nombre,
                        'Servicio': numero_servicio,
                        'Descripción': registro.descripcion,
                        'Aprobado': 'Sí' if registro.aprobado else 'No'
                    })
                
                # Calcular KPIs
                productividad = (horas_generan_ingreso / horas_disponibles * 100) if horas_disponibles > 0 else 0
                eficiencia = (horas_facturadas / horas_generan_ingreso * 100) if horas_generan_ingreso > 0 else 0
                desempeno = (horas_facturadas / horas_disponibles * 100) if horas_disponibles > 0 else 0
                
                # Agregar datos del técnico al resumen
                datos_tecnicos.append({
                    'Técnico': tecnico.get_nombre_completo(),
                    'Total Horas': round(total_horas, 2),
                    'Horas Disponibles': round(horas_disponibles, 2),
                    'Horas que Generan Ingreso': round(horas_generan_ingreso, 2),
                    'Horas Facturadas': round(horas_facturadas, 2),
                    'Productividad (%)': round(productividad, 2),
                    'Eficiencia (%)': round(eficiencia, 2),
                    'Desempeño (%)': round(desempeno, 2)
                })
                
                # Crear DataFrame con los datos detallados del técnico
                if datos_detalle:
                    df_detalle = pd.DataFrame(datos_detalle)
                    # Escribir en una hoja separada para cada técnico
                    sheet_name = f"Detalle {tecnico.get_nombre_completo()}"[:31]  # Excel limita nombres de hojas a 31 caracteres
                    df_detalle.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Obtener la hoja y aplicar formatos
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 12)  # Fecha
                    worksheet.set_column('B:C', 10)  # Hora Inicio/Fin
                    worksheet.set_column('D:D', 30)  # Actividad
                    worksheet.set_column('E:E', 15)  # Servicio
                    worksheet.set_column('F:F', 40)  # Descripción
                    worksheet.set_column('G:G', 10)  # Aprobado
                    
                    # Agregar formato de fecha
                    date_format = writer.book.add_format({'num_format': 'dd/mm/yyyy'})
                    worksheet.set_column('A:A', 12, date_format)
                    
                    # Agregar formato de hora
                    time_format = writer.book.add_format({'num_format': 'hh:mm'})
                    worksheet.set_column('B:C', 10, time_format)
            
            # Crear DataFrame con los datos de los técnicos
            df_tecnicos = pd.DataFrame(datos_tecnicos)
            
            # Agregar fila de promedios
            promedios = {
                'Técnico': 'PROMEDIO',
                'Total Horas': df_tecnicos['Total Horas'].mean(),
                'Horas Disponibles': df_tecnicos['Horas Disponibles'].mean(),
                'Horas que Generan Ingreso': df_tecnicos['Horas que Generan Ingreso'].mean(),
                'Horas Facturadas': df_tecnicos['Horas Facturadas'].mean(),
                'Productividad (%)': df_tecnicos['Productividad (%)'].mean(),
                'Eficiencia (%)': df_tecnicos['Eficiencia (%)'].mean(),
                'Desempeño (%)': df_tecnicos['Desempeño (%)'].mean()
            }
            df_tecnicos = pd.concat([df_tecnicos, pd.DataFrame([promedios])], ignore_index=True)
            
            # Escribir en Excel
            df_tecnicos.to_excel(writer, sheet_name='Resumen Técnicos', index=False)
            
            # Obtener el workbook y la hoja
            workbook = writer.book
            worksheet = writer.sheets['Resumen Técnicos']
            
            # Formato para porcentajes
            percent_format = workbook.add_format({'num_format': '0.00%'})
            number_format = workbook.add_format({'num_format': '0.00'})
            
            # Aplicar formatos
            for col_num, value in enumerate(df_tecnicos.columns.values):
                if '%' in value:
                    worksheet.set_column(col_num, col_num, 15, percent_format)
                elif 'Horas' in value:
                    worksheet.set_column(col_num, col_num, 15, number_format)
                else:
                    worksheet.set_column(col_num, col_num, 20)
        
        # Preparar la respuesta HTTP
        output.seek(0)
        excel_data = output.getvalue()
        
        # Crear la respuesta HTTP
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Configurar los encabezados de la respuesta
        filename = f'registro_horas_{fecha_inicio}_{fecha_fin}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(excel_data)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"Error en exportar_registros_horas: {str(e)}")
        raise

@login_required
def detalle_tecnico(request, tecnico_id):
    tecnico = get_object_or_404(Usuario, pk=tecnico_id)

    # Obtener la fecha actual y calcular el inicio de la semana
    fecha_actual = datetime.today().date()

    # Si el usuario está navegando entre semanas, obtener el parámetro GET 'semana'
    semana_str = request.GET.get('semana')
    if semana_str:
        try:
            inicio_semana = datetime.strptime(semana_str, '%Y-%m-%d').date()
        except ValueError:
            inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())  # Reiniciar a semana actual en caso de error
    else:
        inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())  # Lunes de la semana actual

    fin_semana = inicio_semana + timedelta(days=5)  # Hasta el sábado

    # Obtener los registros de horas del técnico en la semana actual
    registros_por_dia = RegistroHorasTecnico.objects.filter(
        tecnico=tecnico,
        fecha__range=[inicio_semana, fin_semana]
    ).values('fecha').annotate(
        total_horas_registradas=Sum(
            ExpressionWrapper(F('hora_fin') - F('hora_inicio'), output_field=DurationField())
        ),
        total_horas_aprobadas=Sum(
            Case(
                When(aprobado=True, then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), output_field=DurationField())),
                default=Value(timedelta()),
                output_field=DurationField()
            )
        ),
        horas_disponibles=Sum(
            Case(
                When(tipo_hora__disponibilidad='DISPONIBLE', 
                     then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                     output_field=DurationField())),
                default=Value(timedelta()),
                output_field=DurationField()
            )
        ),
        horas_generan_ingreso=Sum(
            Case(
                When(tipo_hora__disponibilidad='DISPONIBLE',
                     tipo_hora__genera_ingreso='INGRESO',
                     then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                     output_field=DurationField())),
                default=Value(timedelta()),
                output_field=DurationField()
            )
        ),
        horas_facturadas=Sum(
            Case(
                When(tipo_hora__disponibilidad='DISPONIBLE',
                     tipo_hora__genera_ingreso='INGRESO',
                     tipo_hora__categoria_facturacion='FACTURABLE',
                     then=ExpressionWrapper(F('hora_fin') - F('hora_inicio'), 
                     output_field=DurationField())),
                default=Value(timedelta()),
                output_field=DurationField()
            )
        )
    ).order_by('fecha')

    # Calcular métricas
    total_productividad = 0
    total_eficiencia = 0
    total_desempeno = 0
    total_dias = len(registros_por_dia)

    if total_dias > 0:
        for registro in registros_por_dia:
            horas_disponibles = registro['horas_disponibles'].total_seconds() / 3600 if registro['horas_disponibles'] else 0
            horas_generan_ingreso = registro['horas_generan_ingreso'].total_seconds() / 3600 if registro['horas_generan_ingreso'] else 0
            horas_facturadas = registro['horas_facturadas'].total_seconds() / 3600 if registro['horas_facturadas'] else 0
            
            # Calcular métricas para este día
            productividad = (horas_generan_ingreso / horas_disponibles) * 100 if horas_disponibles > 0 else 0
            eficiencia = (horas_facturadas / horas_generan_ingreso) * 100 if horas_generan_ingreso > 0 else 0
            desempeno = (horas_facturadas / horas_disponibles) * 100 if horas_disponibles > 0 else 0
            
            total_productividad += productividad
            total_eficiencia += eficiencia
            total_desempeno += desempeno

        # Calcular promedios
        promedio_productividad = total_productividad / total_dias
        promedio_eficiencia = total_eficiencia / total_dias
        promedio_desempeno = total_desempeno / total_dias
    else:
        promedio_productividad = 0
        promedio_eficiencia = 0
        promedio_desempeno = 0

    # Formatear los registros por día en un diccionario más fácil de usar en el template
    registros_dict = {registro['fecha']: registro for registro in registros_por_dia}

    # Construir la estructura de la semana con estado de cada día
    dias_semana = []
    for i in range(6):  # De lunes a sábado
        dia_fecha = inicio_semana + timedelta(days=i)
        registros_dia = registros_dict.get(dia_fecha, {})
        horas_registradas = registros_dia.get('total_horas_registradas', timedelta()).total_seconds() / 3600 if registros_dia.get('total_horas_registradas') else 0
        horas_aprobadas = registros_dia.get('total_horas_aprobadas', timedelta()).total_seconds() / 3600 if registros_dia.get('total_horas_aprobadas') else 0
        horas_disponibles = 9 if i < 5 else 4  # Lunes a viernes 9h, sábado 4h

        # Definir el estado del día
        if horas_aprobadas == horas_disponibles:
            estado = 'completo'
        elif horas_registradas > 0:
            estado = 'parcial'
        else:
            estado = 'sin_registro'

        dias_semana.append({
            'fecha': dia_fecha,
            'horas_registradas': horas_registradas,
            'horas_aprobadas': horas_aprobadas,
            'horas_disponibles': horas_disponibles,
            'estado': estado,
        })

    # Obtener días pendientes de registro
    registros_pendientes = [
        dia['fecha'] for dia in dias_semana if dia['estado'] == 'sin_registro' and dia['fecha'] < fecha_actual
    ]

    # Calcular semana anterior y siguiente
    semana_anterior = (inicio_semana - timedelta(days=7)).strftime('%Y-%m-%d')
    semana_siguiente = (inicio_semana + timedelta(days=7)).strftime('%Y-%m-%d')

    context = {
        'tecnico': tecnico,
        'dias_semana': dias_semana,
        'registros_por_dia': registros_por_dia,
        'registros_pendientes': registros_pendientes,
        'fecha_actual': fecha_actual,
        'semana_actual': inicio_semana.strftime('%d %b') + " - " + fin_semana.strftime('%d %b'),
        'semana_anterior': semana_anterior,
        'semana_siguiente': semana_siguiente,
        'promedio_productividad': promedio_productividad,
        'promedio_eficiencia': promedio_eficiencia,
        'promedio_desempeno': promedio_desempeno,
    }

    return render(request, 'gestionDeTaller/tecnicos/detalle_tecnico.html', context)


def dashboard_kpi(request):
    context = {
        'facturacion_spot': Servicio.get_facturacion_spot(),
        'facturacion_programados': Servicio.get_facturacion_programados(),
        'facturacion_campania': Servicio.get_facturacion_campania(),
        'facturacion_adicional': Servicio.get_facturacion_adicional(),
        'tiempo_promedio_cierre': Servicio.get_tiempo_promedio_cierre(),
        'trabajo_en_curso': Servicio.get_trabajo_en_curso(),
    }
    return render(request, 'dashboard.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from recursosHumanos.models import Usuario, RegistroHorasTecnico
from gestionDeTaller.models import Servicio
from recursosHumanos.forms import RegistroHorasTecnicoForm  # Asegúrate de importar el formulario

@login_required
def registrar_horas(request, tecnico_id):
    tecnico = get_object_or_404(Usuario, pk=tecnico_id)
    actividad = ActividadTrabajo.objects.all()

    # Obtener la fecha desde el parámetro GET (por defecto, la fecha actual)
    fecha_str = request.GET.get('fecha', datetime.today().strftime('%Y-%m-%d'))
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

    # Obtener los registros previos para esta fecha
    registros_previos = RegistroHorasTecnico.objects.filter(
        tecnico=tecnico,
        fecha=fecha
    ).order_by('hora_inicio')

    if request.method == "POST":
        form = RegistroHorasTecnicoForm(request.POST, tecnico=tecnico)  # Pasar el técnico al formulario
        if form.is_valid():
            registro = form.save(commit=False)
            registro.tecnico = tecnico
            registro.fecha = fecha
            
            # Validar que la actividad sea consistente con el servicio
            if registro.tipo_hora.disponibilidad == 'DISPONIBLE' and registro.tipo_hora.genera_ingreso == 'INGRESO':
                if not registro.servicio:
                    form.add_error('servicio', 'Las horas productivas deben estar asociadas a un servicio.')
                    return render(request, 'gestionDeTaller/tecnicos/registrar_horas.html', {
                        'tecnico': tecnico,
                        'form': form,
                        'fecha': fecha,
                        'registros_previos': registros_previos
                    })
            else:
                registro.servicio = None  # No permitir servicio para horas no productivas
            
            registro.save()
            messages.success(request, "Horas registradas correctamente.")
            
            # Verificar si el usuario quiere continuar registrando
            if request.POST.get('action') == 'save_and_continue':
                return redirect('gestionDeTaller:registrar_horas', tecnico_id=tecnico.id, fecha=fecha_str)
            else:
                return redirect('gestionDeTaller:detalle_tecnico', tecnico_id=tecnico.id)
    else:
        form = RegistroHorasTecnicoForm(tecnico=tecnico)  # Pasar el técnico al formulario

    context = {
        'tecnico': tecnico,
        'form': form,
        'fecha': fecha,
        'registros_previos': registros_previos,
        'actividad': actividad,
    }

    return render(request, 'gestionDeTaller/tecnicos/registrar_horas.html', context)


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from recursosHumanos.models import Usuario, RegistroHorasTecnico
from recursosHumanos.forms import AprobacionHorasForm

@login_required
def revisar_horas(request, tecnico_id, fecha):
    # Verificar que el usuario sea Gerente
    if not request.user.rol == 'GERENTE':
        messages.error(request, "No tienes permiso para aprobar horas.")
        return redirect('gestionDeTaller:detalle_tecnico', tecnico_id=tecnico_id)

    tecnico = get_object_or_404(Usuario, pk=tecnico_id)
    fecha = datetime.strptime(fecha, '%Y-%m-%d').date()

    # Obtener los registros de horas del técnico en la fecha seleccionada
    registros = RegistroHorasTecnico.objects.filter(tecnico=tecnico, fecha=fecha).order_by('hora_inicio')

    if request.method == "POST":
        form = AprobacionHorasForm(request.POST)

        if form.is_valid():
            # Procesar aprobación de horas
            registros.update(aprobado=True, aprobado_por=request.user, fecha_aprobacion=datetime.now())
            messages.success(request, "Horas aprobadas correctamente.")
            return redirect('gestionDeTaller:detalle_tecnico', tecnico_id=tecnico.id)
        else:
            messages.error(request, "Error al aprobar horas.")

    else:
        form = AprobacionHorasForm()

    context = {
        'tecnico': tecnico,
        'fecha': fecha,
        'registros': registros,
        'form': form,
    }

    return render(request, 'gestionDeTaller/tecnicos/revisar_horas.html', context)

@login_required
def lista_revisiones_5s(request):
    revisiones = Revision5S.objects.all().order_by('-fecha_revision')
    return render(request, 'gestionDeTaller/5s/lista_revisiones.html', {'revisiones': revisiones})

@login_required
def crear_revision_5s(request):
    if request.method == 'POST':
        form = Revision5SForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.evaluador = request.user
            revision.save()
            
            # Procesar múltiples evidencias
            evidencias = request.FILES.getlist('evidencias')
            for evidencia in evidencias:
                from .models import EvidenciaRevision5S
                EvidenciaRevision5S.objects.create(
                    revision=revision,
                    imagen=evidencia
                )
            
            messages.success(request, 'Revisión 5S creada exitosamente.')
            return redirect('gestionDeTaller:detalle_revision_5s', revision_id=revision.id)
    else:
        form = Revision5SForm(user=request.user)
    return render(request, 'gestionDeTaller/5s/crear_revision.html', {'form': form})

@login_required
def detalle_revision_5s(request, revision_id):
    revision = get_object_or_404(Revision5S, id=revision_id)
    planes_accion = revision.planes_accion.all()
    evidencias = revision.evidencias.all()
    return render(request, 'gestionDeTaller/5s/detalle_revision.html', {
        'revision': revision,
        'planes_accion': planes_accion,
        'evidencias': evidencias
    })

@login_required
def crear_plan_accion_5s(request, revision_id):
    revision = get_object_or_404(Revision5S, id=revision_id)
    
    # Obtener items no conformes de la revisión
    items_no_conformes = []
    campos_5s = [
        ('bancos_trabajo', 'Bancos de Trabajo'),
        ('herramientas_funcionales', 'Herramientas Funcionales'),
        ('piezas_organizadas', 'Piezas Organizadas'),
        ('herramientas_devueltas', 'Herramientas Devueltas'),
        ('box_limpios', 'Box Limpios'),
        ('sala_garantia', 'Sala Garantía'),
        ('piso_limpio', 'Piso Limpio'),
        ('instrumentos_limpios', 'Instrumentos Limpios'),
        ('paredes_limpias', 'Paredes Limpias'),
        ('personal_uniformado', 'Personal Uniformado'),
        ('epp_usado', 'EPP Usado'),
        ('herramientas_calibradas', 'Herramientas Calibradas'),
        ('residuos_gestionados', 'Residuos Gestionados'),
        ('documentacion_actualizada', 'Documentación Actualizada'),
        ('procedimientos_seguidos', 'Procedimientos Seguidos'),
    ]
    
    for campo, nombre in campos_5s:
        if getattr(revision, campo) == 'NO_CONFORME':
            items_no_conformes.append(nombre)
    
    if request.method == 'POST':
        form = PlanAccion5SForm(request.POST, request.FILES)
        if form.is_valid():
            # Obtener el item no conforme del formulario
            item_no_conforme = form.cleaned_data['item_no_conforme']
            
            # Verificar si hay múltiples items separados por punto y coma
            if ';' in item_no_conforme:
                items = [item.strip() for item in item_no_conforme.split(';')]
                planes_creados = 0
                
                for item in items:
                    if item in items_no_conformes:  # Validar que el item sea válido
                        plan = form.save(commit=False)
                        plan.revision = revision
                        plan.item_no_conforme = item
                        plan.save()
                        planes_creados += 1
                
                if planes_creados > 0:
                    messages.success(request, f'{planes_creados} planes de acción creados exitosamente.')
                else:
                    messages.error(request, 'No se pudieron crear los planes de acción.')
            else:
                # Crear un solo plan de acción
                plan = form.save(commit=False)
                plan.revision = revision
                plan.save()
                messages.success(request, 'Plan de acción creado exitosamente.')
            
            return redirect('gestionDeTaller:detalle_revision_5s', revision_id=revision.id)
    else:
        form = PlanAccion5SForm()
    
    return render(request, 'gestionDeTaller/5s/crear_plan_accion.html', {
        'form': form,
        'revision': revision,
        'items_no_conformes': items_no_conformes
    })

@login_required
def lista_planes_accion_5s(request):
    """
    Vista para listar todos los planes de acción 5S.
    Permite ver el estado de todos los planes de acción y acceder a sus detalles.
    """
    planes_accion = PlanAccion5S.objects.all().order_by('-fecha_limite')
    today = timezone.now().date()
    
    # Paginación
    paginator = Paginator(planes_accion, 10)  # 10 planes por página
    page = request.GET.get('page')
    planes_accion = paginator.get_page(page)
    
    context = {
        'planes_accion': planes_accion,
        'today': today,
    }
    return render(request, 'gestionDeTaller/5s/lista_planes_accion.html', context)

@login_required
def detalle_plan_accion_5s(request, plan_id):
    """
    Vista para mostrar los detalles de un plan de acción 5S específico.
    """
    plan = get_object_or_404(PlanAccion5S, id=plan_id)
    
    context = {
        'plan': plan,
    }
    return render(request, 'gestionDeTaller/5s/detalle_plan_accion.html', context)

@login_required
def editar_plan_accion_5s(request, plan_id):
    """
    Vista para editar un plan de acción 5S existente.
    """
    plan = get_object_or_404(PlanAccion5S, id=plan_id)
    revision = plan.revision
    
    # Obtener todos los items no conformes de la revisión
    items_no_conformes = []
    campos_5s = [
        ('bancos_trabajo', 'Bancos de Trabajo'),
        ('herramientas_funcionales', 'Herramientas Funcionales'),
        ('piezas_organizadas', 'Piezas Organizadas'),
        ('herramientas_devueltas', 'Herramientas Devueltas'),
        ('box_limpios', 'Box Limpios'),
        ('sala_garantia', 'Sala Garantía'),
        ('piso_limpio', 'Piso Limpio'),
        ('instrumentos_limpios', 'Instrumentos Limpios'),
        ('paredes_limpias', 'Paredes Limpias'),
        ('personal_uniformado', 'Personal Uniformado'),
        ('epp_usado', 'EPP Usado'),
        ('herramientas_calibradas', 'Herramientas Calibradas'),
        ('residuos_gestionados', 'Residuos Gestionados'),
        ('documentacion_actualizada', 'Documentación Actualizada'),
        ('procedimientos_seguidos', 'Procedimientos Seguidos'),
    ]
    
    for campo, nombre in campos_5s:
        if getattr(revision, campo) == 'NO_CONFORME':
            items_no_conformes.append((campo, nombre))
    
    if request.method == 'POST':
        # Procesar formulario del plan de acción
        if 'plan_accion' in request.POST:
            form = PlanAccion5SForm(request.POST, request.FILES, instance=plan)
            if form.is_valid():
                form.save()
                messages.success(request, 'Plan de acción actualizado exitosamente.')
                return redirect('gestionDeTaller:detalle_plan_accion_5s', plan_id=plan.id)
        
        # Procesar corrección de items no conformes
        elif 'corregir_items' in request.POST:
            # Guardar puntuación anterior
            puntuacion_anterior = revision.porcentaje_conformidad
            
            # Actualizar los campos de la revisión
            for campo, nombre in items_no_conformes:
                if request.POST.get(f'corregir_{campo}') == 'on':
                    setattr(revision, campo, 'CONFORME')
            
            # Recalcular puntuación
            revision.calcular_conformidad()
            revision.save()
            
            puntuacion_nueva = revision.porcentaje_conformidad
            messages.success(request, f'Items corregidos exitosamente. Puntuación: {puntuacion_anterior}% → {puntuacion_nueva}%')
            return redirect('gestionDeTaller:detalle_plan_accion_5s', plan_id=plan.id)
        
        # Procesar subida de múltiples evidencias
        elif 'subir_evidencias' in request.POST:
            imagenes = request.FILES.getlist('evidencias')
            descripciones = request.POST.getlist('descripciones')
            
            for i, imagen in enumerate(imagenes):
                if imagen:
                    descripcion = descripciones[i] if i < len(descripciones) else ''
                    EvidenciaPlanAccion5S.objects.create(
                        plan_accion=plan,
                        imagen=imagen,
                        descripcion=descripcion
                    )
            
            messages.success(request, f'{len(imagenes)} evidencias subidas exitosamente.')
            return redirect('gestionDeTaller:detalle_plan_accion_5s', plan_id=plan.id)
    else:
        form = PlanAccion5SForm(instance=plan)
    
    # Obtener evidencias existentes
    evidencias = plan.evidencias.all()
    
    context = {
        'form': form,
        'plan': plan,
        'revision': revision,
        'items_no_conformes': items_no_conformes,
        'evidencias': evidencias,
    }
    return render(request, 'gestionDeTaller/5s/editar_plan_accion.html', context)

# Vistas para encuestas
@login_required
def lista_encuestas(request):
    # Verificar que el usuario sea Gerente o Administrativo
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Obtener servicios completados sin encuesta
    servicios = Servicio.objects.filter(
        estado='COMPLETADO',
        encuestas__isnull=True
    ).order_by('-fecha_servicio')
    
    # Obtener encuestas enviadas
    encuestas_enviadas = EncuestaServicio.objects.all().order_by('-fecha_envio')
    
    # Calcular estadísticas NPS
    respuestas = RespuestaEncuesta.objects.all()
    promotores_count = respuestas.filter(probabilidad_recomendacion__gte=9).count()
    pasivos_count = respuestas.filter(probabilidad_recomendacion__gte=7, probabilidad_recomendacion__lt=9).count()
    detractores_count = respuestas.filter(probabilidad_recomendacion__lt=7).count()
    
    # Calcular promedio NPS
    nps_promedio = respuestas.aggregate(Avg('probabilidad_recomendacion'))['probabilidad_recomendacion__avg'] or 0
    
    context = {
        'servicios': servicios,
        'encuestas_enviadas': encuestas_enviadas,
        'promotores_count': promotores_count,
        'pasivos_count': pasivos_count,
        'detractores_count': detractores_count,
        'nps_promedio': nps_promedio,
    }
    return render(request, 'gestionDeTaller/encuestas/lista_encuestas.html', context)

@login_required
def enviar_encuesta(request, servicio_id):
    # Verificar que el usuario sea Gerente o Administrativo
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    try:
        servicio = Servicio.objects.get(id=servicio_id)
        cliente = servicio.preorden.cliente
        destinatarios_existentes = [cliente.email] if cliente.email else []
        contactos = cliente.contactos.all()
        destinatarios_existentes += [contacto.email for contacto in contactos if contacto.email]

        if request.method == 'POST':
            emails_seleccionados = request.POST.getlist('emails[]')
            nuevo_correo = request.POST.get('nuevo_correo')
            mensaje_correo = request.POST.get('mensaje_correo', '')

            if nuevo_correo:
                emails_seleccionados.append(nuevo_correo)

            if emails_seleccionados:
                # Crear la encuesta
                encuesta = EncuestaServicio.objects.create(servicio=servicio)
                
                # Enviar el correo
                asunto = f"Encuesta de Satisfacción - Servicio #{servicio.id}"
                email = EmailMultiAlternatives(
                    asunto,
                    strip_tags(mensaje_correo),
                    to=emails_seleccionados,
                    cc=settings.CC_EMAILS
                )
                email.attach_alternative(mensaje_correo, "text/html")
                email.send()

                # Actualizar el servicio
                servicio.encuesta_enviada = True
                servicio.fecha_envio_encuesta = timezone.now()
                servicio.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Encuesta enviada exitosamente.'
                    })
                else:
                    messages.success(request, "Encuesta enviada exitosamente.")
                    return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio_id)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'No se pudo enviar la encuesta.'
            })
        else:
            context = {
                'servicio': servicio,
                'destinatarios_existentes': destinatarios_existentes
            }
            return render(request, 'gestionDeTaller/enviar_encuesta.html', context)

    except Servicio.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'El servicio no existe.'
            })
        else:
            messages.error(request, "El servicio no existe.")
            return redirect('gestionDeTaller:lista_servicios')

@login_required
def estadisticas_encuestas(request):
    # Verificar que el usuario sea Gerente o Administrativo
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    encuestas = EncuestaServicio.objects.all().order_by('-fecha_envio')
    
    context = {
        'encuestas': encuestas
    }
    return render(request, 'gestionDeTaller/encuestas/estadisticas.html', context)

@login_required
def reenviar_encuesta(request, encuesta_id):
    # Verificar que el usuario sea Gerente o Administrativo
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    try:
        encuesta = EncuestaServicio.objects.get(id=encuesta_id)
        servicio = encuesta.servicio
        cliente = servicio.preorden.cliente
        
        # Obtener destinatarios
        destinatarios = [cliente.email] if cliente.email else []
        for contacto in cliente.contactos.all():
            if contacto.email:
                destinatarios.append(contacto.email)
        
        if not destinatarios:
            messages.error(request, 'No hay direcciones de correo disponibles para este cliente.')
            return redirect('gestionDeTaller:lista_encuestas')
        
        # Crear mensaje de correo
        mensaje_correo = f"""
        <html>
        <body>
            <h2>Encuesta de Satisfacción - Servicio #{servicio.id}</h2>
            <p>Estimado cliente,</p>
            <p>Le enviamos nuevamente la encuesta de satisfacción para el servicio realizado en su equipo.</p>
            <p><strong>Detalles del servicio:</strong></p>
            <ul>
                <li><strong>Cliente:</strong> {cliente.razon_social}</li>
                <li><strong>Equipo:</strong> {servicio.preorden.equipo.numero_serie}</li>
                <li><strong>Fecha de servicio:</strong> {servicio.fecha_servicio.strftime('%d/%m/%Y')}</li>
            </ul>
            <p>Por favor, complete la encuesta para ayudarnos a mejorar nuestros servicios.</p>
            <p>Gracias por su tiempo.</p>
        </body>
        </html>
        """
        
        # Enviar el correo
        asunto = f"Encuesta de Satisfacción - Servicio #{servicio.id} (Reenvío)"
        email = EmailMultiAlternatives(
            asunto,
            strip_tags(mensaje_correo),
            to=destinatarios,
            cc=settings.CC_EMAILS
        )
        email.attach_alternative(mensaje_correo, "text/html")
        email.send()
        
        # Actualizar fecha de envío
        encuesta.fecha_envio = timezone.now()
        encuesta.save()
        
        messages.success(request, 'Encuesta reenviada exitosamente.')
        return redirect('gestionDeTaller:lista_encuestas')
        
    except EncuestaServicio.DoesNotExist:
        messages.error(request, 'La encuesta no existe.')
        return redirect('gestionDeTaller:lista_encuestas')
    except Exception as e:
        messages.error(request, f'Error al reenviar la encuesta: {str(e)}')
        return redirect('gestionDeTaller:lista_encuestas')

@login_required
def cargar_respuesta_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(EncuestaServicio, id=encuesta_id)
    servicio = encuesta.servicio
    
    if request.method == 'POST':
        form = RespuestaEncuestaForm(request.POST)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.encuesta = encuesta
            respuesta.save()
            # Actualizar el estado y la fecha de respuesta de la encuesta
            encuesta.estado = 'RESPONDIDA'
            encuesta.fecha_respuesta = respuesta.fecha_respuesta
            encuesta.save()
            messages.success(request, 'Respuesta guardada exitosamente.')
            return redirect('gestionDeTaller:lista_encuestas')
    else:
        form = RespuestaEncuestaForm()
    
    return render(request, 'gestionDeTaller/encuestas/cargar_respuesta.html', {
        'form': form,
        'servicio': servicio,
        'encuesta': encuesta,
    })

@login_required
def ver_respuesta_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(EncuestaServicio, id=encuesta_id)
    respuesta = encuesta.respuestas.first()  # Obtener la primera respuesta
    
    if not respuesta:
        messages.warning(request, 'Esta encuesta aún no tiene respuesta.')
        return redirect('gestionDeTaller:lista_encuestas')
    
    context = {
        'encuesta': encuesta,
        'respuesta': respuesta,
        'servicio': encuesta.servicio
    }
    return render(request, 'gestionDeTaller/encuestas/ver_respuesta.html', context)

@login_required
def registrar_insatisfaccion(request, encuesta_id):
    encuesta = get_object_or_404(EncuestaServicio, id=encuesta_id)
    
    # Verificar si la encuesta tiene una respuesta con calificación de detractor
    respuesta = encuesta.respuestas.first()
    if not respuesta or respuesta.probabilidad_recomendacion >= 7:
        messages.error(request, 'Solo se pueden registrar insatisfacciones para encuestas con probabilidad de recomendación menor a 7.')
        return redirect('gestionDeTaller:lista_encuestas')
    
    if request.method == 'POST':
        form = InsatisfaccionClienteForm(request.POST)
        if form.is_valid():
            insatisfaccion = form.save(commit=False)
            insatisfaccion.encuesta = encuesta
            insatisfaccion.save()
            messages.success(request, 'Insatisfacción registrada exitosamente.')
            return redirect('gestionDeTaller:lista_encuestas')
    else:
        form = InsatisfaccionClienteForm()
    
    context = {
        'form': form,
        'encuesta': encuesta,
        'respuesta': respuesta
    }
    return render(request, 'gestionDeTaller/encuestas/registrar_insatisfaccion.html', context)

@login_required
def ver_insatisfaccion(request, insatisfaccion_id):
    insatisfaccion = get_object_or_404(InsatisfaccionCliente, id=insatisfaccion_id)
    return render(request, 'gestionDeTaller/encuestas/ver_insatisfaccion.html', {'insatisfaccion': insatisfaccion})

@login_required
def editar_insatisfaccion(request, insatisfaccion_id):
    insatisfaccion = get_object_or_404(InsatisfaccionCliente, id=insatisfaccion_id)
    
    if request.method == 'POST':
        form = InsatisfaccionClienteForm(request.POST, instance=insatisfaccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insatisfacción actualizada exitosamente.')
            return redirect('gestionDeTaller:lista_encuestas')
    else:
        form = InsatisfaccionClienteForm(instance=insatisfaccion)
    
    context = {
        'form': form,
        'insatisfaccion': insatisfaccion
    }
    return render(request, 'gestionDeTaller/encuestas/editar_insatisfaccion.html', context)

@login_required
def lista_insatisfacciones(request):
    # Verificar que el usuario sea Gerente o Administrativo
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')

    # Obtener todas las insatisfacciones ordenadas por fecha de creación
    insatisfacciones = InsatisfaccionCliente.objects.all().order_by('-fecha_creacion')
    
    # Contar insatisfacciones por estado
    estados = {
        'PENDIENTE': insatisfacciones.filter(estado='PENDIENTE').count(),
        'EN_PROCESO': insatisfacciones.filter(estado='EN_PROCESO').count(),
        'RESUELTO': insatisfacciones.filter(estado='RESUELTO').count(),
        'CERRADO': insatisfacciones.filter(estado='CERRADO').count(),
    }
    
    context = {
        'insatisfacciones': insatisfacciones,
        'estados': estados,
    }
    
    return render(request, 'gestionDeTaller/encuestas/lista_insatisfacciones.html', context)

@login_required
def historial_cambios_servicio(request, servicio_id):
    """Vista para mostrar el historial de cambios de estado de un servicio"""
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    # Obtener el historial de cambios
    logs_cambios = servicio.logs_cambios.all().order_by('-fecha_cambio')
    
    # Obtener usuarios únicos que han hecho cambios
    usuarios_unicos = logs_cambios.values_list('usuario__nombre', flat=True).distinct()
    
    context = {
        'servicio': servicio,
        'logs_cambios': logs_cambios,
        'usuarios_unicos': usuarios_unicos,
    }
    
    return render(request, 'gestionDeTaller/servicios/historial_cambios.html', context)

@login_required
def cambiar_estado_servicio(request, servicio_id):
    """Vista para cambiar el estado de un servicio con validaciones"""
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        motivo = request.POST.get('motivo', '')
        
        if nuevo_estado:
            # Usar el método del modelo para cambiar estado
            exito, mensaje = servicio.cambiar_estado(nuevo_estado, request.user, motivo)
            
            if exito:
                messages.success(request, mensaje)
            else:
                messages.error(request, mensaje)
        
        return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio.id)
    
    # Obtener estados disponibles
    from .security import obtener_estados_disponibles
    estados_disponibles = obtener_estados_disponibles(request.user, servicio)
    
    context = {
        'servicio': servicio,
        'estados_disponibles': estados_disponibles,
        'estados_choices': servicio.ESTADO_CHOICES,
    }
    
    return render(request, 'gestionDeTaller/servicios/cambiar_estado.html', context)

@login_required
def historial_cambios_informe(request, servicio_id):
    """Vista para mostrar el historial de cambios del informe de un servicio"""
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    # Obtener el historial de cambios del informe
    from .security import obtener_cambios_informe, obtener_usuarios_cambios_informe
    logs_cambios = obtener_cambios_informe(servicio)
    usuarios_unicos = obtener_usuarios_cambios_informe(servicio)
    
    context = {
        'servicio': servicio,
        'logs_cambios': logs_cambios,
        'usuarios_unicos': usuarios_unicos,
    }
    
    return render(request, 'gestionDeTaller/servicios/historial_cambios_informe.html', context)


@login_required
def agregar_observacion(request, servicio_id):
    """Vista para agregar una nueva observación a un servicio"""
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        observacion_texto = request.POST.get('observacion', '').strip()
        
        if observacion_texto:
            ObservacionServicio.objects.create(
                servicio=servicio,
                usuario=request.user,
                observacion=observacion_texto
            )
            messages.success(request, 'Observación agregada exitosamente.')
        else:
            messages.error(request, 'La observación no puede estar vacía.')
    
    return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio_id)


@login_required
def eliminar_observacion(request, observacion_id):
    """Vista para eliminar una observación"""
    observacion = get_object_or_404(ObservacionServicio, id=observacion_id)
    servicio_id = observacion.servicio.id
    
    # Verificar que el usuario sea el creador de la observación o tenga permisos de administrador
    if request.user == observacion.usuario or request.user.rol in ['GERENTE', 'ADMINISTRACION']:
        observacion.delete()
        messages.success(request, 'Observación eliminada exitosamente.')
    else:
        messages.error(request, 'No tienes permisos para eliminar esta observación.')
    
    return redirect('gestionDeTaller:detalle_servicio', servicio_id=servicio_id)

@login_required
def calendario_semanal_tecnicos(request):
    """Vista para el calendario semanal por técnicos"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Obtener la semana actual o la semana seleccionada
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_actual = timezone.now().date()
    else:
        fecha_actual = timezone.now().date()
    
    # Calcular el lunes de la semana
    lunes = fecha_actual - timedelta(days=fecha_actual.weekday())
    sabado = lunes + timedelta(days=5)  # Sábado
    
    # Obtener todos los técnicos
    tecnicos = Usuario.objects.filter(rol='TECNICO', is_active=True).order_by('apellido', 'nombre')
    
    # Obtener las preórdenes para la semana
    preordenes = PreOrden.objects.filter(
        fecha_estimada__range=[lunes, sabado],
        activo=True
    ).prefetch_related('tecnicos', 'cliente', 'equipo')
    
    # Obtener los servicios en proceso (no completados) que deben mostrarse todos los días
    # Los servicios en proceso se muestran desde su fecha de creación hasta que se completen
    # Mostrar servicios EN_PROCESO y PROGRAMADO (excluir ESPERA_REPUESTOS y A_FACTURAR)
    servicios = Servicio.objects.filter(
        estado__in=['PROGRAMADO', 'EN_PROCESO']
    ).prefetch_related('preorden__tecnicos', 'preorden__cliente', 'preorden__equipo')
    
    # Crear diccionario de elementos por técnico y fecha
    calendario_tecnicos = {}
    
    for tecnico in tecnicos:
        calendario_tecnicos[tecnico.id] = {
            'tecnico': tecnico,
            'dias': {}
        }
        
        # Inicializar cada día de la semana
        for i in range(6):  # Lunes a Sábado
            fecha = lunes + timedelta(days=i)
            calendario_tecnicos[tecnico.id]['dias'][fecha] = {
                'preordenes': [],
                'servicios_programados': [],
                'servicios_en_proceso': []
            }
    
    # Crear un conjunto de preórdenes que tienen servicios asociados
    preordenes_con_servicios = set()
    for servicio in servicios:
        preordenes_con_servicios.add(servicio.preorden.numero)
    
    # Asignar preórdenes a los técnicos correspondientes (solo en su fecha estimada)
    # Solo mostrar preórdenes que NO tienen servicios asociados
    for preorden in preordenes:
        # Solo agregar la preorden si no tiene servicios asociados
        if preorden.numero not in preordenes_con_servicios:
            for tecnico in preorden.tecnicos.all():
                if tecnico.id in calendario_tecnicos:
                    fecha = preorden.fecha_estimada
                    if fecha in calendario_tecnicos[tecnico.id]['dias']:
                        calendario_tecnicos[tecnico.id]['dias'][fecha]['preordenes'].append(preorden)
    
    # Asignar servicios a los técnicos correspondientes (todos los días hasta completarse)
    for servicio in servicios:
        for tecnico in servicio.preorden.tecnicos.all():
            if tecnico.id in calendario_tecnicos:
                # Los servicios se muestran todos los días de la semana hasta ser completados
                for i in range(6):  # Lunes a Sábado
                    fecha = lunes + timedelta(days=i)
                    if fecha in calendario_tecnicos[tecnico.id]['dias']:
                        if servicio.estado == 'PROGRAMADO':
                            calendario_tecnicos[tecnico.id]['dias'][fecha]['servicios_programados'].append(servicio)
                        elif servicio.estado == 'EN_PROCESO':
                            calendario_tecnicos[tecnico.id]['dias'][fecha]['servicios_en_proceso'].append(servicio)
    
    # Calcular fechas de navegación
    semana_anterior = lunes - timedelta(days=7)
    semana_siguiente = lunes + timedelta(days=7)
    
    # Nombres de los días
    nombres_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    context = {
        'calendario_tecnicos': calendario_tecnicos,
        'lunes': lunes,
        'sabado': sabado,
        'nombres_dias': nombres_dias,
        'semana_anterior': semana_anterior,
        'semana_siguiente': semana_siguiente,
        'fecha_actual': fecha_actual,
    }
    
    return render(request, 'gestionDeTaller/preorden/calendario_semanal_tecnicos.html', context)


@login_required
def gestionar_repuestos(request):
    """Vista para gestionar repuestos"""
    
    # Solo gerentes y administrativos pueden gestionar repuestos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para gestionar repuestos.')
        return redirect('gestionDeTaller:lista_servicios')
    
    # Obtener repuestos con filtros
    repuestos = Repuesto.objects.all()
    
    # Aplicar filtros
    search = request.GET.get('search')
    categoria = request.GET.get('categoria')
    proveedor = request.GET.get('proveedor')
    activo = request.GET.get('activo')
    
    if search:
        repuestos = repuestos.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(categoria__icontains=search) |
            Q(proveedor__icontains=search)
        )
    
    if categoria:
        repuestos = repuestos.filter(categoria__icontains=categoria)
    
    if proveedor:
        repuestos = repuestos.filter(proveedor__icontains=proveedor)
    
    if activo is not None:
        repuestos = repuestos.filter(activo=activo == 'true')
    
    # Ordenar por código
    repuestos = repuestos.order_by('codigo')
    
    # Paginación
    paginator = Paginator(repuestos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener categorías y proveedores únicos para los filtros
    categorias_unicas = Repuesto.objects.values_list('categoria', flat=True).distinct().exclude(categoria='').order_by('categoria')
    proveedores_unicos = Repuesto.objects.values_list('proveedor', flat=True).distinct().exclude(proveedor='').order_by('proveedor')
    
    context = {
        'page_obj': page_obj,
        'search_filtro': search,
        'categoria_filtro': categoria,
        'proveedor_filtro': proveedor,
        'activo_filtro': activo,
        'categorias_unicas': categorias_unicas,
        'proveedores_unicos': proveedores_unicos,
    }
    
    return render(request, 'gestionDeTaller/gestionar_repuestos.html', context)

@login_required
def crear_repuesto(request):
    """Vista para crear un nuevo repuesto"""
    
    # Solo gerentes y administrativos pueden crear repuestos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear repuestos.'})
    
    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            descripcion = request.POST.get('descripcion', '')
            costo = request.POST.get('costo')
            precio_venta = request.POST.get('precio_venta')
            categoria = request.POST.get('categoria', '')
            proveedor = request.POST.get('proveedor', '')
            
            # Validaciones
            if not all([codigo, precio_venta]):
                return JsonResponse({'success': False, 'message': 'El código y precio de venta son obligatorios.'})
            
            # Verificar si el código ya existe
            if Repuesto.objects.filter(codigo=codigo).exists():
                return JsonResponse({'success': False, 'message': f'El código {codigo} ya existe en la base de datos.'})
            
            # Crear el repuesto
            nuevo_repuesto = Repuesto(
                codigo=codigo,
                descripcion=descripcion,
                costo=float(costo) if costo else None,
                precio_venta=float(precio_venta),
                categoria=categoria,
                proveedor=proveedor,
                creado_por=request.user
            )
            nuevo_repuesto.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Repuesto {codigo} creado exitosamente.',
                'repuesto_id': nuevo_repuesto.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error al crear el repuesto: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

@login_required
def obtener_repuesto(request):
    """Vista para obtener información de un repuesto específico (AJAX)"""
    codigo = request.GET.get('codigo')
    
    if not codigo:
        return JsonResponse({'success': False, 'message': 'Código de repuesto requerido'})
    
    try:
        # Buscar el repuesto
        repuesto = Repuesto.objects.filter(
            codigo=codigo,
            activo=True
        ).first()
        
        if repuesto:
            return JsonResponse({
                'success': True,
                'repuesto': {
                    'codigo': repuesto.codigo,
                    'descripcion': repuesto.descripcion,
                    'costo': float(repuesto.costo) if repuesto.costo else None,
                    'precio_venta': float(repuesto.precio_venta),
                    'categoria': repuesto.categoria,
                    'proveedor': repuesto.proveedor,
                }
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': f'Repuesto {codigo} no encontrado en la base de datos'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al buscar repuesto: {str(e)}'})

@login_required
def obtener_lista_repuestos(request):
    """Vista API para obtener lista de repuestos (AJAX)"""
    try:
        repuestos = Repuesto.objects.filter(activo=True).values(
            'codigo', 'descripcion', 'costo', 'precio_venta', 'categoria', 'proveedor'
        ).order_by('codigo')
        
        return JsonResponse({
            'success': True,
            'repuestos': list(repuestos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener repuestos: {str(e)}'})

# Vistas para Herramientas Especiales
@login_required
def herramientas_especiales_list(request):
    """Lista de herramientas especiales"""
    herramientas = HerramientaEspecial.objects.all()
    
    # Filtros
    codigo_filtro = request.GET.get('codigo', '')
    ubicacion_filtro = request.GET.get('ubicacion', '')
    disponible_filtro = request.GET.get('disponible', '')
    
    if codigo_filtro:
        herramientas = herramientas.filter(codigo__icontains=codigo_filtro)
    
    if ubicacion_filtro:
        herramientas = herramientas.filter(ubicacion__icontains=ubicacion_filtro)
    
    if disponible_filtro == 'disponible':
        herramientas = [h for h in herramientas if h.disponible]
    elif disponible_filtro == 'no_disponible':
        herramientas = [h for h in herramientas if not h.disponible]
    
    # Paginación
    paginator = Paginator(herramientas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'codigo_filtro': codigo_filtro,
        'ubicacion_filtro': ubicacion_filtro,
        'disponible_filtro': disponible_filtro,
    }
    
    return render(request, 'gestionDeTaller/herramientas_especiales_list.html', context)


@login_required
def herramienta_especial_detail(request, herramienta_id):
    """Detalle de una herramienta especial"""
    herramienta = get_object_or_404(HerramientaEspecial, id=herramienta_id)
    
    # Obtener reservas activas
    reservas_activas = herramienta.reservas.filter(
        estado__in=['RESERVADA', 'RETIRADA']
    ).order_by('-fecha_reserva')
    
    # Obtener historial de logs
    logs = herramienta.logs.all()[:20]  # Últimos 20 logs
    
    # Obtener pre-órdenes y servicios para el formulario de reserva
    preordenes = PreOrden.objects.filter(activo=True)
    servicios = Servicio.objects.filter(estado__in=['PROGRAMADO', 'EN_PROCESO'])
    
    context = {
        'herramienta': herramienta,
        'reservas_activas': reservas_activas,
        'logs': logs,
        'preordenes': preordenes,
        'servicios': servicios,
    }
    
    return render(request, 'gestionDeTaller/herramienta_especial_detail.html', context)


@login_required
def reservar_herramienta(request, herramienta_id):
    """Reservar una herramienta especial"""
    herramienta = get_object_or_404(HerramientaEspecial, id=herramienta_id)
    
    if request.method == 'POST':
        fecha_reserva = request.POST.get('fecha_reserva')
        preorden_id = request.POST.get('preorden')
        servicio_id = request.POST.get('servicio')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Verificar si ya está reservada para esa fecha
            if herramienta.reservas.filter(
                fecha_reserva=fecha_reserva,
                estado__in=['RESERVADA', 'RETIRADA']
            ).exists():
                messages.error(request, 'La herramienta ya está reservada para esa fecha.')
                return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=herramienta.id)
            
            # Crear la reserva
            reserva = ReservaHerramienta.objects.create(
                herramienta=herramienta,
                usuario=request.user,
                fecha_reserva=fecha_reserva,
                preorden_id=preorden_id if preorden_id else None,
                servicio_id=servicio_id if servicio_id else None,
                observaciones=observaciones
            )
            
            # Crear log
            LogHerramienta.objects.create(
                herramienta=herramienta,
                usuario=request.user,
                accion='RESERVA',
                reserva=reserva,
                observaciones=f"Herramienta reservada para {fecha_reserva} por {request.user.get_full_name() or request.user.username}"
            )
            
            messages.success(request, f'Herramienta {herramienta.codigo} reservada exitosamente.')
            return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=herramienta.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear la reserva: {str(e)}')
    
    return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=herramienta.id)


@login_required
def retirar_herramienta(request, reserva_id):
    """Marcar herramienta como retirada"""
    reserva = get_object_or_404(ReservaHerramienta, id=reserva_id)
    
    if request.method == 'POST':
        try:
            reserva.marcar_retirada()
            messages.success(request, f'Herramienta {reserva.herramienta.codigo} marcada como retirada.')
        except Exception as e:
            messages.error(request, f'Error al marcar como retirada: {str(e)}')
    
    return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=reserva.herramienta.id)


@login_required
def devolver_herramienta(request, reserva_id):
    """Marcar herramienta como devuelta"""
    reserva = get_object_or_404(ReservaHerramienta, id=reserva_id)
    
    if request.method == 'POST':
        try:
            reserva.marcar_devuelta()
            messages.success(request, f'Herramienta {reserva.herramienta.codigo} marcada como devuelta.')
        except Exception as e:
            messages.error(request, f'Error al marcar como devuelta: {str(e)}')
    
    return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=reserva.herramienta.id)


@login_required
def cancelar_reserva(request, reserva_id):
    """Cancelar una reserva"""
    reserva = get_object_or_404(ReservaHerramienta, id=reserva_id)
    
    if request.method == 'POST':
        try:
            reserva.estado = 'CANCELADA'
            reserva.save()
            
            # Crear log
            LogHerramienta.objects.create(
                herramienta=reserva.herramienta,
                usuario=request.user,
                accion='CANCELACION',
                reserva=reserva,
                observaciones=f"Reserva cancelada por {request.user.get_full_name() or request.user.username}"
            )
            
            messages.success(request, f'Reserva de {reserva.herramienta.codigo} cancelada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al cancelar la reserva: {str(e)}')
    
    return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=reserva.herramienta.id)


@login_required
def retirar_sin_reserva(request, herramienta_id):
    """Retirar herramienta sin reserva previa"""
    herramienta = get_object_or_404(HerramientaEspecial, id=herramienta_id)
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Crear reserva con estado RETIRADA
            reserva = ReservaHerramienta.objects.create(
                herramienta=herramienta,
                usuario=request.user,
                fecha_reserva=timezone.now().date(),
                estado='RETIRADA',
                fecha_retiro=timezone.now(),
                observaciones=observaciones
            )
            
            # Crear log
            LogHerramienta.objects.create(
                herramienta=herramienta,
                usuario=request.user,
                accion='RETIRO',
                reserva=reserva,
                observaciones=f"Retiro sin reserva previa por {request.user.get_full_name() or request.user.username} - {observaciones}"
            )
            
            messages.success(request, f'Herramienta {herramienta.codigo} retirada sin reserva previa.')
        except Exception as e:
            messages.error(request, f'Error al retirar la herramienta: {str(e)}')
    
    return redirect('gestionDeTaller:herramienta_especial_detail', herramienta_id=herramienta.id)

@login_required
def importar_herramientas_especiales(request):
    """Vista para importar herramientas especiales desde Excel"""
    if request.method == 'POST':
        try:
            # Verificar que se haya subido un archivo
            if 'archivo_excel' not in request.FILES:
                messages.error(request, 'Por favor seleccione un archivo Excel.')
                return render(request, 'gestionDeTaller/importar_herramientas_especiales.html')
            
            archivo = request.FILES['archivo_excel']
            
            # Verificar que sea un archivo Excel
            if not archivo.name.endswith(('.xlsx', '.xls')):
                messages.error(request, 'Por favor seleccione un archivo Excel válido (.xlsx o .xls).')
                return render(request, 'gestionDeTaller/importar_herramientas_especiales.html')
            
            # Leer el archivo Excel
            df = pd.read_excel(archivo)
            
            # Verificar que tenga las columnas necesarias
            columnas_requeridas = ['CODIGO ( Ver Notas p/descripcion)', 'ITEMS', 'CANTIDAD', 'UBICACION', 'IMAGEN']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                messages.error(request, f'El archivo Excel debe contener las siguientes columnas: {", ".join(columnas_faltantes)}')
                return render(request, 'gestionDeTaller/importar_herramientas_especiales.html')
            
            # Procesar los datos
            herramientas_creadas = 0
            herramientas_actualizadas = 0
            errores = []
            
            for index, row in df.iterrows():
                try:
                    codigo = str(row['CODIGO ( Ver Notas p/descripcion)']).strip()
                    if pd.isna(codigo) or codigo == '':
                        continue
                    
                    # Obtener o crear la herramienta
                    herramienta, created = HerramientaEspecial.objects.get_or_create(
                        codigo=codigo,
                        defaults={
                            'nombre': str(row['ITEMS']) if not pd.isna(row['ITEMS']) else f'Herramienta {codigo}',
                            'cantidad': int(row['CANTIDAD']) if not pd.isna(row['CANTIDAD']) else 1,
                            'ubicacion': str(row['UBICACION']) if not pd.isna(row['UBICACION']) else 'Sin ubicación',
                            'nota': f'Importado desde Excel - Fila {index + 2}',
                            'creado_por': request.user
                        }
                    )
                    
                    if created:
                        herramientas_creadas += 1
                    else:
                        # Actualizar datos existentes
                        herramienta.nombre = str(row['ITEMS']) if not pd.isna(row['ITEMS']) else f'Herramienta {codigo}'
                        herramienta.cantidad = int(row['CANTIDAD']) if not pd.isna(row['CANTIDAD']) else 1
                        herramienta.ubicacion = str(row['UBICACION']) if not pd.isna(row['UBICACION']) else 'Sin ubicación'
                        herramienta.save()
                        herramientas_actualizadas += 1
                    
                    # Procesar imagen si existe
                    nombre_imagen = str(row['IMAGEN']) if not pd.isna(row['IMAGEN']) else None
                    if nombre_imagen and nombre_imagen != 'nan':
                        # Aquí podrías implementar la lógica para copiar las imágenes
                        # Por ahora solo registramos que existe una imagen
                        if not herramienta.nota:
                            herramienta.nota = f'Imagen: {nombre_imagen}'
                        else:
                            herramienta.nota += f' | Imagen: {nombre_imagen}'
                        herramienta.save()
                        
                except Exception as e:
                    errores.append(f'Fila {index + 2}: {str(e)}')
            
            # Mostrar resultados
            if herramientas_creadas > 0:
                messages.success(request, f'Se crearon {herramientas_creadas} herramientas nuevas.')
            
            if herramientas_actualizadas > 0:
                messages.info(request, f'Se actualizaron {herramientas_actualizadas} herramientas existentes.')
            
            if errores:
                for error in errores[:10]:  # Mostrar solo los primeros 10 errores
                    messages.warning(request, error)
                if len(errores) > 10:
                    messages.warning(request, f'... y {len(errores) - 10} errores más.')
            
            return redirect('gestionDeTaller:herramientas_especiales_list')
            
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
    
    return render(request, 'gestionDeTaller/importar_herramientas_especiales.html')


# Personal Tools Views
@login_required
def personal_tools_list(request):
    """Lista de herramientas personales"""
    tools = HerramientaPersonal.objects.select_related('creado_por').all()
    
    # Filtros
    categoria_id = request.GET.get('categoria')
    estado = request.GET.get('estado')
    tecnico_id = request.GET.get('tecnico')
    
    if categoria_id:
        tools = tools.filter(categoria=categoria_id)
    if estado:
        tools = tools.filter(estado=estado)
    if tecnico_id:
        tools = tools.filter(asignacion_actual__tecnico_id=tecnico_id)
    
    categorias = HerramientaPersonal.CATEGORIA_CHOICES
    tecnicos = Usuario.objects.filter(rol='TECNICO').order_by('first_name', 'last_name')
    
    # Calcular estadísticas
    total_herramientas = tools.count()
    herramientas_asignadas = tools.filter(estado='ASIGNADA').count()
    herramientas_disponibles = tools.filter(estado='DISPONIBLE').count()
    herramientas_mantenimiento = tools.filter(estado='MANTENIMIENTO').count()
    
    # Estadísticas de certificación
    herramientas_certificacion_vencida = tools.filter(
        fecha_vencimiento_certificacion__lt=timezone.now().date()
    ).count()
    herramientas_certificacion_proxima_vencer = tools.filter(
        fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento_certificacion__gt=timezone.now().date()
    ).count()
    
    context = {
        'tools': tools,
        'categorias': categorias,
        'tecnicos': tecnicos,
        'estados': HerramientaPersonal.ESTADO_CHOICES,
        'total_herramientas': total_herramientas,
        'herramientas_asignadas': herramientas_asignadas,
        'herramientas_disponibles': herramientas_disponibles,
        'herramientas_mantenimiento': herramientas_mantenimiento,
        'herramientas_certificacion_vencida': herramientas_certificacion_vencida,
        'herramientas_certificacion_proxima_vencer': herramientas_certificacion_proxima_vencer,
    }
    return render(request, 'gestionDeTaller/personal_tools/list.html', context)

@login_required
def personal_tool_detail(request, tool_id):
    """Detalle de herramienta personal"""
    try:
        tool = HerramientaPersonal.objects.select_related(
            'creado_por'
        ).prefetch_related(
            'asignaciones__tecnico',
            'asignaciones__asignado_por'
        ).get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('personal_tools_list')
    
    # Obtener auditorías a través de DetalleAuditoriaHerramienta
    from .models import DetalleAuditoriaHerramienta
    detalles_auditoria = DetalleAuditoriaHerramienta.objects.filter(
        herramienta=tool
    ).select_related(
        'auditoria__auditor',
        'auditoria__tecnico'
    ).order_by('-auditoria__fecha_auditoria')
    
    # Obtener auditorías realizadas sobre la herramienta
    auditorias = AuditoriaHerramientaPersonal.objects.filter(
        detalles_auditoria__herramienta=tool
    ).distinct().select_related(
        'auditor',
        'tecnico'
    ).order_by('-fecha_auditoria')
    
    # Debug: Imprimir información sobre las auditorías encontradas
    print(f"DEBUG: Herramienta ID: {tool.id}, Nombre: {tool.nombre}")
    print(f"DEBUG: Auditorías encontradas: {auditorias.count()}")
    for aud in auditorias:
        print(f"DEBUG: Auditoría ID: {aud.id}, Tipo: {aud.tipo_auditoria}, Fecha: {aud.fecha_auditoria}")
    
    context = {
        'tool': tool,
        'asignaciones': tool.asignaciones.all().order_by('-fecha_asignacion'),
        'auditorias': auditorias,
        'detalles_auditoria': detalles_auditoria,
    }
    return render(request, 'gestionDeTaller/personal_tools/detail.html', context)

@login_required
def assign_personal_tool(request, tool_id):
    """Asignar herramienta personal a técnico"""
    try:
        tool = HerramientaPersonal.objects.get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('gestionDeTaller:personal_tools_list')
    
    if request.method == 'POST':
        tecnico_id = request.POST.get('tecnico')
        fecha_asignacion = request.POST.get('fecha_asignacion')
        observaciones = request.POST.get('observaciones', '')
        
        if not tecnico_id or not fecha_asignacion:
            messages.error(request, 'Todos los campos son obligatorios')
        else:
            try:
                tecnico = Usuario.objects.get(id=tecnico_id)
                
                # Finalizar asignación actual si existe
                if tool.asignacion_actual:
                    asignacion_actual = tool.asignacion_actual
                    asignacion_actual.fecha_devolucion = timezone.now().date()
                    asignacion_actual.estado = 'DEVUELTA'
                    asignacion_actual.save()
                
                # Crear nueva asignación
                nueva_asignacion = AsignacionHerramientaPersonal.objects.create(
                    herramienta=tool,
                    tecnico=tecnico,
                    fecha_asignacion=fecha_asignacion,
                    observaciones_asignacion=observaciones,
                    estado_asignacion='ENTREGADA',
                    asignado_por=request.user
                )
                
                # Actualizar estado de la herramienta
                tool.estado = 'ASIGNADA'
                tool.save()
                
                messages.success(request, f'Herramienta asignada exitosamente a {tecnico.get_full_name()}')
                return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
                
            except Usuario.DoesNotExist:
                messages.error(request, 'Técnico no encontrado')
    
    tecnicos = Usuario.objects.filter(rol='TECNICO').order_by('first_name', 'last_name')
    context = {
        'tool': tool,
        'tecnicos': tecnicos,
    }
    return render(request, 'gestionDeTaller/personal_tools/assign.html', context)

@login_required
def return_personal_tool(request, tool_id):
    """Devolver herramienta personal"""
    try:
        tool = HerramientaPersonal.objects.get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('gestionDeTaller:personal_tools_list')
    
    if request.method == 'POST':
        fecha_devolucion = request.POST.get('fecha_devolucion')
        observaciones = request.POST.get('observaciones', '')
        
        if not fecha_devolucion:
            messages.error(request, 'La fecha de devolución es obligatoria')
        else:
            if tool.asignacion_actual:
                asignacion = tool.asignacion_actual
                asignacion.fecha_devolucion = fecha_devolucion
                asignacion.estado = 'DEVUELTA'
                asignacion.observaciones_devolucion = observaciones
                asignacion.save()
                
                # Actualizar estado de la herramienta
                tool.estado = 'DISPONIBLE'
                tool.save()
                
                messages.success(request, 'Herramienta devuelta exitosamente')
                return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
            else:
                messages.error(request, 'La herramienta no está asignada actualmente')
    
    context = {
        'tool': tool,
    }
    return render(request, 'gestionDeTaller/personal_tools/return.html', context)

@login_required
def audit_personal_tool(request, tool_id):
    """Realizar auditoría de herramienta personal"""
    try:
        tool = HerramientaPersonal.objects.get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('gestionDeTaller:personal_tools_list')
    
    if request.method == 'POST':
        fecha_auditoria = request.POST.get('fecha_auditoria')
        tipo_auditoria = request.POST.get('tipo_auditoria')
        observaciones = request.POST.get('observaciones', '')
        
        if not fecha_auditoria or not tipo_auditoria:
            messages.error(request, 'Fecha y tipo de auditoría son obligatorios')
        else:
            # Crear auditoría
            auditoria = AuditoriaHerramientaPersonal.objects.create(
                tecnico=tool.asignacion_actual.tecnico if tool.asignacion_actual else request.user,
                auditor=request.user,
                fecha_auditoria=fecha_auditoria,
                tipo_auditoria=tipo_auditoria,
                estado_general='BUENO',  # Valor por defecto
                observaciones_generales=observaciones
            )
            
            # Procesar detalles de auditoría
            detalles_raw = request.POST.get('detalles', '[]')
            print(f"DEBUG: detalles_raw = '{detalles_raw}'")  # Debug line
            if detalles_raw and detalles_raw.strip():
                try:
                    detalles_data = json.loads(detalles_raw)
                    # Crear un detalle de auditoría para la herramienta
                    # Basado en los resultados del checklist
                    cumple_todos = all(detalle.get('cumple', False) for detalle in detalles_data)
                    estado_herramienta = 'PRESENTE' if cumple_todos else 'DAÑADA'
                    
                    DetalleAuditoriaHerramienta.objects.create(
                        auditoria=auditoria,
                        herramienta=tool,
                        estado_herramienta=estado_herramienta,
                        observaciones=f"Auditoría {tipo_auditoria}. Resultados del checklist: {len([d for d in detalles_data if d.get('cumple')])}/{len(detalles_data)} campos cumplen.",
                        accion_requerida='NINGUNA' if cumple_todos else 'MANTENIMIENTO'
                    )
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error for detalles: {e}")  # Debug line
                    # Si hay error en el JSON, crear un detalle básico
                    DetalleAuditoriaHerramienta.objects.create(
                        auditoria=auditoria,
                        herramienta=tool,
                        estado_herramienta='PRESENTE',
                        observaciones=f"Auditoría {tipo_auditoria} realizada sin detalles específicos.",
                        accion_requerida='NINGUNA'
                    )
            else:
                # Si no hay detalles, crear un detalle básico
                DetalleAuditoriaHerramienta.objects.create(
                    auditoria=auditoria,
                    herramienta=tool,
                    estado_herramienta='PRESENTE',
                    observaciones=f"Auditoría {tipo_auditoria} realizada.",
                    accion_requerida='NINGUNA'
                )
            
            # Procesar auditoría de items
            items_raw = request.POST.get('items_data', '[]')
            print(f"DEBUG: items_raw = '{items_raw}'")  # Debug line
            if items_raw and items_raw.strip():
                try:
                    items_data = json.loads(items_raw)
                    for item_data in items_data:
                        try:
                            item = ItemHerramientaPersonal.objects.get(
                                id=item_data['item_id'],
                                herramienta=tool
                            )
                            estado_anterior = item.estado
                            item.estado = item_data['estado']
                            if item_data.get('observaciones'):
                                item.observaciones = item_data['observaciones']
                            item.save()
                            
                            # Registrar cambio de estado si hubo cambio
                            if estado_anterior != item.estado:
                                LogCambioItemHerramienta.objects.create(
                                    item=item,
                                    auditoria=auditoria,
                                    estado_anterior=estado_anterior,
                                    estado_nuevo=item.estado,
                                    observaciones=item_data.get('observaciones', '')
                                )
                        except ItemHerramientaPersonal.DoesNotExist:
                            continue
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error for items: {e}")  # Debug line
                    # Si hay error en el JSON, continuar sin procesar items
                    pass
            
            # Actualizar estado de la herramienta si es necesario
            if tipo_auditoria == 'MANTENIMIENTO' and any(not d.cumple for d in auditoria.detalles.all()):
                tool.estado = 'MANTENIMIENTO'
                tool.save()
            
            messages.success(request, 'Auditoría realizada exitosamente')
            return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
    
    # Obtener campos de auditoría según el tipo de herramienta
    campos_auditoria = []
    if tool.categoria == 'HERRAMIENTA_ADICIONAL':
        campos_auditoria = [
            {'nombre': 'Estado físico', 'tipo': 'text'},
            {'nombre': 'Funcionamiento', 'tipo': 'boolean'},
            {'nombre': 'Limpieza', 'tipo': 'boolean'},
            {'nombre': 'Completitud', 'tipo': 'boolean'},
        ]
    elif tool.categoria == 'EPP':
        campos_auditoria = [
            {'nombre': 'Estado físico', 'tipo': 'text'},
            {'nombre': 'Fecha de vencimiento', 'tipo': 'date'},
            {'nombre': 'Limpieza', 'tipo': 'boolean'},
            {'nombre': 'Ajuste correcto', 'tipo': 'boolean'},
        ]
    
    context = {
        'tool': tool,
        'campos_auditoria': campos_auditoria,
        'tipos_auditoria': AuditoriaHerramientaPersonal.TIPO_AUDITORIA_CHOICES,
    }
    return render(request, 'gestionDeTaller/personal_tools/audit.html', context)

@login_required
def personal_tools_dashboard(request):
    """Dashboard de herramientas personales"""
    # Estadísticas generales
    total_herramientas = HerramientaPersonal.objects.count()
    herramientas_asignadas = HerramientaPersonal.objects.filter(estado='ASIGNADA').count()
    herramientas_mantenimiento = HerramientaPersonal.objects.filter(estado='MANTENIMIENTO').count()
    herramientas_disponibles = HerramientaPersonal.objects.filter(estado='DISPONIBLE').count()
    
    # Auditorías pendientes (últimos 6 meses)
    seis_meses_atras = timezone.now().date() - timedelta(days=180)
    auditorias_pendientes = HerramientaPersonal.objects.filter(
        Q(detalleauditoriaherramienta__isnull=True) | 
        Q(detalleauditoriaherramienta__auditoria__fecha_auditoria__lt=seis_meses_atras)
    ).distinct().count()
    
    # Herramientas por categoría
    herramientas_por_categoria = HerramientaPersonal.objects.values(
        'categoria'
    ).annotate(
        total=Count('id'),
        asignadas=Count('id', filter=Q(estado='ASIGNADA')),
        mantenimiento=Count('id', filter=Q(estado='MANTENIMIENTO'))
    )
    
    # Últimas auditorías
    ultimas_auditorias = AuditoriaHerramientaPersonal.objects.select_related(
        'herramienta', 'auditor'
    ).order_by('-fecha_auditoria')[:10]
    
    # Asignaciones recientes
    asignaciones_recientes = AsignacionHerramientaPersonal.objects.select_related(
        'herramienta', 'tecnico'
    ).order_by('-fecha_asignacion')[:10]
    
    context = {
        'total_herramientas': total_herramientas,
        'herramientas_asignadas': herramientas_asignadas,
        'herramientas_mantenimiento': herramientas_mantenimiento,
        'herramientas_disponibles': herramientas_disponibles,
        'auditorias_pendientes': auditorias_pendientes,
        'herramientas_por_categoria': herramientas_por_categoria,
        'ultimas_auditorias': ultimas_auditorias,
        'asignaciones_recientes': asignaciones_recientes,
    }
    return render(request, 'gestionDeTaller/personal_tools/dashboard.html', context)

@login_required
def personal_tools_reports(request):
    """Reportes de herramientas personales"""
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    categoria_id = request.GET.get('categoria')
    tecnico_id = request.GET.get('tecnico')
    
    # Asignaciones
    asignaciones = AsignacionHerramientaPersonal.objects.select_related(
        'herramienta', 'tecnico'
    ).all()
    
    # Auditorías
    auditorias = AuditoriaHerramientaPersonal.objects.select_related(
        'tecnico', 'auditor'
    ).all()
    
    if fecha_inicio:
        asignaciones = asignaciones.filter(fecha_asignacion__gte=fecha_inicio)
        auditorias = auditorias.filter(fecha_auditoria__gte=fecha_inicio)
    
    if fecha_fin:
        asignaciones = asignaciones.filter(fecha_asignacion__lte=fecha_fin)
        auditorias = auditorias.filter(fecha_auditoria__lte=fecha_fin)
    
    if categoria_id:
        asignaciones = asignaciones.filter(herramienta__categoria=categoria_id)
        auditorias = auditorias.filter(herramienta__categoria=categoria_id)
    
    if tecnico_id:
        asignaciones = asignaciones.filter(tecnico_id=tecnico_id)
        auditorias = auditorias.filter(herramienta__asignacion_actual__tecnico_id=tecnico_id)
    
    # Estadísticas
    total_asignaciones = asignaciones.count()
    total_auditorias = auditorias.count()
    
    # Auditorías por resultado
    auditorias_exitosas = auditorias.filter(
        detalles_auditoria__estado_herramienta='PRESENTE'
    ).distinct().count()
    auditorias_con_incidencias = auditorias.filter(
        detalles_auditoria__estado_herramienta__in=['AUSENTE', 'DAÑADA', 'DESGASTADA', 'VENCIDA']
    ).distinct().count()
    
    categorias = HerramientaPersonal.CATEGORIA_CHOICES
    tecnicos = Usuario.objects.filter(rol='TECNICO').order_by('first_name', 'last_name')
    
    context = {
        'asignaciones': asignaciones.order_by('-fecha_asignacion'),
        'auditorias': auditorias.order_by('-fecha_auditoria'),
        'total_asignaciones': total_asignaciones,
        'total_auditorias': total_auditorias,
        'auditorias_exitosas': auditorias_exitosas,
        'auditorias_con_incidencias': auditorias_con_incidencias,
        'categorias': categorias,
        'tecnicos': tecnicos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'categoria_id': categoria_id,
        'tecnico_id': tecnico_id,
    }
    return render(request, 'gestionDeTaller/personal_tools/reports.html', context)

@login_required
def descargar_template_excel(request):
    """Vista para descargar un template de Excel para importación"""
    try:
        # Crear un DataFrame de ejemplo
        datos_ejemplo = [
            {
                'CODIGO ( Ver Notas p/descripcion)': 'JT01674A',
                'ITEMS': 'Herramienta especial para motor',
                'CANTIDAD': 1,
                'UBICACION': 'JD 01',
                'IMAGEN': 'JT01674A.jpg'
            },
            {
                'CODIGO ( Ver Notas p/descripcion)': 'JDG11263',
                'ITEMS': 'Kit de diagnóstico',
                'CANTIDAD': 2,
                'UBICACION': 'JD 02',
                'IMAGEN': 'JDG11263.JPG'
            }
        ]
        
        df = pd.DataFrame(datos_ejemplo)
        
        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Herramientas', index=False)
            
            # Obtener el workbook y worksheet para formatear
            workbook = writer.book
            worksheet = writer.sheets['Herramientas']
            
            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Aplicar formato a los encabezados
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustar ancho de columnas
            worksheet.set_column('A:A', 25)  # Código
            worksheet.set_column('B:B', 40)  # Items
            worksheet.set_column('C:C', 10)  # Cantidad
            worksheet.set_column('D:D', 15)  # Ubicación
            worksheet.set_column('E:E', 20)  # Imagen
        
        output.seek(0)
        
        # Crear la respuesta HTTP
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_herramientas_especiales.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error al generar el template: {str(e)}')
        return redirect('gestionDeTaller:importar_herramientas_especiales')

@login_required
def update_certification(request, tool_id):
    """Actualizar información de certificación de herramienta personal"""
    try:
        tool = HerramientaPersonal.objects.get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('gestionDeTaller:personal_tools_list')
    
    if request.method == 'POST':
        fecha_certificacion = request.POST.get('fecha_certificacion')
        fecha_vencimiento = request.POST.get('fecha_vencimiento_certificacion')
        
        # Convertir fechas vacías a None
        if fecha_certificacion == '':
            fecha_certificacion = None
        if fecha_vencimiento == '':
            fecha_vencimiento = None
        
        # Validar que si hay fecha de vencimiento, debe haber fecha de certificación
        if fecha_vencimiento and not fecha_certificacion:
            messages.error(request, 'Si se especifica una fecha de vencimiento, debe especificar también la fecha de certificación')
            return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
        
        # Validar que la fecha de vencimiento no sea anterior a la fecha de certificación
        if fecha_certificacion and fecha_vencimiento:
            from datetime import datetime
            fecha_cert = datetime.strptime(fecha_certificacion, '%Y-%m-%d').date()
            fecha_venc = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
            if fecha_venc < fecha_cert:
                messages.error(request, 'La fecha de vencimiento no puede ser anterior a la fecha de certificación')
                return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
        
        # Actualizar la herramienta
        tool.fecha_certificacion = fecha_certificacion
        tool.fecha_vencimiento_certificacion = fecha_vencimiento
        tool.save()
        
        messages.success(request, 'Información de certificación actualizada exitosamente')
        return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
    
    # Si no es POST, redirigir al detalle
    return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)


@login_required
def add_item(request, tool_id):
    """Agregar item a herramienta personal"""
    try:
        tool = HerramientaPersonal.objects.get(id=tool_id)
    except HerramientaPersonal.DoesNotExist:
        messages.error(request, 'Herramienta no encontrada')
        return redirect('personal_tools_list')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        cantidad = request.POST.get('cantidad', 1)
        estado = request.POST.get('estado', 'PRESENTE')
        observaciones = request.POST.get('observaciones', '')
        
        if not nombre:
            messages.error(request, 'El nombre del item es obligatorio')
        else:
            try:
                # Verificar si ya existe un item con el mismo nombre
                if tool.items.filter(nombre=nombre).exists():
                    messages.error(request, f'Ya existe un item llamado "{nombre}" en esta herramienta')
                else:
                    # Crear el nuevo item
                    ItemHerramientaPersonal.objects.create(
                        herramienta=tool,
                        nombre=nombre,
                        descripcion=descripcion,
                        cantidad=cantidad,
                        estado=estado,
                        observaciones=observaciones
                    )
                    
                    messages.success(request, f'Item "{nombre}" agregado exitosamente')
                    return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)
                    
            except Exception as e:
                messages.error(request, f'Error al crear el item: {str(e)}')
    
    # Si no es POST, redirigir al detalle
    return redirect('gestionDeTaller:personal_tool_detail', tool_id=tool.id)

@login_required
def importar_repuestos_jd(request):
    """Vista para importar repuestos desde archivo de John Deere"""
    
    # Solo gerentes y administrativos pueden importar repuestos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para importar repuestos.')
        return redirect('gestionDeTaller:gestionar_repuestos')
    
    if request.method == 'POST':
        try:
            # Verificar si se subió un archivo
            if 'archivo_repuestos' not in request.FILES:
                messages.error(request, 'Debe seleccionar un archivo para importar.')
                return redirect('gestionDeTaller:importar_repuestos_jd')
            
            archivo = request.FILES['archivo_repuestos']
            
            # Verificar el tipo de archivo
            if not archivo.name.endswith('.txt') and not archivo.name.startswith('AR.DMS.DWNLD.V2'):
                messages.error(request, 'El archivo debe ser un archivo de texto de John Deere.')
                return redirect('gestionDeTaller:importar_repuestos_jd')
            
            # Opciones de importación
            modo_importacion = request.POST.get('modo_importacion', 'crear_nuevos')
            categoria_default = request.POST.get('categoria_default', '')
            proveedor_default = request.POST.get('proveedor_default', 'John Deere')
            
            # Procesar el archivo
            resultado = procesar_archivo_repuestos_jd(
                archivo, 
                modo_importacion, 
                categoria_default, 
                proveedor_default,
                request.user
            )
            
            if resultado['success']:
                messages.success(
                    request, 
                    f"Importación completada: {resultado['creados']} nuevos, "
                    f"{resultado['actualizados']} actualizados, {resultado['errores']} errores."
                )
            else:
                messages.error(request, f"Error en la importación: {resultado['error']}")
                
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
    
    return render(request, 'gestionDeTaller/importar_repuestos_jd.html')

def procesar_archivo_repuestos_jd(archivo, modo_importacion, categoria_default, proveedor_default, usuario):
    """Procesa el archivo de repuestos de John Deere"""
    
    from .parser_repuestos_jd_v2 import ParserRepuestosJDV2
    from django.db import transaction
    
    try:
        # Guardar el archivo temporalmente
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            for chunk in archivo.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        # Parsear el archivo
        parser = ParserRepuestosJDV2()
        repuestos_parseados, errores_parseo = parser.parse_archivo(temp_file_path)
        
        # Limpiar archivo temporal
        os.unlink(temp_file_path)
        
        if not repuestos_parseados:
            return {
                'success': False,
                'error': 'No se pudieron parsear repuestos del archivo'
            }
        
        # Procesar repuestos en la base de datos
        creados = 0
        actualizados = 0
        errores = 0
        
        with transaction.atomic():
            for repuesto_data in repuestos_parseados:
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
        
        return {
            'success': True,
            'creados': creados,
            'actualizados': actualizados,
            'errores': errores,
            'total_parseados': len(repuestos_parseados)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }