from django.db import migrations

def update_old_embudo_states(apps, schema_editor):
    """Actualizar estados viejos de embudos a los nuevos estados"""
    EmbudoVentas = apps.get_model('crm', 'EmbudoVentas')
    
    # Mapeo de estados viejos a nuevos
    state_mapping = {
        'CONTACTO_INICIAL': 'PENDIENTE',
        'CALIFICACION': 'CONTACTADO',
        'PROPUESTA': 'CON_RESPUESTA',
        'NEGOCIACION': 'PRESUPUESTADO',
        'CIERRE': 'VENTA_EXITOSA',
        'PERDIDO': 'VENTA_PERDIDA',
    }
    
    # Actualizar embudos con estados viejos
    for old_state, new_state in state_mapping.items():
        EmbudoVentas.objects.filter(etapa=old_state).update(etapa=new_state)
        print(f"Actualizados {EmbudoVentas.objects.filter(etapa=new_state).count()} embudos de {old_state} a {new_state}")

def reverse_update_old_embudo_states(apps, schema_editor):
    """Revertir la actualización de estados"""
    EmbudoVentas = apps.get_model('crm', 'EmbudoVentas')
    
    # Mapeo inverso
    state_mapping = {
        'PENDIENTE': 'CONTACTO_INICIAL',
        'CONTACTADO': 'CALIFICACION',
        'CON_RESPUESTA': 'PROPUESTA',
        'PRESUPUESTADO': 'NEGOCIACION',
        'VENTA_EXITOSA': 'CIERRE',
        'VENTA_PERDIDA': 'PERDIDO',
    }
    
    # Revertir cambios
    for new_state, old_state in state_mapping.items():
        EmbudoVentas.objects.filter(etapa=new_state).update(etapa=old_state)

class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0015_alter_contactocliente_resultado_and_more'),
    ]

    operations = [
        migrations.RunPython(update_old_embudo_states, reverse_update_old_embudo_states),
    ]
