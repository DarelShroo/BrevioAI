#!/bin/bash
# Script para eliminar caché de Python y carpetas específicas
# Este script elimina los directorios de caché de Python y archivos compilados
# en un directorio específico"
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
echo "  - Directorios: __pycache__, .mypy_cache, .pytest_cache, .ipynb_checkpoints"
echo "  - Archivos: *.pyc, *.pyo, *.pyd, *.py.class"

# Eliminar la carpeta "data" si existe
if [ -d "$DIRECTORIO/data" ]; then
  rm -rf "$DIRECTORIO/data"
  echo -e "\n✅ Carpeta 'data' eliminada de $DIRECTORIO"
else
  echo -e "\nℹ️  La carpeta 'data' no existe en $DIRECTORIO"
fi

# Eliminar la carpeta "backend/audios" si existe
if [ -d "$DIRECTORIO/backend/audios" ]; then
  rm -rf "$DIRECTORIO/backend/audios"
  echo -e "\n✅ Carpeta 'backend/audios' eliminada de $DIRECTORIO/backend"
else
  echo -e "\nℹ️  La carpeta 'backend/audios' no existe en $DIRECTORIO/backend"
fi
