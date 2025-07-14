#!/usr/bin/env bash

echo "=== Probando configuración de deploy ==="

# Configurar variables de entorno
export DJANGO_SETTINGS_MODULE=PatagoniaMaquinarias.settings_render
export DEBUG=False
export SECRET_KEY="django-insecure-rr%o!9z(2r-o&l-#ca0fddq38*583@b%m@+wfwgcvyyu)4_4k&"

# Cambiar al directorio del proyecto
cd Proyecto

echo "Directorio actual: $(pwd)"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

# Verificar que Django puede importar la configuración
echo "=== Verificando configuración de Django ==="
python -c "import django; django.setup(); print('✅ Django configurado correctamente')"

# Verificar que las aplicaciones se pueden importar
echo "=== Verificando aplicaciones ==="
python -c "import django; django.setup(); from django.apps import apps; print('✅ Aplicaciones cargadas:', [app.name for app in apps.get_app_configs()])"

# Verificar configuración de base de datos
echo "=== Verificando configuración de base de datos ==="
python -c "from django.conf import settings; print('✅ Base de datos configurada:', settings.DATABASES['default']['ENGINE'])"

echo "=== Configuración verificada correctamente ===" 