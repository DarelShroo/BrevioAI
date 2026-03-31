import asyncio
import logging
import os
from os.path import exists, join
from typing import Any, Optional, Type

from dotenv import load_dotenv
from openai import AsyncOpenAI
import whisper

from core.brevio.constants.constants import Constants
from core.brevio.enums.language import LanguageType
from core.brevio.utils.utils import format_time

load_dotenv()


class TranscriptionService:
    _instance: Optional["TranscriptionService"] = None
    _directory_manager_initialized: bool = (
        False  # Track DirectoryManager initialization
    )
    logger: logging.Logger

    def __new__(
        cls: Type["TranscriptionService"], *args: Any, **kwargs: Any
    ) -> "TranscriptionService":
        if not cls._instance:
            cls._instance = super(TranscriptionService, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(__name__)
            cls._instance.logger.setLevel(logging.DEBUG)
            if not cls._instance.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "%(asctime)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                cls._instance.logger.addHandler(handler)
            cls._instance.logger.info("Creating new instance of TranscriptionService")
        else:
            cls._instance.logger.info(
                "Reusing existing instance of TranscriptionService"
            )
        return cls._instance

    def __init__(self) -> None:
        if not self._directory_manager_initialized:
            from ..managers.directory_manager import DirectoryManager

            self._directory_manager = DirectoryManager()
            self._directory_manager_initialized = True
            self.logger.debug("DirectoryManager initialized")

        raw_environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        if raw_environment not in {"development", "production"}:
            self.logger.warning(
                "Invalid ENVIRONMENT='%s'. Falling back to 'development'.",
                raw_environment,
            )
            raw_environment = "development"

        self._environment = raw_environment
        self._openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self._openai_api_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")
        self._openai_transcription_model = os.getenv(
            "OPENAI_TRANSCRIPTION_MODEL", "whisper-1"
        )
        self.logger.info("Transcription environment set to '%s'", self._environment)

    def _is_production(self) -> bool:
        return self._environment == "production"

    def _build_transcription_text(self, result: Any) -> str:
        segments_data: list[tuple[float, str]] = []
        fallback_text = ""

        if isinstance(result, dict):
            fallback_text = str(result.get("text", "")).strip()
            raw_segments = result.get("segments") or []
            for segment in raw_segments:
                if not isinstance(segment, dict):
                    continue
                text = str(segment.get("text", "")).strip()
                start = float(segment.get("start", 0.0))
                if text:
                    segments_data.append((start, text))
        else:
            fallback_text = str(getattr(result, "text", "")).strip()
            raw_segments = getattr(result, "segments", None) or []
            for segment in raw_segments:
                text = str(getattr(segment, "text", "")).strip()
                start = float(getattr(segment, "start", 0.0))
                if text:
                    segments_data.append((start, text))

        if segments_data:
            return "\n".join(
                f"{format_time(start)} {text}" for start, text in segments_data
            )

        return fallback_text

    async def _transcribe_local(self, audio_path: str) -> Any:
        model = whisper.load_model("small")
        self.logger.debug("Whisper model loaded successfully")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: model.transcribe(audio_path))
        self.logger.info("Local transcription completed successfully")
        return result

    async def _transcribe_remote(self, audio_path: str, language: LanguageType) -> Any:
        if not self._openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when ENVIRONMENT=production"
            )

        client = AsyncOpenAI(api_key=self._openai_api_key, base_url=self._openai_api_url)
        self.logger.debug(
            "Using remote OpenAI transcription with model '%s'",
            self._openai_transcription_model,
        )

        try:
            with open(audio_path, "rb") as audio_file:
                result = await client.audio.transcriptions.create(
                    model=self._openai_transcription_model,
                    file=audio_file,
                    language=language.value,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            self.logger.info("Remote transcription completed successfully")
            return result
        finally:
            await client.close()

    def _validate_paths(self, audio_path: str, destination_path: str) -> None:
        if not exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        if not exists(destination_path):
            error_msg = f"Destination directory not found: {destination_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

    def _write_transcription(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    async def generate_transcription(
        self,
        audio_path: str,
        destination_path: str,
        language: LanguageType,
    ) -> str:
        try:
            self.logger.info(
                f"Starting transcription for {audio_path} in {language.value}"
            )
            self._validate_paths(audio_path, destination_path)

            if self._is_production():
                self.logger.info(
                    "ENVIRONMENT=production detected, using remote OpenAI transcription"
                )
                result = await self._transcribe_remote(audio_path, language)
            else:
                self.logger.info(
                    "ENVIRONMENT=development detected, using local Whisper transcription"
                )
                result = await self._transcribe_local(audio_path)

            transcription_text = self._build_transcription_text(result)
            raw_segments = (
                result.get("segments")
                if isinstance(result, dict)
                else getattr(result, "segments", None)
            )
            if raw_segments is not None and len(raw_segments) == 0:
                self.logger.info("No segments found in transcription result")
            if not transcription_text.strip():
                self.logger.info("No transcription text generated from result")

            transcription_path = os.path.join(
                destination_path, Constants.TRANSCRIPTION_FILE
            )
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._write_transcription(
                    transcription_path, transcription_text
                ),
            )

            return transcription_text
        except Exception as e:
            self.logger.error(f"Unexpected error in transcription: {str(e)}")
            raise
