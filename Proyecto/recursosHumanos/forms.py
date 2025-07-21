from django import forms
from django.utils import timezone
from datetime import timedelta
from gestionDeTaller.models import Servicio
from recursosHumanos.models import RegistroHorasTecnico, ActividadTrabajo

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

        # Calcular la fecha límite (15 días atrás desde hoy)
        fecha_limite = timezone.now().date() - timedelta(days=15)

        # Filtrar servicios por estado y sucursal del técnico
        # Incluir servicios completados solo si no han pasado más de 15 días
        servicios_query = Servicio.objects.filter(
            estado__in=["EN_PROCESO", "PROGRAMADO", "A_FACTURAR", "COMPLETADO"]
        ).filter(
            # Para servicios completados, verificar que no sean más antiguos de 15 días
            fecha_servicio__gte=fecha_limite
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

        # Nueva lógica: verificar si la actividad requiere servicio
        if tipo_hora and tipo_hora.requiere_servicio:
            if not servicio:
                if numero_informe:
                    # Calcular la fecha límite para la búsqueda por número de informe
                    fecha_limite = timezone.now().date() - timedelta(days=15)
                    servicio = Servicio.objects.filter(
                        numero_orden=numero_informe, 
                        estado__in=['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR', 'COMPLETADO'],
                        fecha_servicio__gte=fecha_limite
                    ).first()
                    if not servicio:
                        self.add_error("numero_informe", "No se encontró un servicio con ese número de informe en estado válido o es muy antiguo (más de 15 días).")
                    else:
                        cleaned_data["servicio"] = servicio
                else:
                    self.add_error("servicio", "Esta actividad requiere asociar un servicio.")
        
        # Lógica existente para compatibilidad (mantener como fallback)
        elif tipo_hora and tipo_hora.disponibilidad == "DISPONIBLE" and tipo_hora.genera_ingreso == "INGRESO":
            if not servicio:
                if numero_informe:
                    # Calcular la fecha límite para la búsqueda por número de informe
                    fecha_limite = timezone.now().date() - timedelta(days=15)
                    servicio = Servicio.objects.filter(
                        numero_orden=numero_informe, 
                        estado__in=['EN_PROCESO', 'PROGRAMADO', 'A_FACTURAR', 'COMPLETADO'],
                        fecha_servicio__gte=fecha_limite
                    ).first()
                    if not servicio:
                        self.add_error("numero_informe", "No se encontró un servicio con ese número de informe en estado válido o es muy antiguo (más de 15 días).")
                    else:
                        cleaned_data["servicio"] = servicio
                else:
                    self.add_error("servicio", "Las horas productivas deben estar asociadas a un servicio.")

        # Validar que el servicio esté en un estado válido y no sea muy antiguo
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
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha Inicio"
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha Fin"
    )
