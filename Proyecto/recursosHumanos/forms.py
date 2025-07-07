from django import forms
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

        # Filtrar servicios por estado y sucursal del técnico
        servicios_query = Servicio.objects.filter(estado="EN_PROCESO")
        if self.tecnico and self.tecnico.sucursal:
            servicios_query = servicios_query.filter(preorden__sucursal=self.tecnico.sucursal)
        self.fields['servicio'].queryset = servicios_query

        # Personalizar la etiqueta de los servicios en la lista desplegable
        self.fields['servicio'].label_from_instance = lambda obj: f"Orden {obj.id} - {obj.preorden.equipo.numero_serie} - {obj.get_estado_display()}"

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

        if tipo_hora and tipo_hora.disponibilidad == "DISPONIBLE" and tipo_hora.genera_ingreso == "INGRESO":
            if not servicio:
                if numero_informe:
                    servicio = Servicio.objects.filter(numero_orden=numero_informe, estado='EN_PROCESO').first()
                    if not servicio:
                        self.add_error("numero_informe", "No se encontró un servicio con ese número de informe en estado EN PROCESO.")
                    else:
                        cleaned_data["servicio"] = servicio
                else:
                    self.add_error("servicio", "Debe ingresar el número de informe o seleccionar un servicio.")

        if tipo_hora and (tipo_hora.disponibilidad != "DISPONIBLE" or tipo_hora.genera_ingreso != "INGRESO"):
            cleaned_data["servicio"] = None  # No permitir servicio para horas no productivas

        if servicio and servicio.estado and servicio.estado not in ['EN_PROCESO']:
            self.add_error("servicio", "Solo se pueden registrar horas en servicios en proceso.")

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
