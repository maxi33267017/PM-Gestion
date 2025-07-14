# Changelog - Deploy en Render.com

## Cambios Realizados

### 1. Dependencias (requirements.txt)
- ✅ Reemplazado `mysqlclient==2.2.0` por `psycopg2-binary==2.9.9` para PostgreSQL
- ✅ Agregado `whitenoise==6.6.0` para servir archivos estáticos
- ✅ Agregado `gunicorn==21.2.0` como servidor WSGI
- ✅ Agregado `dj-database-url==2.1.0` para manejar URLs de base de datos
- ✅ Eliminado duplicados en requirements.txt

### 2. Configuración de Base de Datos
- ✅ Creado `settings_render.py` para configuración específica de Render.com
- ✅ Configurado para usar PostgreSQL en producción
- ✅ Configurado para usar MySQL en desarrollo
- ✅ Agregado manejo de variables de entorno para DATABASE_URL
- ✅ Configurado conexiones persistentes a la base de datos

### 3. Archivos Estáticos
- ✅ Configurado WhiteNoise para servir archivos estáticos en producción
- ✅ Agregado middleware de WhiteNoise
- ✅ Configurado STATIC_ROOT y STATICFILES_STORAGE

### 4. Seguridad
- ✅ Configurado DEBUG=False en producción
- ✅ Agregado configuraciones de seguridad (HSTS, XSS, etc.)
- ✅ Configurado cookies seguras (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- ✅ Configurado manejo de SECRET_KEY desde variables de entorno

### 5. Docker y Build
- ✅ Actualizado Dockerfile para usar PostgreSQL
- ✅ Agregado comando de inicio con gunicorn
- ✅ Creado script `build.sh` para Render.com
- ✅ Configurado directorio de archivos estáticos

### 6. Configuración de Render.com
- ✅ Creado `render.yaml` con configuración del servicio
- ✅ Configurado variables de entorno
- ✅ Configurado comandos de build y start
- ✅ Configurado puerto dinámico ($PORT)

### 7. Manejo de Errores
- ✅ Creado templates 404.html y 500.html
- ✅ Configurado logging para producción
- ✅ Configurado notificaciones de errores por email
- ✅ Configurado ADMINS para reportes de errores

### 8. Optimizaciones
- ✅ Configurado caché en memoria
- ✅ Configurado conexiones persistentes a la base de datos
- ✅ Configurado compresión de archivos estáticos

## Archivos Creados/Modificados

### Nuevos Archivos:
- `build.sh` - Script de build para Render.com
- `start.sh` - Script de inicio para Render.com
- `render.yaml` - Configuración de Render.com
- `README_DEPLOY.md` - Guía de deploy
- `CHANGELOG_DEPLOY.md` - Este archivo
- `Proyecto/PatagoniaMaquinarias/settings_render.py` - Configuración de producción
- `Proyecto/templates/404.html` - Template de error 404
- `Proyecto/templates/500.html` - Template de error 500

### Archivos Modificados:
- `requirements.txt` - Dependencias actualizadas
- `Dockerfile` - Configuración para PostgreSQL y gunicorn
- `Proyecto/PatagoniaMaquinarias/settings.py` - Variables de entorno
- `Proyecto/PatagoniaMaquinarias/wsgi.py` - Configuración de settings

## Variables de Entorno Requeridas

En Render.com, configurar:

```bash
SECRET_KEY=<generado automáticamente>
DEBUG=False
ALLOWED_HOSTS=tu-dominio.onrender.com
DATABASE_URL=postgresql://patagonia:MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7@dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com/patagonia_81l3
DJANGO_SETTINGS_MODULE=Proyecto.PatagoniaMaquinarias.settings_render
```

## Comandos de Deploy

1. **Build Command**: `./build.sh`
2. **Start Command**: `./start.sh`

## Próximos Pasos

1. Subir todos los cambios a Git
2. Conectar el repositorio a Render.com
3. Configurar las variables de entorno en Render.com
4. Hacer deploy del servicio web
5. Verificar que la aplicación funcione correctamente
6. Crear superusuario si es necesario 