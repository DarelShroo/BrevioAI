from enum import Enum


class ModelType(str, Enum):
    # OpenAI Models
    GPT_4 = "gpt-4"
    GPT_4O_MINI = "gpt-4o-mini"
    DEEPSEEK_CHAT = "deepseek-chat"
