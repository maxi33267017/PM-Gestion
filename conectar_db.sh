#!/usr/bin/env bash

echo "=== Conectando a la Base de Datos PostgreSQL ==="
echo "Host: dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com"
echo "Database: patagonia_81l3"
echo "Usuario: patagonia"
echo ""

# Conectar a la base de datos
PGPASSWORD=MyE8vlJgKi4ADY7NRgysAUTynAbQ0DF7 psql -h dpg-d1qhtk6r433s73edhccg-a.oregon-postgres.render.com -U patagonia patagonia_81l3 