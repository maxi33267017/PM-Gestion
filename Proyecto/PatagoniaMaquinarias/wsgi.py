"""
WSGI config for PatagoniaMaquinarias project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings if DATABASE_URL is set (Render.com)
if os.environ.get('DATABASE_URL'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')

application = get_wsgi_application()
