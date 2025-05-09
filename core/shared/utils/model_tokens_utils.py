import logging
from typing import Union, cast

import tiktoken
from transformers.models.auto.tokenization_auto import AutoTokenizer  # type: ignore
from transformers.tokenization_utils_fast import PreTrainedTokenizerFast

from core.shared.config.model_mapper_tiktoken import VALID_MODELS
from core.shared.enums.model import ModelType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


def is_deepseek(model: ModelType) -> bool:
    """Check if the model is DeepSeek."""
    return model == ModelType.DEEPSEEK_CHAT


def get_encoder(
    model_type: ModelType,
) -> Union[tiktoken.Encoding, PreTrainedTokenizerFast]:
    """Get the appropriate tokenizer or encoding for the given model type."""
    if is_deepseek(model_type):
        try:
            auto_tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-v3")
            return cast(PreTrainedTokenizerFast, auto_tokenizer)
        except Exception as e:
            logger.error(f"Failed to load DeepSeek tokenizer: {e}")
            raise RuntimeError(f"Could not load tokenizer for {model_type}: {e}")

    if model_type in VALID_MODELS:
        mapping = VALID_MODELS[model_type].value
    else:
        mapping = ModelType.GPT_4.value

    encoding_name = mapping.lower().replace("-", "")
    try:
        return tiktoken.encoding_for_model(encoding_name)
    except KeyError:
        logger.warning(
            f"Encoding {encoding_name} not found, falling back to cl100k_base"
        )
        return tiktoken.get_encoding("cl100k_base")
