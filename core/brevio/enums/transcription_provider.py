from enum import Enum


class TranscriptionProviderType(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    XAI = "xai"
    LOCAL_WHISPER = "local_whisper"
