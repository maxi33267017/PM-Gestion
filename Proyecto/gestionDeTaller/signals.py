from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PreOrden
from clientes.models import RegistroHorometro

@receiver(post_save, sender=PreOrden)
def registrar_horometro_preorden(sender, instance, created, **kwargs):
    if created and instance.horometro:  # Verifica que la preorden es nueva y que tiene un horómetro
        RegistroHorometro.objects.create(
            equipo=instance.equipo,
            horas=instance.horometro,
            origen='PRE_ORDER',
            usuario=instance.creado_por,
            observaciones="Registro automático desde preorden"
        )