from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import EquipoStock, Certificado, MovimientoStockCertificado, VentaEquipo, TransferenciaEquipo
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario


def es_gerente(user):
    """Verifica si el usuario es gerente"""
    return user.is_authenticated and user.rol == 'GERENTE'


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def dashboard_ventas(request):
    """Dashboard principal de ventas de maquinarias"""
    
    # Estadísticas generales
    total_equipos_stock = EquipoStock.objects.filter(estado='EN_STOCK').count()
    total_equipos_vendidos = EquipoStock.objects.filter(estado='VENDIDO').count()
    total_ventas_mes = VentaEquipo.objects.filter(
        fecha_venta__month=timezone.now().month,
        fecha_venta__year=timezone.now().year
    ).count()
    
    # Certificados que necesitan reposición
    certificados_bajo_stock = Certificado.objects.filter(
        stock_disponible__lte=F('stock_minimo'),
        activo=True
    )
    
    # Últimas ventas
    ultimas_ventas = VentaEquipo.objects.select_related(
        'equipo_stock', 'cliente', 'vendedor'
    ).order_by('-fecha_creacion')[:10]
    
    # Equipos en stock por sucursal
    equipos_por_sucursal = EquipoStock.objects.filter(
        estado='EN_STOCK'
    ).values('sucursal__nombre').annotate(
        total=Count('id', distinct=True)
    ).order_by('-total')
    
    context = {
        'total_equipos_stock': total_equipos_stock,
        'total_equipos_vendidos': total_equipos_vendidos,
        'total_ventas_mes': total_ventas_mes,
        'certificados_bajo_stock': certificados_bajo_stock,
        'ultimas_ventas': ultimas_ventas,
        'equipos_por_sucursal': equipos_por_sucursal,
    }
    
    return render(request, 'ventaMaquinarias/dashboard.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def lista_equipos_stock(request):
    """Lista de equipos en stock"""
    
    # Filtros
    estado = request.GET.get('estado', '')
    sucursal = request.GET.get('sucursal', '')
    tipo_equipo = request.GET.get('tipo_equipo', '')
    search = request.GET.get('search', '')
    
    equipos = EquipoStock.objects.select_related(
        'modelo', 'tipo_equipo', 'sucursal'
    ).all()
    
    # Aplicar filtros
    if estado:
        equipos = equipos.filter(estado=estado)
    if sucursal:
        equipos = equipos.filter(sucursal_id=sucursal)
    if tipo_equipo:
        equipos = equipos.filter(tipo_equipo_id=tipo_equipo)
    if search:
        equipos = equipos.filter(
            Q(numero_serie__icontains=search) |
            Q(modelo__nombre__icontains=search) |
            Q(modelo__marca__icontains=search) |
            Q(numero_orden_compra__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(equipos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener datos para filtros
    from recursosHumanos.models import Sucursal
    from clientes.models import TipoEquipo
    
    context = {
        'page_obj': page_obj,
        'estados': EquipoStock.ESTADO_CHOICES,
        'sucursales': Sucursal.objects.all(),
        'tipos_equipo': TipoEquipo.objects.all(),
        'filtros': {
            'estado': estado,
            'sucursal': sucursal,
            'tipo_equipo': tipo_equipo,
            'search': search,
        }
    }
    
    return render(request, 'ventaMaquinarias/lista_equipos_stock.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def detalle_equipo_stock(request, equipo_id):
    """Detalle de un equipo en stock"""
    
    equipo = get_object_or_404(EquipoStock, id=equipo_id)
    
    # Verificar si ya tiene una venta asociada
    venta_existente = None
    try:
        venta_existente = equipo.ventaequipo
    except VentaEquipo.DoesNotExist:
        pass
    
    context = {
        'equipo': equipo,
        'venta_existente': venta_existente,
    }
    
    return render(request, 'ventaMaquinarias/detalle_equipo_stock.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def crear_venta(request, equipo_id):
    """Crear una nueva venta para un equipo"""
    
    equipo = get_object_or_404(EquipoStock, id=equipo_id, estado='EN_STOCK')
    
    if request.method == 'POST':
        # Procesar formulario de venta
        cliente_id = request.POST.get('cliente')
        fecha_venta = request.POST.get('fecha_venta')
        precio_venta = request.POST.get('precio_venta')
        numero_factura = request.POST.get('numero_factura', '')
        
        # Certificados (solo si están marcados los checkboxes)
        certificado_garantia_id = None
        certificado_garantia_extendida_id = None
        certificado_svap_id = None
        
        if request.POST.get('check_garantia'):
            certificado_garantia_id = request.POST.get('certificado_garantia')
        if request.POST.get('check_garantia_extendida'):
            certificado_garantia_extendida_id = request.POST.get('certificado_garantia_extendida')
        if request.POST.get('check_svap'):
            certificado_svap_id = request.POST.get('certificado_svap')
        
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Crear la venta
            venta = VentaEquipo.objects.create(
                equipo_stock=equipo,
                cliente_id=cliente_id,
                fecha_venta=fecha_venta,
                precio_venta=precio_venta,
                numero_factura=numero_factura,
                certificado_garantia_id=certificado_garantia_id or None,
                certificado_garantia_extendida_id=certificado_garantia_extendida_id or None,
                certificado_svap_id=certificado_svap_id or None,
                vendedor=request.user,
                observaciones=observaciones
            )
            
            # Cambiar estado del equipo a VENDIDO
            equipo.estado = 'VENDIDO'
            equipo.save()
            
            # Reducir stock de certificados y verificar stock mínimo
            certificados_usados = []
            certificados_bajo_stock = []
            
            if certificado_garantia_id:
                certificados_usados.append(int(certificado_garantia_id))
            if certificado_garantia_extendida_id:
                certificados_usados.append(int(certificado_garantia_extendida_id))
            if certificado_svap_id:
                certificados_usados.append(int(certificado_svap_id))
            
            for cert_id in certificados_usados:
                certificado = Certificado.objects.get(id=cert_id)
                stock_anterior = certificado.stock_disponible
                certificado.stock_disponible -= 1
                certificado.save()
                
                # Verificar si llegó al stock mínimo
                if certificado.necesita_reposicion:
                    certificados_bajo_stock.append(certificado)
                
                # Registrar movimiento
                MovimientoStockCertificado.objects.create(
                    certificado=certificado,
                    tipo_movimiento='SALIDA',
                    cantidad=1,
                    stock_anterior=stock_anterior,
                    stock_nuevo=certificado.stock_disponible,
                    venta=venta,
                    usuario=request.user,
                    motivo=f'Venta de equipo {equipo.numero_serie}'
                )
            
            # Enviar email de alerta si hay certificados bajo stock
            if certificados_bajo_stock:
                enviar_alerta_stock_minimo(certificados_bajo_stock, venta)
            
            messages.success(request, f'Venta creada exitosamente para el equipo {equipo.numero_serie}')
            return redirect('ventaMaquinarias:detalle_venta', venta_id=venta.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear la venta: {str(e)}')
    
    # Obtener datos para el formulario
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    certificados_garantia = Certificado.objects.filter(
        tipo='GARANTIA', activo=True, stock_disponible__gt=0
    )
    certificados_garantia_extendida = Certificado.objects.filter(
        tipo='GARANTIA_EXTENDIDA', activo=True, stock_disponible__gt=0
    )
    certificados_svap = Certificado.objects.filter(
        tipo='SVAP', activo=True, stock_disponible__gt=0
    )
    
    context = {
        'equipo': equipo,
        'clientes': clientes,
        'certificados_garantia': certificados_garantia,
        'certificados_garantia_extendida': certificados_garantia_extendida,
        'certificados_svap': certificados_svap,
    }
    
    return render(request, 'ventaMaquinarias/crear_venta.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def detalle_venta(request, venta_id):
    """Detalle de una venta"""
    
    venta = get_object_or_404(VentaEquipo, id=venta_id)
    
    # Verificar si ya tiene transferencia
    transferencia_existente = None
    try:
        transferencia_existente = venta.transferenciaequipo
    except TransferenciaEquipo.DoesNotExist:
        pass
    
    context = {
        'venta': venta,
        'transferencia_existente': transferencia_existente,
    }
    
    return render(request, 'ventaMaquinarias/detalle_venta.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def lista_ventas(request):
    """Lista de ventas realizadas"""
    
    # Filtros
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    search = request.GET.get('search', '')
    
    ventas = VentaEquipo.objects.select_related(
        'equipo_stock', 'cliente', 'vendedor'
    ).all()
    
    # Aplicar filtros
    if estado:
        ventas = ventas.filter(estado=estado)
    if fecha_desde:
        ventas = ventas.filter(fecha_venta__gte=fecha_desde)
    if fecha_hasta:
        ventas = ventas.filter(fecha_venta__lte=fecha_hasta)
    if search:
        ventas = ventas.filter(
            Q(cliente__razon_social__icontains=search) |
            Q(cliente__cuit__icontains=search) |
            Q(equipo_stock__numero_serie__icontains=search) |
            Q(numero_factura__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(ventas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estados': VentaEquipo.ESTADO_CHOICES,
        'filtros': {
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'search': search,
        }
    }
    
    return render(request, 'ventaMaquinarias/lista_ventas.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def gestion_certificados(request):
    """Gestión de certificados y stock"""
    
    # Filtros
    tipo = request.GET.get('tipo', '')
    activo = request.GET.get('activo', '')
    
    certificados = Certificado.objects.all()
    
    # Aplicar filtros
    if tipo:
        certificados = certificados.filter(tipo=tipo)
    if activo != '':
        certificados = certificados.filter(activo=activo == 'true')
    
    # Estadísticas
    total_certificados = certificados.count()
    certificados_bajo_stock = certificados.filter(
        stock_disponible__lte=F('stock_minimo')
    ).count()
    
    context = {
        'certificados': certificados,
        'total_certificados': total_certificados,
        'certificados_bajo_stock': certificados_bajo_stock,
        'tipos': Certificado.TIPO_CERTIFICADO,
        'filtros': {
            'tipo': tipo,
            'activo': activo,
        }
    }
    
    return render(request, 'ventaMaquinarias/gestion_certificados.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def agregar_stock_certificado(request, certificado_id):
    """Agregar stock a un certificado"""
    
    certificado = get_object_or_404(Certificado, id=certificado_id)
    
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', '')
        
        if cantidad > 0:
            stock_anterior = certificado.stock_disponible
            certificado.stock_disponible += cantidad
            certificado.save()
            
            # Registrar movimiento
            MovimientoStockCertificado.objects.create(
                certificado=certificado,
                tipo_movimiento='ENTRADA',
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=certificado.stock_disponible,
                usuario=request.user,
                motivo=motivo or f'Agregado de stock manual'
            )
            
            messages.success(request, f'Se agregaron {cantidad} unidades al stock de {certificado.nombre}')
            return redirect('gestion_certificados')
        else:
            messages.error(request, 'La cantidad debe ser mayor a 0')
    
    context = {
        'certificado': certificado,
    }
    
    return render(request, 'ventaMaquinarias/agregar_stock_certificado.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def transferir_equipo(request, venta_id):
    """Transferir equipo vendido al cliente"""
    
    venta = get_object_or_404(VentaEquipo, id=venta_id, estado='PENDIENTE')
    
    if request.method == 'POST':
        # Verificar checklist
        checklist_completado = request.POST.get('checklist_completado') == 'on'
        observaciones = request.POST.get('observaciones', '')
        
        if checklist_completado:
            # Crear transferencia
            transferencia = TransferenciaEquipo.objects.create(
                venta=venta,
                equipo_cliente=Equipo.objects.get(numero_serie=venta.equipo_stock.numero_serie),
                usuario_transferencia=request.user,
                checklist_completado=True,
                fecha_checklist=timezone.now(),
                observaciones=observaciones
            )
            
            # Actualizar estado de la venta
            venta.estado = 'COMPLETADA'
            venta.save()
            
            messages.success(request, f'Equipo transferido exitosamente a {venta.cliente.razon_social}')
            return redirect('detalle_venta', venta_id=venta.id)
        else:
            messages.error(request, 'Debe completar el checklist antes de transferir el equipo')
    
    context = {
        'venta': venta,
    }
    
    return render(request, 'ventaMaquinarias/transferir_equipo.html', context)


# API endpoints para AJAX
@login_required
@user_passes_test(es_gerente, login_url='/login/')
def api_equipos_stock(request):
    """API para obtener equipos en stock (AJAX)"""
    
    equipos = EquipoStock.objects.filter(estado='EN_STOCK').select_related(
        'modelo', 'tipo_equipo', 'sucursal'
    )[:50]  # Limitar resultados
    
    data = []
    for equipo in equipos:
        data.append({
            'id': equipo.id,
            'numero_serie': equipo.numero_serie,
            'modelo': f"{equipo.modelo.marca} {equipo.modelo.nombre}",
            'tipo_equipo': equipo.tipo_equipo.nombre,
            'sucursal': equipo.sucursal.nombre,
            'costo_compra': float(equipo.costo_compra),
            'dias_en_stock': equipo.dias_en_stock,
        })
    
    return JsonResponse({'equipos': data})


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def api_certificados_disponibles(request):
    """API para obtener certificados disponibles (AJAX)"""
    
    tipo = request.GET.get('tipo', '')
    
    certificados = Certificado.objects.filter(
        activo=True, 
        stock_disponible__gt=0
    )
    
    if tipo:
        certificados = certificados.filter(tipo=tipo)
    
    data = []
    for cert in certificados:
        data.append({
            'id': cert.id,
            'nombre': cert.nombre,
            'tipo': cert.get_tipo_display(),
            'stock_disponible': cert.stock_disponible,
            'precio_venta': float(cert.precio_venta),
        })
    
    return JsonResponse({'certificados': data})


def enviar_alerta_stock_minimo(certificados_bajo_stock, venta):
    """Envía email de alerta cuando se llega al stock mínimo de certificados"""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    # Lista de destinatarios
    destinatarios = [
        'santiago.fiocchi@patagoniamaquinarias.com',
        'carolina.fiocchi@patagoniamaquinarias.com',
        'hector.gonzalez@patagoniamaquinarias.com',
        'candela.lopez@patagoniamaquinarias.com',
        'maxi.caamano@patagoniamaquinarias.com'
    ]
    
    # Crear tabla de certificados bajo stock
    tabla_certificados = []
    for cert in certificados_bajo_stock:
        tabla_certificados.append({
            'nombre': cert.nombre,
            'tipo': cert.get_tipo_display(),
            'stock_actual': cert.stock_disponible,
            'stock_minimo': cert.stock_minimo,
            'necesita_reposicion': cert.necesita_reposicion
        })
    
    # Contexto para el template
    context = {
        'venta': venta,
        'equipo': venta.equipo_stock,
        'cliente': venta.cliente,
        'certificados_bajo_stock': tabla_certificados,
        'fecha_alerta': timezone.now().strftime('%d/%m/%Y %H:%M'),
    }
    
    # Renderizar template HTML
    mensaje_html = render_to_string('ventaMaquinarias/email_alerta_stock_minimo.html', context)
    mensaje_texto = strip_tags(mensaje_html)
    
    # Configurar email
    asunto = f"⚠️ ALERTA: Stock Mínimo de Certificados - Venta #{venta.id}"
    
    email = EmailMultiAlternatives(
        asunto,
        mensaje_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios
    )
    email.attach_alternative(mensaje_html, "text/html")
    
    try:
        email.send()
        print(f"Alerta de stock mínimo enviada para la venta #{venta.id}")
    except Exception as e:
        print(f"Error al enviar alerta de stock mínimo: {str(e)}")


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def crear_equipo_stock(request):
    """Crear un nuevo equipo en stock desde el frontend"""
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            numero_serie = request.POST.get('numero_serie')
            modelo_id = request.POST.get('modelo')
            tipo_equipo_id = request.POST.get('tipo_equipo')
            fecha_compra_jd = request.POST.get('fecha_compra_jd')
            numero_orden_compra = request.POST.get('numero_orden_compra')
            costo_compra = request.POST.get('costo_compra')
            sucursal_id = request.POST.get('sucursal')
            año_fabricacion = request.POST.get('año_fabricacion')
            color = request.POST.get('color', '')
            observaciones = request.POST.get('observaciones', '')
            
            # Validar que el número de serie no exista
            if EquipoStock.objects.filter(numero_serie=numero_serie).exists():
                messages.error(request, f'Ya existe un equipo con el número de serie {numero_serie}')
                return redirect('ventaMaquinarias:crear_equipo_stock')
            
            # Crear el equipo
            equipo = EquipoStock.objects.create(
                numero_serie=numero_serie,
                modelo_id=modelo_id,
                tipo_equipo_id=tipo_equipo_id,
                fecha_compra_jd=fecha_compra_jd,
                numero_orden_compra=numero_orden_compra,
                costo_compra=costo_compra,
                sucursal_id=sucursal_id,
                año_fabricacion=año_fabricacion,
                color=color,
                observaciones=observaciones
            )
            
            messages.success(request, f'Equipo {equipo.numero_serie} creado exitosamente')
            return redirect('ventaMaquinarias:detalle_equipo_stock', equipo_id=equipo.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el equipo: {str(e)}')
    
    # Obtener datos para el formulario
    from recursosHumanos.models import Sucursal
    from clientes.models import ModeloEquipo, TipoEquipo
    
    context = {
        'sucursales': Sucursal.objects.all(),
        'modelos': ModeloEquipo.objects.filter(activo=True),
        'tipos_equipo': TipoEquipo.objects.all(),
    }
    
    return render(request, 'ventaMaquinarias/crear_equipo_stock.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def crear_venta_directa(request):
    """Crear una nueva venta directamente desde el frontend"""
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            equipo_stock_id = request.POST.get('equipo_stock')
            cliente_id = request.POST.get('cliente')
            fecha_venta = request.POST.get('fecha_venta')
            precio_venta = request.POST.get('precio_venta')
            numero_factura = request.POST.get('numero_factura', '')
            observaciones = request.POST.get('observaciones', '')
            
            # Certificados seleccionados (pueden ser varios)
            certificados_ids = request.POST.getlist('certificados')
            
            # Crear la venta
            venta = VentaEquipo.objects.create(
                equipo_stock_id=equipo_stock_id,
                cliente_id=cliente_id,
                fecha_venta=fecha_venta,
                precio_venta=precio_venta,
                numero_factura=numero_factura,
                vendedor=request.user,
                observaciones=observaciones
            )
            
            # Asociar certificados
            if certificados_ids:
                certificados = Certificado.objects.filter(id__in=certificados_ids)
                venta.certificados.set(certificados)
                # Descontar stock y registrar movimientos
                certificados_bajo_stock = []
                for cert in certificados:
                    stock_anterior = cert.stock_disponible
                    cert.stock_disponible -= 1
                    cert.save()
                    if cert.necesita_reposicion:
                        certificados_bajo_stock.append(cert)
                    MovimientoStockCertificado.objects.create(
                        certificado=cert,
                        tipo_movimiento='SALIDA',
                        cantidad=1,
                        stock_anterior=stock_anterior,
                        stock_nuevo=cert.stock_disponible,
                        venta=venta,
                        usuario=request.user,
                        motivo=f'Venta de equipo {venta.equipo_stock.numero_serie}'
                    )
                # Enviar email de alerta si hay certificados bajo stock
                if certificados_bajo_stock:
                    enviar_alerta_stock_minimo(certificados_bajo_stock, venta)
            
            # Cambiar estado del equipo a VENDIDO
            equipo = venta.equipo_stock
            equipo.estado = 'VENDIDO'
            equipo.save()
            
            messages.success(request, f'Venta creada exitosamente para el equipo {equipo.numero_serie}')
            return redirect('ventaMaquinarias:detalle_venta', venta_id=venta.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear la venta: {str(e)}')
    
    # Obtener datos para el formulario
    equipos_disponibles = EquipoStock.objects.filter(estado='EN_STOCK').select_related('modelo', 'tipo_equipo')
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    # Solo certificados reales (no procesos JD)
    certificados = Certificado.objects.exclude(tipo__in=['GARANTIA', 'GARANTIA_EXTENDIDA', 'SVAP']).filter(activo=True, stock_disponible__gt=0)
    
    context = {
        'equipos_disponibles': equipos_disponibles,
        'clientes': clientes,
        'certificados': certificados,
    }
    
    return render(request, 'ventaMaquinarias/crear_venta_directa.html', context)


@login_required
@user_passes_test(es_gerente, login_url='/login/')
def actualizar_checklist_procesos(request, venta_id):
    """Actualizar el checklist de procesos de John Deere"""
    
    venta = get_object_or_404(VentaEquipo, id=venta_id)
    
    if request.method == 'POST':
        try:
            # Obtener el checklist o crearlo si no existe
            checklist, created = ChecklistProcesosJD.objects.get_or_create(
                venta=venta,
                defaults={
                    'registro_garantias': False,
                    'garantia_extendida': False,
                    'operations_center': False,
                    'svap': False,
                }
            )
            
            # Actualizar procesos
            checklist.registro_garantias = request.POST.get('registro_garantias') == 'on'
            checklist.garantia_extendida = request.POST.get('garantia_extendida') == 'on'
            checklist.operations_center = request.POST.get('operations_center') == 'on'
            checklist.svap = request.POST.get('svap') == 'on'
            checklist.observaciones = request.POST.get('observaciones', '')
            checklist.usuario_actualizacion = request.user
            checklist.save()
            
            messages.success(request, 'Checklist de procesos actualizado exitosamente')
            return redirect('ventaMaquinarias:detalle_venta', venta_id=venta.id)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el checklist: {str(e)}')
    
    context = {
        'venta': venta,
        'checklist': getattr(venta, 'checklist_procesos', None),
    }
    
    return render(request, 'ventaMaquinarias/actualizar_checklist_procesos.html', context)
