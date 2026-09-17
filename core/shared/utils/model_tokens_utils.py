import logging

import tiktoken

from core.shared.config.model_mapper_tiktoken import VALID_MODELS
from core.shared.enums.model import ModelType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


def is_deepseek(model: ModelType) -> bool:
    """Check if the model is DeepSeek."""
    return model in (ModelType.DEEPSEEK_V4_PRO, ModelType.DEEPSEEK_FLASH)


def is_qwen3(model: ModelType) -> bool:
    return model in (
        ModelType.QWEN3_8B,
        ModelType.QWEN3_14B_BASE,
        ModelType.QWEN3_14B,
        ModelType.QWEN3_32B,
    )


def is_ollama_thinking_model(model: ModelType) -> bool:
    return is_qwen3(model) or model in (
        ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS,
        ModelType.GPT_OSS_20B,
        ModelType.GEMMA4_31B_IQ3,
    )


def _ollama_runtime_options(model: ModelType, *, max_tokens: int | None = None) -> dict:
    from core.shared.utils.model_capabilities import get_model_capabilities

    caps = get_model_capabilities(model)
    num_predict = caps.native_max_output_tokens
    # Keep num_predict stable at the runner output cap. Resizing it between
    # MAP (e.g. 3758) and REDUCE (e.g. 7349) triggers Ollama context-shift and
    # can drop the system prompt. OpenAI max_tokens still limits the completion.
    return {
        "num_ctx": caps.context_window,
        "num_predict": num_predict,
    }


def completion_extra_kwargs(model: ModelType, *, max_tokens: int | None = None) -> dict:
    """Provider extras for chat.completions.create.

    DeepSeek V4 thinking is on by default. Reasoning tokens count against
    max_tokens and can exhaust a REDUCE budget before any visible
    message.content is written (HTTP 200, finish_reason=length, empty body).

    Qwen3, DeepSeek-R1 distills, gpt-oss, and Gemma 4 have the same failure
    mode on Ollama. Ollama also defaults num_ctx far below the native window
    unless options.num_ctx is sent and the runner is loaded at that size.
    num_predict stays at native_max_output_tokens so the loaded runner does not
    resize between MAP and REDUCE (context-shift drops the system prompt).
    """
    extra_body: dict = {}
    if is_deepseek(model):
        extra_body["thinking"] = {"type": "disabled"}
    if is_ollama_thinking_model(model):
        extra_body["think"] = False
    if model in (
        ModelType.QWEN3_8B,
        ModelType.QWEN3_14B_BASE,
        ModelType.QWEN3_14B,
        ModelType.QWEN3_32B,
        ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS,
        ModelType.GPT_OSS_20B,
        ModelType.GEMMA4_31B_IQ3,
    ):
        extra_body["options"] = _ollama_runtime_options(model, max_tokens=max_tokens)
    if extra_body:
        return {"extra_body": extra_body}
    return {}


def get_encoder(model_type: ModelType) -> tiktoken.Encoding:
    """Return a tiktoken encoding for quota/chunk estimates (API calls only; no local LLMs).

    Non-OpenAI models fall back to cl100k_base. Exact vendor tokenizers are not
    loaded in production — inference runs via remote APIs / Ollama HTTP.
    """
    mapping = (
        VALID_MODELS[model_type].value
        if model_type in VALID_MODELS
        else ModelType.GPT_4.value
    )
    encoding_name = mapping.lower().replace("-", "")

    try:
        return tiktoken.encoding_for_model(encoding_name)
    except KeyError:
        logger.warning(
            "Encoding %s not found for %s, falling back to cl100k_base",
            encoding_name,
            model_type,
        )
        return tiktoken.get_encoding("cl100k_base")
