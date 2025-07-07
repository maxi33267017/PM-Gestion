from django import forms
from .models import Cliente, ContactoCliente, TipoEquipo, ModeloEquipo, ModeloMotor, Equipo, RegistroHorometro
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django_select2.forms import Select2Widget

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'tipo', 'sucursal', 'razon_social', 'nombre_fantasia',
            'cuit', 'email', 'telefono', 'direccion',
            'codigo_postal', 'ciudad', 'provincia', 'observaciones',
            'activo'
        ]
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 4}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Cliente'))

class ContactoClienteForm(forms.ModelForm):
    class Meta:
        model = ContactoCliente
        exclude = ['cliente']  # Excluir el campo cliente
        fields = [
            'nombre', 'apellido', 'rol', 'email', 'telefono_fijo',
            'telefono_celular', 'es_contacto_principal', 'activo'
        ]
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Contacto'))

class TipoEquipoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipo
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Tipo de Equipo'))

class ModeloEquipoForm(forms.ModelForm):
    class Meta:
        model = ModeloEquipo
        fields = ['tipo_equipo', 'nombre', 'marca', 'descripcion', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Modelo'))

class ModeloMotorForm(forms.ModelForm):
    class Meta:
        model = ModeloMotor
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Motor'))

class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        exclude = ['cliente']  # Excluir el campo cliente
        fields = [
            'modelo', 'numero_serie',
            'modelo_motor', 'numero_serie_motor', 'año_fabricacion',
            'fecha_venta', 'notas', 'activo'
        ]
        widgets = {
            'modelo': Select2Widget(attrs={'class': 'form-control'}),
            'modelo_motor': Select2Widget(attrs={'class': 'form-control'}),
            'fecha_venta': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notas': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Equipo'))

class RegistroHorometroForm(forms.ModelForm):
    class Meta:
        model = RegistroHorometro
        fields = [
            'equipo', 'horas', 'origen',
            'observaciones'
        ]
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Registro'))