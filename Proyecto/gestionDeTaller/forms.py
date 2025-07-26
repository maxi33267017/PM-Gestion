from django import forms
from .models import PreOrden, Servicio, PedidoRepuestosTerceros, GastoAsistencia, VentaRepuesto, ChecklistSalidaCampo, Revision5S, PlanAccion5S, RespuestaEncuesta, InsatisfaccionCliente
from clientes.models import Cliente
from recursosHumanos.models import Usuario
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
import base64
from django.contrib import messages


from django import forms
from .models import PreOrden, Evidencia
from recursosHumanos.models import Sucursal
from django.forms import TextInput


class PreordenForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Usar el nuevo método del modelo Usuario para obtener sucursales disponibles
        if self.user:
            self.fields['sucursal'].queryset = self.user.get_sucursales_para_formulario()
        else:
            self.fields['sucursal'].queryset = Sucursal.objects.filter(activo=True)

        # Agregar clase select2 a los campos cliente y equipo
        self.fields['cliente'].widget.attrs.update({'class': 'form-control select2'})
        self.fields['equipo'].widget.attrs.update({'class': 'form-control select2'})
        self.fields['sucursal'].widget.attrs.update({'class': 'form-control select2'})

        # Personalizar el campo de clasificación (opcional)
        self.fields['clasificacion'].widget.attrs.update({'class': 'form-control select2'})

    class Meta:
        model = PreOrden
        fields = [
            'sucursal', 'cliente', 'equipo', 'horometro', 'solicitud_cliente',
            'detalles_adicionales', 'tipo_trabajo', 'tecnicos',
            'fecha_estimada', 'hora_inicio_estimada', 'hora_fin_estimada', 'codigos_error',
            'trae_llave', 'estado_cabina', 'estado_neumaticos_tren', 'estado_vidrios',
            'combustible_ingreso', 'observaciones_estado_equipo', 'firma_cliente', 'nombre_cliente',
            'clasificacion'  # Nuevo campo agregado
        ]
        widgets = {
            'fecha_estimada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_inicio_estimada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin_estimada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'codigos_error': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'solicitud_cliente': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'detalles_adicionales': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'trae_llave': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado_cabina': forms.TextInput(attrs={'class': 'form-control'}),
            'estado_neumaticos_tren': forms.TextInput(attrs={'class': 'form-control'}),
            'estado_vidrios': forms.TextInput(attrs={'class': 'form-control'}),
            'combustible_ingreso': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones_estado_equipo': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aclaración del cliente'}),
            'clasificacion': forms.Select(attrs={'class': 'form-control'}),  # Widget para el nuevo campo
        }

class ServicioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar el queryset de preorden usando las sucursales disponibles del usuario
        if self.user:
            sucursales_disponibles = self.user.get_sucursales_disponibles()
            self.fields['preorden'].queryset = PreOrden.objects.filter(
                sucursal__in=sucursales_disponibles,
                servicio__isnull=True
            )
        else:
            self.fields['preorden'].queryset = PreOrden.objects.filter(servicio__isnull=True)

        # Agregar clases y atributos a los campos
        for field_name, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField):
                field.widget.attrs.update({'class': 'form-control select2'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_fecha_servicio(self):
        fecha = self.cleaned_data.get('fecha_servicio')
        if isinstance(fecha, str):
            try:
                # Intentar convertir la fecha del formato DD/MM/YYYY a YYYY-MM-DD
                from datetime import datetime
                fecha = datetime.strptime(fecha, '%d/%m/%Y').date()
            except ValueError:
                raise forms.ValidationError('Por favor ingrese una fecha válida en formato DD/MM/YYYY')
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        preorden = cleaned_data.get('preorden')
        fecha_servicio = cleaned_data.get('fecha_servicio')
        horometro_servicio = cleaned_data.get('horometro_servicio')

        if preorden and fecha_servicio:
            # Verificar que la fecha del servicio no sea anterior a la fecha de la preorden
            if fecha_servicio < preorden.fecha_creacion.date():
                self.add_error('fecha_servicio', 'La fecha del servicio no puede ser anterior a la fecha de la preorden.')

            # Verificar que el horómetro del servicio no sea menor que el de la preorden
            if horometro_servicio and preorden.horometro and horometro_servicio < preorden.horometro:
                self.add_error('horometro_servicio', 'El horómetro del servicio no puede ser menor que el de la preorden.')

        return cleaned_data

    class Meta:
        model = Servicio
        fields = [
            'preorden', 'fecha_servicio', 'horometro_servicio', 'orden_servicio', 'estado', 
            'trabajo', 'observaciones', 
            'numero_cotizacion', 'archivo_cotizacion', 'prioridad'
        ]
        widgets = {
            'fecha_servicio': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'placeholder': 'YYYY-MM-DD'
                }
            ),
            'orden_servicio': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Número de hasta 8 dígitos',
                    'maxlength': '8'
                }
            ),
            'observaciones': forms.Textarea(attrs={'rows': 4}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'trabajo': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
        }

class ServicioEditarForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar si el usuario puede modificar el servicio
        if self.user and self.instance:
            from .security import puede_modificar_servicio
            if not puede_modificar_servicio(self.user, self.instance):
                raise forms.ValidationError(
                    "No puedes modificar este servicio porque está 'Finalizado a Facturar'. Solo un gerente puede hacer cambios."
                )
        
        return cleaned_data

    class Meta:
        model = Servicio
        fields = ['fecha_servicio', 'horometro_servicio', 'orden_servicio', 'prioridad']
        widgets = {
            'fecha_servicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horometro_servicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'orden_servicio': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Número de hasta 8 dígitos',
                    'maxlength': '8'
                }
            ),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
        }

class ServicioDocumentosForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar si el usuario puede modificar el informe
        if self.user and self.instance:
            from .security import puede_modificar_informe
            if not puede_modificar_informe(self.user, self.instance):
                raise forms.ValidationError(
                    "No puedes modificar este informe porque ya fue firmado por el cliente. Solo un gerente puede hacer cambios."
                )
        
        return cleaned_data
    
    class Meta:
        model = Servicio
        fields = [
            'numero_factura', 'archivo_factura',
            'numero_cotizacion', 'archivo_cotizacion',
            'archivo_informe'
        ]
        widgets = {
            'numero_factura': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cotizacion': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo_factura': forms.ClearableFileInput(attrs={'class': 'form-control', 'clear': False}),
            'archivo_cotizacion': forms.ClearableFileInput(attrs={'class': 'form-control', 'clear': False}),
            'archivo_informe': forms.ClearableFileInput(attrs={'class': 'form-control', 'clear': False}),
        }
    
    def clean_archivo_factura(self):
        archivo = self.cleaned_data.get('archivo_factura')
        if archivo and not archivo.name.endswith('.pdf'):
            raise forms.ValidationError("Solo se permiten archivos PDF.")
        return archivo

    def clean_archivo_cotizacion(self):
        archivo = self.cleaned_data.get('archivo_cotizacion')
        if archivo and not archivo.name.endswith('.pdf'):
            raise forms.ValidationError("Solo se permiten archivos PDF.")
        return archivo

    def clean_archivo_informe(self):
        archivo = self.cleaned_data.get('archivo_informe')
        if archivo and not archivo.name.endswith('.pdf'):
            raise forms.ValidationError("Solo se permiten archivos PDF.")
        return archivo

class ServicioManoObraForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['valor_mano_obra']
        widgets = {
            'valor_mano_obra': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el valor de mano de obra'}),
        }

class PedidoRepuestosTercerosForm(forms.ModelForm):
    class Meta:
        model = PedidoRepuestosTerceros
        fields = ['proveedor', 'numero_pedido', 'fecha_pedido', 'costo', 'estado', 'descripcion', 'observaciones']
        widgets = {
            'fecha_pedido': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class GastoAsistenciaForm(forms.ModelForm):
    class Meta:
        model = GastoAsistencia
        fields = ['tipo', 'descripcion', 'monto', 'fecha', 'comprobante']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'comprobante': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class VentaRepuestoForm(forms.ModelForm):
    class Meta:
        model = VentaRepuesto
        fields = ['codigo', 'descripcion', 'cantidad', 'costo_unitario', 'precio_unitario']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class EditarInformeForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = [
            'ubicacion',
            'kilometros',
            'causa',
            'accion_correctiva',
            'observaciones',
            'nombre_cliente',
        ]
        widgets = {
            'causa': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'accion_correctiva': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ubicacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'kilometros': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aclaracion'}),
        }

class EvidenciaForm(forms.Form):
    imagen = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}), required=False)


class ChecklistSalidaCampoForm(forms.ModelForm):
    class Meta:
        model = ChecklistSalidaCampo
        fields = [
            'tipo_equipo',
            'nivel_aceite_motor', 'nivel_refrigerante', 'nivel_combustible',
            'estado_neumaticos', 'luces', 'carroceria',
            'preorden', 'orden_servicio', 'herramientas_basicas',
            'herramientas_especiales', 'repuestos', 'cobertores',
            'tiempo_preparacion'
        ]
        widgets = {
            'tipo_equipo': forms.Select(attrs={'class': 'form-control'}),
            'nivel_aceite_motor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nivel_refrigerante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nivel_combustible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado_neumaticos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'luces': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'carroceria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'preorden': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orden_servicio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'herramientas_basicas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'herramientas_especiales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'repuestos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cobertores': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiempo_preparacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
        }

class FiltroExportacionServiciosForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha Inicio"
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha Fin"
    )

class Revision5SForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Usar el nuevo método del modelo Usuario para obtener sucursales disponibles
        if self.user:
            self.fields['sucursal'].queryset = self.user.get_sucursales_para_formulario()
        else:
            self.fields['sucursal'].queryset = Sucursal.objects.filter(activo=True)
    
    class Meta:
        model = Revision5S
        fields = [
            'sucursal', 'fecha_revision', 'fecha_proxima',
            'box_trabajo_limpios', 'mesas_trabajo_estaticas', 'herramientas_uso_comun_devueltas',
            'paredes_limpias_tachos_ok', 'herramientas_no_uso_limpias', 'sala_garantia_ordenada',
            'epp_correspondiente_usado', 'herramientas_calibradas_certificadas', 'area_trabajo_limpia',
            'procedimientos_seguidos', 'documentacion_actualizada', 'mantenimiento_preventivo',
            'residuos_gestionados', 'mejora_continua', 'capacitacion_actualizada'
        ]
        widgets = {
            'fecha_revision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_proxima': forms.DateInput(attrs={'type': 'date'}),
        }

class PlanAccion5SForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Asegurar que el campo responsable muestre todos los usuarios sin filtro de rol
        self.fields['responsable'].queryset = Usuario.objects.filter(is_active=True).order_by('apellido', 'nombre')
        
        # Personalizar el campo responsable para mostrar solo nombre y apellido
        self.fields['responsable'].label_from_instance = lambda obj: obj.get_nombre_completo()
        
        # Agregar clases CSS a los campos
        self.fields['item_no_conforme'].widget.attrs.update({'class': 'form-control'})
        self.fields['accion_correctiva'].widget.attrs.update({'class': 'form-control', 'rows': 4})
        self.fields['responsable'].widget.attrs.update({'class': 'form-select'})
        self.fields['fecha_limite'].widget.attrs.update({'class': 'form-control'})
        self.fields['estado'].widget.attrs.update({'class': 'form-select'})
        self.fields['evidencia_despues'].widget.attrs.update({'class': 'form-control'})
        self.fields['observaciones'].widget.attrs.update({'class': 'form-control', 'rows': 3})
    
    class Meta:
        model = PlanAccion5S
        fields = [
            'item_no_conforme', 'accion_correctiva', 'responsable',
            'fecha_limite', 'estado', 'evidencia_despues', 'observaciones'
        ]
        widgets = {
            'fecha_limite': forms.DateInput(attrs={'type': 'date'}),
        }

class RespuestaEncuestaForm(forms.ModelForm):
    class Meta:
        model = RespuestaEncuesta
        fields = [
            'cumplimiento_acuerdo', 'motivo_cumplimiento_bajo',
            'probabilidad_recomendacion', 'motivo_recomendacion_baja',
            'problemas_pendientes', 'comentarios_generales',
            'nombre_respondente', 'cargo_respondente'
        ]
        widgets = {
            'cumplimiento_acuerdo': forms.Select(
                choices=[(i, f"{i}") for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'motivo_cumplimiento_bajo': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Explique por qué la calificación fue baja...'}
            ),
            'probabilidad_recomendacion': forms.Select(
                choices=[(i, f"{i}") for i in range(1, 11)],
                attrs={'class': 'form-select'}
            ),
            'motivo_recomendacion_baja': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Explique por qué la probabilidad de recomendación fue baja...'}
            ),
            'problemas_pendientes': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Describa cualquier problema pendiente o no resuelto...'}
            ),
            'comentarios_generales': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Comentarios adicionales sobre el servicio...'}
            ),
            'nombre_respondente': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Nombre de quien responde'}
            ),
            'cargo_respondente': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Cargo de quien responde'}
            ),
        }
        labels = {
            'cumplimiento_acuerdo': 'Del momento del agendamiento hasta la entrega del Equipo, ¿Lo que fue acordado fue cumplido? (1-10)',
            'motivo_cumplimiento_bajo': 'Si la respuesta fue menor o igual a 7, ¿podría decirnos por qué?',
            'probabilidad_recomendacion': 'En una escala de 1 a 10, ¿cuán probable es que recomiende el Servicio del Concesionario a otras personas?',
            'motivo_recomendacion_baja': 'Si la respuesta fue menor o igual a 7, ¿podría decirnos por qué?',
            'problemas_pendientes': '¿Algún pendiente o problema no resuelto?',
            'comentarios_generales': 'Comentarios adicionales',
            'nombre_respondente': 'Nombre del respondente',
            'cargo_respondente': 'Cargo del respondente'
        }

class InsatisfaccionClienteForm(forms.ModelForm):
    class Meta:
        model = InsatisfaccionCliente
        fields = ['responsable', 'descripcion_problema', 'solucion', 'fecha_solucion', 'estado']
        widgets = {
            'descripcion_problema': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'solucion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'fecha_solucion': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-control'})
        }


