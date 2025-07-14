FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    bash \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hacer el script ejecutable
RUN chmod +x build.sh

# Crear directorio para archivos estáticos
RUN mkdir -p /app/Proyecto/staticfiles

EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "Proyecto.PatagoniaMaquinarias.wsgi:application", "--settings=Proyecto.PatagoniaMaquinarias.settings_render"]