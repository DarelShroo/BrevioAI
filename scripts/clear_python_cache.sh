#!/bin/bash

# Script para limpiar caché de Python
# Uso: ./clear_python_cache.sh /ruta/a/tu/carpeta

# Verificar si se proporcionó un argumento
if [ -z "$1" ]; then
  echo "Error: Debes proporcionar la ruta del directorio."
  echo "Uso: $0 /ruta/a/tu/carpeta"
  exit 1
fi

DIRECTORIO="$1"

# Verificar si el directorio existe
if [ ! -d "$DIRECTORIO" ]; then
  echo "Error: El directorio '$DIRECTORIO' no existe."
  exit 1
fi

echo "Eliminando caché de Python en $DIRECTORIO..."

# Eliminar directorios de caché
find "$DIRECTORIO" -type d \( \
  -name "__pycache__" \
  -o -name ".mypy_cache" \
  -o -name ".pytest_cache" \
  -o -name ".ipynb_checkpoints" \
\) -exec rm -rf {} + 2>/dev/null

# Eliminar archivos compilados de Python
find "$DIRECTORIO" -type f \( \
  -name "*.pyc" \
  -o -name "*.pyo" \
  -o -name "*.pyd" \
  -o -name "*.py.class" \
\) -delete 2>/dev/null

echo -e "\n✅ Caché de Python eliminada con éxito en $DIRECTORIO"
echo "Se eliminó:"
echo "  - Directorios __pycache__, .mypy_cache, .pytest_cache"
echo "  - Archivos *.pyc, *.pyo y otros archivos compilados"