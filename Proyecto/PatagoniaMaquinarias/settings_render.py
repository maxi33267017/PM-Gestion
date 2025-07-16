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

# Configuración de logging para debugging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log de configuración
logger.info(f"DEBUG: {DEBUG}")
logger.info(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
logger.info(f"DATABASE_URL definida: {'SÍ' if os.environ.get('DATABASE_URL') else 'NO'}")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,pm-gestion.onrender.com').split(',')

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Database configuration for Render.com
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'patagonia_81l3',
        'USER': 'patagonia',
        'PASSWORD': 'MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7',
        'HOST': 'dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com',
        'PORT': '5432',
    }
}

# Configuración de conexión a la base de datos para producción
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutos

LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'es-ar')

TIME_ZONE = os.environ.get('TIME_ZONE', 'America/Argentina/Buenos_Aires')
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuración de AWS S3 para archivos media
USE_S3 = os.environ.get('USE_S3', 'False').lower() == 'true'

if USE_S3:
    # Configuración de AWS S3
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_LOCATION = 'media'
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    
    # Configurar storage para archivos media
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    
    # Los archivos estáticos seguirán usando WhiteNoise (no S3)
    # STATICFILES_STORAGE se mantiene como WhiteNoise más abajo
    
    # Agregar django-storages a INSTALLED_APPS
    INSTALLED_APPS += ['storages']
    
    print(f"✅ Configuración AWS S3 activada")
    print(f"   Bucket: {AWS_STORAGE_BUCKET_NAME}")
    print(f"   Región: {AWS_S3_REGION_NAME}")
    print(f"   Media URL: {MEDIA_URL}")
else:
    # Configuración local para archivos media
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    print(f"✅ Usando almacenamiento local: {MEDIA_ROOT}")

# Media files (uploads) - Configuración base

# Configuración de archivos estáticos para producción
# Usar CompressedStaticFilesStorage en lugar de CompressedManifestStaticFilesStorage
# para evitar problemas con el manifest file
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Configuración adicional de WhiteNoise
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Configurar WhiteNoise para servir archivos media
WHITENOISE_ROOT = os.path.join(BASE_DIR, 'media')

# Agregar directorio media a STATICFILES_DIRS para que WhiteNoise lo sirva
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'media'),  # Agregar media como archivos estáticos
]

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
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# Para desarrollo local, comentar las líneas anteriores
# Para producción en Render.com, descomentar las líneas anteriores

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

CSRF_TRUSTED_ORIGINS = [
    "https://pm-gestion.onrender.com"
]