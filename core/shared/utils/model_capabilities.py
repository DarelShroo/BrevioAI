from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from core.shared.enums.model import ModelType


@dataclass(frozen=True)
class ModelCapabilities:
    model: ModelType
    provider: str
    context_window: int
    native_max_output_tokens: int
    max_tokens_per_chunk: int
    reduce_batch_tokens: int
    chunk_overlap: float
    safe_percent: float
    tokenizer: str
    supports_json: bool
    supports_mermaid: bool
    supports_chunking: bool
    reduce_input_token_budget: int
    reduce_safety_margin: int
    reduce_min_batch_tokens: int
    output_padding_tokens: int
    format_safety_margin: int
    min_tokens_for_postprocess: int
    global_map_safety_cap: int
    overhead: int
    min_chunk_tokens: int
    # Vendor Chat Completions / Messages field for the output cap.
    output_token_param: str = "max_tokens"
    supports_temperature: bool = True
    # Official vendor default when temperature is accepted. None if omitted.
    default_temperature: Optional[float] = None
    # None, or the vendor parameter name: reasoning_effort | effort
    reasoning: Optional[str] = None
    reasoning_values: Tuple[str, ...] = ()
    status: str = "stable"
    retirement: Optional[str] = None
    recommended: bool = True


MODEL_CAPABILITIES: Dict[ModelType, ModelCapabilities] = {
    ModelType.GPT_4O_MINI: ModelCapabilities(
        model=ModelType.GPT_4O_MINI,
        provider="openai",
        context_window=128000,
        native_max_output_tokens=16384,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=16000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=12000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=1.0,
        status="stable",
        recommended=True,
    ),
    ModelType.GPT_5_6: ModelCapabilities(
        model=ModelType.GPT_5_6,
        provider="openai",
        context_window=1_050_000,
        native_max_output_tokens=128_000,
        max_tokens_per_chunk=4_000,
        reduce_batch_tokens=12_000,
        chunk_overlap=500,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=25_000,
        reduce_safety_margin=2_000,
        reduce_min_batch_tokens=500,
        output_padding_tokens=1000,
        format_safety_margin=2000,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=6000,
        overhead=2000,
        min_chunk_tokens=100,
        output_token_param="max_completion_tokens",
        supports_temperature=False,
        default_temperature=None,
        reasoning="reasoning_effort",
        reasoning_values=("none", "low", "medium", "high", "xhigh", "max"),
        status="stable",
        recommended=True,
    ),
    ModelType.DEEPSEEK_V4_PRO: ModelCapabilities(
        model=ModelType.DEEPSEEK_V4_PRO,
        provider="deepseek",
        context_window=1_048_576,
        native_max_output_tokens=384_000,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=8000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="hf-deepseek-v3",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=1.0,
    ),
    ModelType.GPT_4: ModelCapabilities(
        model=ModelType.GPT_4,
        provider="openai",
        context_window=8192,
        native_max_output_tokens=8192,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=3500,  # limited context
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=3000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=1.0,
        status="deprecated",
        retirement="2026-10-23",
        recommended=False,
    ),
    ModelType.GEMINI_3_1_FLASH_LITE: ModelCapabilities(
        model=ModelType.GEMINI_3_1_FLASH_LITE,
        provider="google",
        context_window=1_048_576,
        native_max_output_tokens=65_536,
        max_tokens_per_chunk=3000,
        # 1M context is not a REDUCE pack size (lost-in-the-middle). 12k is a
        # stable hierarchical pack, not a context-filling pack.
        reduce_batch_tokens=12_000,
        chunk_overlap=500,
        safe_percent=0.05,
        tokenizer="gemini",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=25_000,
        reduce_safety_margin=2_000,
        reduce_min_batch_tokens=500,
        output_padding_tokens=1000,
        format_safety_margin=2000,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=6000,
        overhead=2000,
        min_chunk_tokens=100,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=1.0,
        # OpenAI-compat maps reasoning_effort → thinking_level.
        # Official Flash-Lite levels: minimal (default), low, medium, high.
        reasoning="reasoning_effort",
        reasoning_values=("minimal", "low", "medium", "high"),
        status="stable",
        recommended=True,
    ),
    ModelType.DEEPSEEK_FLASH: ModelCapabilities(
        model=ModelType.DEEPSEEK_FLASH,
        provider="deepseek",
        context_window=1_048_576,
        native_max_output_tokens=384_000,
        max_tokens_per_chunk=4_000,
        # Native 384k is not a summary call budget. Packs stay small and stable.
        reduce_batch_tokens=8_000,
        chunk_overlap=500,
        safe_percent=0.05,
        tokenizer="deepseek",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=8_000,
        reduce_safety_margin=500,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=1.0,
        recommended=True,
    ),
    ModelType.GROK_4_6: ModelCapabilities(
        model=ModelType.GROK_4_6,
        provider="xai",
        context_window=500_000,
        # Official docs: "No text output limit". Bound output by the documented
        # context window; Brevio still applies summary_max_output_tokens.
        native_max_output_tokens=500_000,
        max_tokens_per_chunk=4_000,
        reduce_batch_tokens=12_000,
        chunk_overlap=500,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=25_000,
        reduce_safety_margin=2_000,
        reduce_min_batch_tokens=500,
        output_padding_tokens=1000,
        format_safety_margin=2000,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=6000,
        overhead=2000,
        min_chunk_tokens=100,
        output_token_param="max_tokens",
        supports_temperature=False,
        default_temperature=None,
        reasoning="reasoning_effort",
        reasoning_values=("low", "medium", "high", "xhigh"),
        status="stable",
        recommended=True,
    ),
    ModelType.CLAUDE_SONNET_5: ModelCapabilities(
        model=ModelType.CLAUDE_SONNET_5,
        provider="anthropic",
        context_window=1_000_000,
        native_max_output_tokens=128_000,
        max_tokens_per_chunk=4_000,
        reduce_batch_tokens=12_000,
        chunk_overlap=500,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=25_000,
        reduce_safety_margin=2_000,
        reduce_min_batch_tokens=500,
        output_padding_tokens=1000,
        format_safety_margin=2000,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=6000,
        overhead=2000,
        min_chunk_tokens=100,
        output_token_param="max_tokens",
        supports_temperature=False,
        default_temperature=None,
        reasoning="effort",
        reasoning_values=("low", "medium", "high", "xhigh", "max"),
        status="stable",
        recommended=True,
    ),
    ModelType.CLAUDE_HAIKU_4_5: ModelCapabilities(
        model=ModelType.CLAUDE_HAIKU_4_5,
        provider="anthropic",
        context_window=200_000,
        native_max_output_tokens=64_000,
        max_tokens_per_chunk=4_000,
        reduce_batch_tokens=8_000,
        chunk_overlap=250,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=8_000,
        reduce_safety_margin=768,
        reduce_min_batch_tokens=250,
        output_padding_tokens=750,
        format_safety_margin=2_000,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=5_000,
        overhead=1_500,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        # Sampling restrictions in official docs apply to Claude 4.7+ and Sonnet 5,
        # not Haiku 4.5. Messages API temperature remains accepted.
        supports_temperature=True,
        default_temperature=1.0,
        status="stable",
        recommended=True,
    ),
    # Official Ollama tag qwen3:14b (same family as Q6_K, typically Q4_K_M).
    ModelType.QWEN3_14B_BASE: ModelCapabilities(
        model=ModelType.QWEN3_14B_BASE,
        provider="ollama",
        context_window=16_384,
        native_max_output_tokens=8192,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=8000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="qwen",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=0.7,
    ),
    # Qwen3-14B Q6_K via Ollama tag qwen3:14b-q6 (~12.1GB, 14.8B, family qwen3).
    # Native context 40_960; local runs keep 16_384 (16GB GPU: ~12GB weights + KV).
    ModelType.QWEN3_14B: ModelCapabilities(
        model=ModelType.QWEN3_14B,
        provider="ollama",
        context_window=16_384,
        native_max_output_tokens=8192,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=8000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="qwen",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=0.7,
    ),
    ModelType.QWEN3_8B: ModelCapabilities(
        model=ModelType.QWEN3_8B,
        provider="ollama",
        context_window=32768,
        native_max_output_tokens=8192,
        max_tokens_per_chunk=3000,
        reduce_batch_tokens=8000,
        chunk_overlap=200,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1500,
        min_tokens_for_postprocess=2000,
        global_map_safety_cap=4000,
        overhead=1000,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=0.7,
    ),
    # Qwen3-32B: 32.8B dense, 64 layers, GQA 64/8.
    # Native context 32_768 (YaRN 131_072 is not used locally: VRAM).
    # Non-thinking max generation 16_384; thinking mode is disabled at call time.
    ModelType.QWEN3_32B: ModelCapabilities(
        model=ModelType.QWEN3_32B,
        provider="ollama",
        context_window=32_768,
        native_max_output_tokens=16_384,
        max_tokens_per_chunk=4_000,
        reduce_batch_tokens=10_000,
        chunk_overlap=250,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=8_000,
        reduce_safety_margin=768,
        reduce_min_batch_tokens=250,
        output_padding_tokens=750,
        format_safety_margin=2_000,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=5_000,
        overhead=1_500,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=0.7,
    ),
    # DeepSeek-R1-Distill-Qwen-32B (Qwen2.5-32B, GQA 40/8, 64 layers, FFN 27648).
    # Local Ollama tag deepseek-r1-local:iq3-xs, IQ3_XS ~13GB.
    # GGUF advertises 131_072 (YaRN); native Qwen2.5 window is 32_768.
    # 131K is not used: KV cache + 3-bit weights will OOM a single GPU.
    # IQ3_XS is lossy vs Q4, so MAP/REDUCE budgets stay below the dense 32B peers.
    ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS: ModelCapabilities(
        model=ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS,
        provider="ollama",
        context_window=32_768,
        native_max_output_tokens=8_192,
        max_tokens_per_chunk=2_500,
        reduce_batch_tokens=6_000,
        chunk_overlap=300,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=5_000,
        reduce_safety_margin=768,
        reduce_min_batch_tokens=250,
        output_padding_tokens=600,
        format_safety_margin=1_500,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=3_500,
        overhead=1_200,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=0.6,
    ),
    # OpenAI gpt-oss:20b via Ollama (~14GB MXFP4). MoE 20.91B total / 3.61B active,
    # 24 layers, 32 experts top-4, GQA 64/8, hidden 2880, sliding window 128.
    # Native context 131_072 via YaRN; local runs keep 32_768 (128K graph ~31GB).
    # Official max output 131_072; summaries cap at 8_192 so MAP fits the 32K window.
    # Reasoning/CoT is disabled at call time (same empty-body failure as R1/Qwen3).
    ModelType.GPT_OSS_20B: ModelCapabilities(
        model=ModelType.GPT_OSS_20B,
        provider="ollama",
        context_window=32_768,
        native_max_output_tokens=8_192,
        max_tokens_per_chunk=3_000,
        reduce_batch_tokens=8_000,
        chunk_overlap=256,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6_000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1_500,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=4_000,
        overhead=1_000,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=1.0,
    ),
    # Gemma 4 31B Dense (30.7B, 60 layers, sliding window 1024).
    # Native context 256_000; Ollama tag batiai/gemma4-31b:iq3 defaults num_ctx=131_072.
    # IQ3 ~13GB weights / ~24GB VRAM; 131K KV will OOM. Local runs keep 32_768.
    # IQ3 is lossy vs Q4, so MAP/REDUCE budgets stay below dense 32B Q4+ peers.
    # Thinking is disabled at call time (same empty-body failure as R1/Qwen3).
    ModelType.GEMMA4_31B_IQ3: ModelCapabilities(
        model=ModelType.GEMMA4_31B_IQ3,
        provider="ollama",
        context_window=32_768,
        native_max_output_tokens=8_192,
        max_tokens_per_chunk=2_500,
        reduce_batch_tokens=6_000,
        chunk_overlap=256,
        safe_percent=0.05,
        tokenizer="tiktoken",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=5_000,
        reduce_safety_margin=768,
        reduce_min_batch_tokens=250,
        output_padding_tokens=600,
        format_safety_margin=1_500,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=3_500,
        overhead=1_200,
        min_chunk_tokens=80,
        supports_temperature=True,
        default_temperature=1.0,
    ),
    # Qwen3-VL-30B-A3B — MoE vision-language model served via RunAI.
    # Architecture: 30.5B total parameters, 3B active per token (sparse MoE).
    # Native context: 256K; local runs capped at 32K (VRAM: weights + KV).
    # Max output: 32K native; Brevio caps at 16K per the summary output policy.
    # Tokenizer: Qwen family (same byte-pair as Qwen3 text-only series).
    # Temperature: accepted; 0.7 is the Qwen3 series recommended default.
    # Thinking/reasoning: NOT enabled — same empty-body failure as R1/Qwen3.
    # Source: https://huggingface.co/Qwen/Qwen3-VL-30B-A3B
    ModelType.QWEN3_VL_30B_A3B: ModelCapabilities(
        model=ModelType.QWEN3_VL_30B_A3B,
        provider="runai",
        context_window=32_768,
        native_max_output_tokens=32_768,
        max_tokens_per_chunk=3_000,
        reduce_batch_tokens=8_000,
        chunk_overlap=250,
        safe_percent=0.05,
        tokenizer="qwen",
        supports_json=True,
        supports_mermaid=True,
        supports_chunking=True,
        reduce_input_token_budget=6_000,
        reduce_safety_margin=512,
        reduce_min_batch_tokens=250,
        output_padding_tokens=500,
        format_safety_margin=1_500,
        min_tokens_for_postprocess=2_000,
        global_map_safety_cap=4_000,
        overhead=1_000,
        min_chunk_tokens=80,
        output_token_param="max_tokens",
        supports_temperature=True,
        default_temperature=0.7,
        status="stable",
        recommended=True,
    ),
}


# Per-call summary generations above this are unstable (Flash 384k, Gemini 65k).
_SUMMARY_PER_CALL_OUTPUT_CAP = 16_384


def get_model_capabilities(model: ModelType) -> ModelCapabilities:
    if model not in MODEL_CAPABILITIES:
        raise ValueError(f"Model capabilities not configured for model '{model.value}'")
    return MODEL_CAPABILITIES[model]


def summary_max_output_tokens(capabilities: ModelCapabilities) -> int:
    """Hard cap for a single summary completion, not the vendor marketing maximum."""
    return min(int(capabilities.native_max_output_tokens), _SUMMARY_PER_CALL_OUTPUT_CAP)


def generation_temperature(capabilities: ModelCapabilities) -> float:
    """Official vendor sampling temperature for this model.

    Models that reject temperature still return 0.0; callers must omit the field.
    """
    if not capabilities.supports_temperature:
        return 0.0
    if capabilities.default_temperature is None:
        return 1.0
    return float(capabilities.default_temperature)


def generation_parameter_ids(capabilities: ModelCapabilities) -> list[str]:
    """User-facing generation parameter ids. Sampling and token caps are backend-only."""
    if capabilities.reasoning:
        return [capabilities.reasoning]
    return []


def packing_token_multiplier(capabilities: ModelCapabilities) -> float:
    """Inflate counted tokens when the local tokenizer under-counts the runtime.

    Ollama Qwen is typically counted with cl100k (or a cached Qwen tokenizer).
    Spanish/code mixed text is denser in Qwen pieces than cl100k, so packing
    without slack overflowed num_ctx and dropped the system prompt.
    """
    if capabilities.provider == "ollama":
        return 1.20
    return 1.0
