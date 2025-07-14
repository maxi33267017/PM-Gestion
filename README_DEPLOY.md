# Guía de Deploy en Render.com

## Configuración para Producción

### 1. Variables de Entorno en Render.com

Configura las siguientes variables de entorno en tu servicio web de Render.com:

- `SECRET_KEY`: Clave secreta de Django (se genera automáticamente)
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: `tu-dominio.onrender.com`
- `DATABASE_URL`: `postgresql://patagonia:MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7@dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com/patagonia_81l3`
- `DJANGO_SETTINGS_MODULE`: `PatagoniaMaquinarias.settings_render`

### 2. Configuración del Servicio Web

- **Build Command**: `./build.sh`
- **Start Command**: `./start_production.sh`

### 3. Cambios Realizados

1. **Base de Datos**: Cambiado de MySQL a PostgreSQL
2. **Dependencias**: Agregado `psycopg2-binary`, `whitenoise`, `gunicorn`, `dj-database-url`
3. **Archivos Estáticos**: Configurado WhiteNoise para servir archivos estáticos
4. **Variables de Entorno**: Configurado para usar variables de entorno en producción
5. **Seguridad**: Configuraciones de seguridad para producción

### 4. Estructura de Archivos

- `build.sh`: Script de build para Render.com
- `render.yaml`: Configuración de Render.com
- `Dockerfile`: Configuración de Docker actualizada
- `requirements.txt`: Dependencias actualizadas

### 5. Comandos Importantes

```bash
# Recolectar archivos estáticos
python Proyecto/manage.py collectstatic --noinput

# Ejecutar migraciones
python Proyecto/manage.py migrate

# Crear superusuario (si es necesario)
python Proyecto/manage.py createsuperuser
```

### 6. Troubleshooting

Si la aplicación se cierra temprano:

1. Verifica que todas las variables de entorno estén configuradas
2. Revisa los logs en Render.com
3. Asegúrate de que la base de datos PostgreSQL esté accesible
4. Verifica que el puerto esté configurado correctamente

### 7. URLs Importantes

- **Base de datos externa**: `postgresql://patagonia:MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7@dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com/patagonia_81l3`
- **Comando PSQL**: `PGPASSWORD=MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7 psql -h dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com -U patagonia patagonia_81l3` 