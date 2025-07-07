from django.apps import AppConfig


class GestiondetallerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestionDeTaller'

    def ready(self):
        import gestionDeTaller.signals  # Importa las señales al iniciar la app