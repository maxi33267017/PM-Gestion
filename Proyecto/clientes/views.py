from django.shortcuts import render, redirect, get_object_or_404
from clientes.models import Cliente, ContactoCliente, TipoEquipo, ModeloEquipo, ModeloMotor, Equipo, RegistroHorometro, Ciudad, Provincia, Sucursal
from clientes.forms import ClienteForm, ContactoClienteForm, TipoEquipoForm, EquipoForm
from django.urls import reverse
from django.db.models import Subquery, OuterRef
from django.contrib.auth.decorators import login_required

@login_required
def clientes(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('clientes')  # Redirige de nuevo a la vista `clientes` después de guardar
    else:
        form = ClienteForm()
    

    # Filtrar los clientes según la sucursal del usuario logueado
    usuario = request.user
    if usuario.rol in ['ADMINISTRATIVO', 'TECNICO'] and usuario.sucursal:
        lista_clientes = Cliente.objects.filter(sucursal=usuario.sucursal, activo=True)
    elif usuario.rol == 'GERENTE':
        # Los gerentes ven todos los clientes (incluyendo inactivos)
        lista_clientes = Cliente.objects.all()
    else:
        lista_clientes = Cliente.objects.all()

    sucursales = Sucursal.objects.all()
    provincias = Provincia.objects.all()
    ciudades = Ciudad.objects.all()

    context = {
        'clientes': lista_clientes,
        'form': form,
        'sucursales': sucursales,
        'provincias': provincias,
        'ciudades': ciudades,
    }

    return render(request, 'clientes/clientes.html', context)

@login_required
def parque(request):

    usuario = request.user
    if usuario.rol in ['ADMINISTRATIVO', 'TECNICO'] and usuario.sucursal:
        equipos =Equipo.objects.select_related('cliente').filter(cliente__sucursal=usuario.sucursal)
    else:
        equipos = Equipo.objects.select_related('cliente').all()

    return render(request, 'clientes/parque_equipos/parque.html', {'equipos': equipos})

@login_required
def guardar_cliente(request):
        if request.method == 'POST':
            form = ClienteForm(request.POST)
            if form.is_valid():
                cliente = form.save()  # Guardar el cliente y obtener el objeto cliente
                cliente_id = cliente.id  # Obtener el ID del cliente
                return redirect(reverse('detalle_cliente', args=[cliente_id]))
        # Manejar errores o mostrar un mensaje de éxito si es necesario
        return render(request, 'clientes/error.html')

@login_required
def detalle_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    contactos = ContactoCliente.objects.filter(cliente=cliente)

    equipos = Equipo.objects.filter(cliente=cliente).annotate(
        ultimo_horometro=Subquery(
            RegistroHorometro.objects.filter(
                equipo=OuterRef('pk')
            ).order_by('-fecha_registro').values('horas')[:1]
        )
    )

    # Inicializar ambos formularios
    contacto_form = ContactoClienteForm()
    equipo_form = EquipoForm()

    # Procesar el formulario si es una petición POST
    if request.method == 'POST':
        print("POST data:", request.POST)  # Imprimir datos POST
        
        # Procesar formulario de contacto
        if 'guardar_contacto' in request.POST:
            print("Procesando formulario de contacto")  # Debug
            contacto_form = ContactoClienteForm(request.POST)
            
            if contacto_form.is_valid():
                print("Formulario válido, guardando contacto")  # Debug
                nuevo_contacto = contacto_form.save(commit=False)
                nuevo_contacto.cliente = cliente
                nuevo_contacto.save()
                return redirect('detalle_cliente', cliente_id=cliente_id)
            else:
                print("Errores del formulario:", contacto_form.errors)  # Debug
        
        # Procesar formulario de equipo
        elif 'guardar_equipo' in request.POST:
            print("Procesando formulario de equipo")  # Debug
            equipo_form = EquipoForm(request.POST)
            
            if equipo_form.is_valid():
                nuevo_equipo = equipo_form.save(commit=False)
                nuevo_equipo.cliente = cliente
                nuevo_equipo.save()
                return redirect('detalle_cliente', cliente_id=cliente_id)
            else:
                print("Errores del formulario de equipo:", equipo_form.errors)  # Debug

    context = {
        'cliente': cliente,
        'contactos': contactos,
        'equipos': equipos,
        'contacto_form': contacto_form,
        'equipo_form': equipo_form,
    }

    return render(request, 'clientes/detalle_cliente.html', context)

from django.db.models import Subquery, OuterRef
from django.shortcuts import get_object_or_404, render
from .models import Cliente, Equipo, RegistroHorometro
from gestionDeTaller.models import Servicio

@login_required
def detalle_equipo(request, cliente_id, equipo_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    
    # Obtener el último horómetro
    horas = Equipo.objects.filter(cliente=cliente).annotate(
        ultimo_horometro=Subquery(
            RegistroHorometro.objects.filter(
                equipo=OuterRef('pk')
            ).order_by('-fecha_registro').values('horas')[:1]
        )
    )

    # Obtener los servicios asociados al equipo
    servicios = Servicio.objects.filter(preorden__equipo=equipo).order_by('-fecha_servicio')

    context = {
        'equipo': equipo,
        'cliente': cliente,
        'horas': horas,
        'servicios': servicios,  # Pasar los servicios al contexto
    }

    return render(request, 'clientes/detalle_equipo.html', context)