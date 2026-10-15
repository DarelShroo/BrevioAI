from enum import Enum


class ModelType(str, Enum):
    # OpenAI — API IDs from https://platform.openai.com/docs/models
    GPT_4 = "gpt-4"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_5_6 = "gpt-5.6"
    DEEPSEEK_V4_PRO = "deepseek-v4-pro"
    DEEPSEEK_FLASH = "deepseek-flash"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"
    GROK_4_6 = "grok-4.6"
    CLAUDE_SONNET_5 = "claude-sonnet-5"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"

    # Local Models (Ollama)
    QWEN3_8B = "qwen3:8b"
    QWEN3_14B_BASE = "qwen3:14b"
    QWEN3_14B = "qwen3:14b-q6"
    QWEN3_32B = "qwen3:32b"
    DEEPSEEK_R1_LOCAL_IQ3_XS = "deepseek-r1-local:iq3-xs"
    GPT_OSS_20B = "gpt-oss:20b"
    GEMMA4_31B_IQ3 = "batiai/gemma4-31b:iq3"

    # Local Models (RunAI — OpenAI-compatible endpoint)
    # Qwen3-VL-30B-A3B: MoE vision-language, 30.5B total / 3B active.
    # Context: 256K native; local runs capped at 32K (VRAM budget).
    # Model ID matches the GGUF filename served by `runai serve`.
    QWEN3_VL_30B_A3B = "qwen3-vl-30b-a3b"
