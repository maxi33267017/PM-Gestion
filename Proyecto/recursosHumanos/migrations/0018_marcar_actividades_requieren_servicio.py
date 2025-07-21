from django.db import migrations

def marcar_actividades_requieren_servicio(apps, schema_editor):
    ActividadTrabajo = apps.get_model('recursosHumanos', 'ActividadTrabajo')
    
    actividades_requieren_servicio = [
        "Servicio Remoto",
        "Servicio / Reparacion en Campo", 
        "Servicio / Reparacion en Taller"
    ]
    
    ActividadTrabajo.objects.filter(
        nombre__in=actividades_requieren_servicio
    ).update(requiere_servicio=True)

def desmarcar_actividades_requieren_servicio(apps, schema_editor):
    ActividadTrabajo = apps.get_model('recursosHumanos', 'ActividadTrabajo')
    
    actividades_requieren_servicio = [
        "Servicio Remoto",
        "Servicio / Reparacion en Campo", 
        "Servicio / Reparacion en Taller"
    ]
    
    ActividadTrabajo.objects.filter(
        nombre__in=actividades_requieren_servicio
    ).update(requiere_servicio=False)

class Migration(migrations.Migration):
    dependencies = [
        ('recursosHumanos', '0017_actividadtrabajo_requiere_servicio'),
    ]
    
    operations = [
        migrations.RunPython(
            marcar_actividades_requieren_servicio,
            desmarcar_actividades_requieren_servicio
        ),
    ] 