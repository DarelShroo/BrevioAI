import os
import sys

# Asegúrate de que el directorio principal esté en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importa los módulos
import brevio
from brevio.managers.directory_manager import DirectoryManager
from brevio.models import (
    ConfigModel,
    FileConfig,
    PromptConfig,
    SummaryConfig,
    SummaryResponse,
)

# Usa diferentes nombres para evitar colisiones con los módulos
directory_managers = {"directory_manager": DirectoryManager}
model_classes = (
    ConfigModel,
    FileConfig,
    PromptConfig,
    SummaryResponse,
    SummaryConfig,
)
service_classes = ()

# Define qué se expone cuando alguien importa este módulo
__all__ = ["service_classes", "model_classes", "directory_managers", "brevio"]
