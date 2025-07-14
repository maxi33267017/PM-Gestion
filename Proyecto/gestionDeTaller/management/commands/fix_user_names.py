from django.core.management.base import BaseCommand
from recursosHumanos.models import Usuario


class Command(BaseCommand):
    help = 'Corrige los nombres de usuario que están vacíos'

    def handle(self, *args, **options):
        self.stdout.write('Verificando usuarios con nombres vacíos...')
        
        # Obtener usuarios sin nombre completo
        usuarios_sin_nombre = Usuario.objects.filter(
            first_name='', last_name=''
        ).exclude(email__icontains='admin')  # Excluir admin si existe
        
        self.stdout.write(f'Encontrados {usuarios_sin_nombre.count()} usuarios sin nombre completo')
        
        for usuario in usuarios_sin_nombre:
            self.stdout.write(f'Usuario: {usuario.email} | Nombre: {usuario.nombre}')
            
            # Intentar extraer nombre del email o username
            if usuario.email and '@' in usuario.email:
                # Extraer nombre del email (parte antes del @)
                nombre_email = usuario.email.split('@')[0]
                # Capitalizar y separar por puntos o guiones bajos
                if '.' in nombre_email:
                    partes = nombre_email.split('.')
                    usuario.first_name = partes[0].capitalize()
                    if len(partes) > 1:
                        usuario.last_name = ' '.join(partes[1:]).capitalize()
                elif '_' in nombre_email:
                    partes = nombre_email.split('_')
                    usuario.first_name = partes[0].capitalize()
                    if len(partes) > 1:
                        usuario.last_name = ' '.join(partes[1:]).capitalize()
                else:
                    usuario.first_name = nombre_email.capitalize()
                    usuario.last_name = 'Usuario'
            else:
                # Usar email como nombre
                nombre_email = usuario.email.split('@')[0] if '@' in usuario.email else usuario.email
                usuario.first_name = nombre_email.capitalize()
                usuario.last_name = 'Usuario'
            
            usuario.save()
            self.stdout.write(f'  → Nombre asignado: {usuario.get_full_name()}')
        
        # Mostrar todos los usuarios
        self.stdout.write('\nTodos los usuarios:')
        for usuario in Usuario.objects.all():
            nombre_completo = usuario.get_full_name() or usuario.email
            self.stdout.write(f'- {usuario.email}: {nombre_completo}')
        
        self.stdout.write(self.style.SUCCESS('Proceso completado')) 