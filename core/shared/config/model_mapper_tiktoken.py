# Map models to valid existing models in tiktoken
from core.shared.enums.model import ModelType

VALID_MODELS: dict[ModelType, ModelType] = {
    ModelType.GPT_4O_MINI: ModelType.GPT_4O_MINI,
    ModelType.GPT_4_1_NANO: ModelType.GPT_4,
}
