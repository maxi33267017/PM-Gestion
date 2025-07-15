# Generated manually for SesionCronometro model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recursosHumanos', '0001_initial'),
        ('gestionDeTaller', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SesionCronometro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hora_inicio', models.DateTimeField(auto_now_add=True, verbose_name='Hora de Inicio')),
                ('hora_fin', models.DateTimeField(blank=True, null=True, verbose_name='Hora de Fin')),
                ('activa', models.BooleanField(default=True, verbose_name='¿Activa?')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')),
                ('fecha_modificacion', models.DateTimeField(auto_now=True, verbose_name='Última Modificación')),
                ('actividad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recursosHumanos.actividadtrabajo', verbose_name='Actividad')),
                ('servicio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestionDeTaller.servicio', verbose_name='Servicio')),
                ('tecnico', models.ForeignKey(limit_choices_to={'rol': 'TECNICO'}, on_delete=django.db.models.deletion.CASCADE, to='recursosHumanos.usuario')),
            ],
            options={
                'verbose_name': 'Sesión de Cronómetro',
                'verbose_name_plural': 'Sesiones de Cronómetro',
                'ordering': ['-fecha_creacion'],
            },
        ),
    ] 