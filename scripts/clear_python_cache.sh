#!/bin/bash

if [ -z "$1" ]; then
  echo "Error: Debes proporcionar la ruta del directorio."
  echo "Uso: ./clear_python_cache.sh /ruta/a/tu/carpeta"
  exit 1
fi

# Especifica el directorio en el que quieres ejecutar el script
DIRECTORIO_ESPECIFICO="$1"

# Verifica si el directorio existe
if [ ! -d "$DIRECTORIO_ESPECIFICO" ]; then
  echo "Error: El directorio $DIRECTORIO_ESPECIFICO no existe."
  exit 1
fi

echo "Eliminando caché de Python en $DIRECTORIO_ESPECIFICO..."

# Buscar y eliminar todas las carpetas __pycache__ y archivos .pyc/.pyo recursivamente en el directorio especificado
find "$DIRECTORIO_ESPECIFICO" -type d -name "__pycache__" -exec rm -rf {} + 
find "$DIRECTORIO_ESPECIFICO" -type f -name "*.pyc" -delete
find "$DIRECTORIO_ESPECIFICO" -type f -name "*.pyo" -delete

echo "Caché de Python eliminado con éxito en $DIRECTORIO_ESPECIFICO. 🚀"

