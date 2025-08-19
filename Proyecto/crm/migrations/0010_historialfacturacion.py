# Generated manually for HistorialFacturacion

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0009_campana_modelo_equipo_campana_tipo_equipo'),
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialFacturacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pin_equipo', models.CharField(max_length=50, verbose_name='PIN del Equipo')),
                ('fecha_servicio', models.DateField(verbose_name='Fecha de Servicio')),
                ('numero_factura', models.CharField(max_length=50, verbose_name='Número de Factura')),
                ('monto_usd', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto USD')),
                ('tipo_servicio', models.CharField(max_length=100, verbose_name='Tipo de Servicio')),
                ('modelo_equipo', models.CharField(max_length=100, verbose_name='Modelo del Equipo')),
                ('fecha_importacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Importación')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clientes.cliente', verbose_name='Cliente')),
                ('equipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='clientes.equipo', verbose_name='Equipo')),
            ],
            options={
                'verbose_name': 'Historial de Facturación',
                'verbose_name_plural': 'Historial de Facturación',
                'ordering': ['-fecha_servicio'],
            },
        ),
    ]
