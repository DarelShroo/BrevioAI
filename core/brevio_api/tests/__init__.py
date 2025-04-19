import core.brevio as brevio
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models import (
    ConfigModel,
    FileConfig,
    PromptConfig,
    SummaryConfig,
    SummaryResponse,
)

directory_managers = {"directory_manager": DirectoryManager}

model_classes = (
    ConfigModel,
    FileConfig,
    PromptConfig,
    SummaryResponse,
    SummaryConfig,
)

service_classes = ()

__all__ = ["service_classes", "model_classes", "directory_managers", "brevio"]
