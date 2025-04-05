import asyncio
import logging
import os
from os.path import exists, join
from typing import Any, Optional, Type

import whisper

from backend.brevio.constants.constants import Constants
from backend.brevio.enums.language import LanguageType
from backend.brevio.utils.utils import format_time


class TranscriptionService:
    _instance: Optional["TranscriptionService"] = None
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
        if not hasattr(self, "_directory_manager"):
            from ..managers.directory_manager import DirectoryManager

            self._directory_manager = DirectoryManager()
            self.logger.debug("DirectoryManager initialized")

    def _validate_paths(self, audio_path: str, destination_path: str) -> None:
        """Validate that audio file and destination directory exist."""
        if not exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        if not exists(destination_path):
            error_msg = f"Destination directory not found: {destination_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

    def _write_transcription(self, path: str, content: str) -> None:
        """Write transcription content to file."""
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

            model = whisper.load_model("small")
            self.logger.debug("Whisper model loaded successfully")

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(audio_path)
            )
            self.logger.info("Transcription completed successfully")

            # Handle case when no segments are returned
            if not result.get("segments"):
                self.logger.info("No segments found in transcription result")
                transcription_text = ""
            else:
                transcription_text = "\n".join(
                    f"{format_time(segment['start'])} {segment['text']}"
                    for segment in result["segments"]
                )

            transcription_path = os.path.join(
                destination_path, Constants.TRANSCRIPTION_FILE
            )
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
