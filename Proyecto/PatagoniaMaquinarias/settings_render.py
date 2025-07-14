"""
Django settings for PatagoniaMaquinarias project on Render.com
"""

import os
from pathlib import Path
from .settings import *

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-rr%o!9z(2r-o&l-#ca0fddq38*583@b%m@+wfwgcvyyu)4_4k&')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Database configuration for Render.com
if os.environ.get('DATABASE_URL'):
    # Production database (PostgreSQL)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Fallback to development database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'patagonia_81l3'),
            'USER': os.environ.get('DB_USER', 'patagonia'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7'),
            'HOST': os.environ.get('DB_HOST', 'dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Configuración de conexión a la base de datos para producción
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutos
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20,
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuración de archivos estáticos para producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Agregar WhiteNoise al middleware
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Debe ir después de SecurityMiddleware
] + MIDDLEWARE

# Configuración de seguridad para producción
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Configuración de sesiones para producción
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Configuración de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Configuración de manejo de errores
ADMINS = [
    ('Admin', 'maxi.caamano@patagoniamaquinarias.com'),
]

# Configuración de correo para errores en producción
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'maxi.caamano@patagoniamaquinarias.com'
EMAIL_HOST_PASSWORD = 'frli wbco botx chtr'
DEFAULT_FROM_EMAIL = 'Patagonia Maquinarias <maxi.caamano@patagoniamaquinarias.com>'

# Configuración de caché para producción
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
} 