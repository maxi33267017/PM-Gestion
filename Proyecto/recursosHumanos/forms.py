from django import forms
from django.utils import timezone
from datetime import timedelta
from gestionDeTaller.models import Servicio
from recursosHumanos.models import RegistroHorasTecnico, ActividadTrabajo
from django.db import models
from recursosHumanos.models import PermisoAusencia
from recursosHumanos.models import Usuario

class RegistroHorasTecnicoForm(forms.ModelForm):
    numero_informe = forms.CharField(
        max_length=50, required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Número de Informe de Servicio"
    )

    class Meta:
        model = RegistroHorasTecnico
        fields = ['hora_inicio', 'hora_fin', 'tipo_hora', 'servicio', 'descripcion']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'tipo_hora': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.tecnico = kwargs.pop('tecnico', None)  # Obtener el técnico del kwargs
        super().__init__(*args, **kwargs)

        # Calcular la fecha límite (15 días atrás desde hoy) - solo para servicios COMPLETADO
        fecha_limite = timezone.now().date() - timedelta(days=15)

        # Filtrar servicios por estado y sucursal del técnico
        # Solo aplicar filtro de fecha para servicios COMPLETADO
        servicios_query = Servicio.objects.filter(
            estado__in=["EN_PROCESO", "PROGRAMADO", "A_FACTURAR", "COMPLETADO"]
        )
        
        # Aplicar filtro de fecha solo para servicios COMPLETADO
        servicios_query = servicios_query.filter(
            models.Q(estado__in=["EN_PROCESO", "PROGRAMADO", "A_FACTURAR"]) |
            models.Q(estado="COMPLETADO", fecha_servicio__gte=fecha_limite)
        )
        
        if self.tecnico and self.tecnico.sucursal:
            servicios_query = servicios_query.filter(preorden__sucursal=self.tecnico.sucursal)
        self.fields['servicio'].queryset = servicios_query

        # Personalizar la etiqueta de los servicios en la lista desplegable
        self.fields['servicio'].label_from_instance = lambda obj: f"Orden {obj.id} - {obj.preorden.cliente.razon_social} - {obj.preorden.equipo.numero_serie} - {obj.get_estado_display()}"

        # Agrupar actividades por disponibilidad y generación de ingreso
        actividades = ActividadTrabajo.objects.all().order_by('disponibilidad', 'genera_ingreso', 'nombre')
        choices = {}
        
        for actividad in actividades:
            # Crear etiquetas más cortas para las categorías
            if actividad.disponibilidad == 'DISPONIBLE':
                if actividad.genera_ingreso == 'INGRESO':
                    categoria = "Horas Disponibles - GI"
                else:
                    categoria = "Horas Disponibles - NI"
            else:
                categoria = "Horas No Disponibles"
                
            if categoria not in choices:
                choices[categoria] = []
            choices[categoria].append((actividad.id, actividad.nombre))

        self.fields['tipo_hora'].choices = [(None, "Selecciona una actividad")] + [
            (categoria, opciones) for categoria, opciones in choices.items()
        ]

    def clean(self):
        cleaned_data = super().clean()
        tipo_hora = cleaned_data.get("tipo_hora")
        servicio = cleaned_data.get("servicio")
        numero_informe = cleaned_data.get("numero_informe")

        # Lógica principal: verificar si la actividad requiere servicio
        if tipo_hora and tipo_hora.requiere_servicio:
            if not servicio:
                if numero_informe:
                    # Calcular la fecha límite para la búsqueda por número de informe (solo para COMPLETADO)
                    fecha_limite = timezone.now().date() - timedelta(days=15)
                    servicio = Servicio.objects.filter(
                        numero_orden=numero_informe, 
                        estado__in=['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR', 'COMPLETADO']
                    ).filter(
                        models.Q(estado__in=['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR']) |
                        models.Q(estado='COMPLETADO', fecha_servicio__gte=fecha_limite)
                    ).first()
                    if not servicio:
                        self.add_error("numero_informe", "No se encontró un servicio con ese número de informe en estado válido o es muy antiguo (más de 15 días para servicios completados).")
                    else:
                        cleaned_data["servicio"] = servicio
                else:
                    self.add_error("servicio", "Esta actividad requiere asociar un servicio.")

        # Validar que el servicio esté en un estado válido y no sea muy antiguo (solo para COMPLETADO)
        if servicio:
            fecha_limite = timezone.now().date() - timedelta(days=15)
            if servicio.estado not in ['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR', 'COMPLETADO']:
                self.add_error("servicio", "Solo se pueden registrar horas en servicios en proceso, programados, finalizados a facturar o completados recientemente.")
            elif servicio.estado == 'COMPLETADO' and servicio.fecha_servicio < fecha_limite:
                self.add_error("servicio", "No se pueden registrar horas en servicios completados con más de 15 días de antigüedad.")
        
        return cleaned_data

from django import forms

class AprobacionHorasForm(forms.Form):
    aprobar = forms.BooleanField(required=False, label="Aprobar todas las horas")

class FiltroExportacionHorasForm(forms.Form):
    fecha_inicio = forms.DateField(
        label='Fecha de Inicio',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    fecha_fin = forms.DateField(
        label='Fecha de Fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    tecnico = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol='TECNICO').order_by('apellido', 'nombre'),
        label='Técnico (Opcional)',
        required=False,
        empty_label="Todos los técnicos",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class FiltroMetricasTecnicosForm(forms.Form):
    """
    Formulario para filtrar métricas de técnicos por mes y técnico específico
    """
    mes = forms.DateField(
        label='Mes',
        widget=forms.DateInput(attrs={
            'type': 'month', 
            'class': 'form-control',
            'onchange': 'this.form.submit()'
        }),
        required=False,
        help_text="Selecciona el mes para ver las métricas"
    )
    tecnico = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol='TECNICO').order_by('apellido', 'nombre'),
        label='Técnico',
        required=False,
        empty_label="Todos los técnicos",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        })
    )

class PermisoAusenciaForm(forms.ModelForm):
    """
    Formulario para solicitar permisos de ausencia
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar widgets con clases Bootstrap
        self.fields['tipo_permiso'].widget.attrs.update({
            'class': 'form-select',
            'required': 'required'
        })
        
        self.fields['motivo'].widget.attrs.update({
            'class': 'form-control',
            'rows': '4',
            'placeholder': 'Describe el motivo de tu solicitud de permiso...',
            'required': 'required'
        })
        
        self.fields['fecha_inicio'].widget.attrs.update({
            'class': 'form-control',
            'type': 'date',
            'required': 'required'
        })
        
        self.fields['fecha_fin'].widget.attrs.update({
            'class': 'form-control',
            'type': 'date',
            'required': 'required'
        })
        
        self.fields['justificativo'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*,.pdf,.doc,.docx'
        })
        
        self.fields['descripcion_justificativo'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Descripción del justificativo (opcional)'
        })
    
    class Meta:
        model = PermisoAusencia
        fields = [
            'tipo_permiso', 'motivo', 'fecha_inicio', 'fecha_fin',
            'justificativo', 'descripcion_justificativo'
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio > fecha_fin:
                raise forms.ValidationError(
                    "La fecha de inicio no puede ser posterior a la fecha de fin."
                )
            
            # Verificar que no sea en el pasado
            from django.utils import timezone
            hoy = timezone.now().date()
            if fecha_inicio < hoy:
                raise forms.ValidationError(
                    "No se pueden solicitar permisos para fechas pasadas."
                )
        
        return cleaned_data

class AprobarPermisoForm(forms.ModelForm):
    """
    Formulario para aprobar/rechazar permisos (solo para gerentes)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['observaciones_aprobacion'].widget.attrs.update({
            'class': 'form-control',
            'rows': '3',
            'placeholder': 'Observaciones sobre la aprobación/rechazo...'
        })
    
    class Meta:
        model = PermisoAusencia
        fields = ['observaciones_aprobacion']
