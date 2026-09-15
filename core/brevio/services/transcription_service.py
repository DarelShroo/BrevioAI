from __future__ import annotations

import asyncio
import logging
import os
from os.path import exists
from typing import Any, Optional, Type

from core.brevio.constants.constants import Constants
from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.media_preprocessor import MediaPreprocessor, PreparedAudio
from core.brevio.services.transcription.access_policy import TranscriptionAccessPolicy
from core.brevio.services.transcription.catalog import (
    resolve_media_provider,
    resolve_transcription_model,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.formatting import format_transcription
from core.brevio.services.transcription.google_provider import (
    GoogleTranscriptionProvider,
)
from core.brevio.services.transcription.local_whisper_provider import (
    LocalWhisperTranscriptionProvider,
)
from core.brevio.services.transcription.openai_provider import (
    OpenAITranscriptionProvider,
)
from core.brevio.services.transcription.provider import TranscriptionProvider
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio.services.transcription.xai_provider import XAITranscriptionProvider
from core.brevio_api.models.errors.api_codes import ApiErrorCode


def _nonempty_file(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TranscriptionService:
    _instance: Optional["TranscriptionService"] = None
    _directory_manager_initialized: bool = False
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

    def __init__(
        self,
        credential_resolver: Any = None,
        preprocessor: Optional[MediaPreprocessor] = None,
        access_policy: Optional[TranscriptionAccessPolicy] = None,
    ) -> None:
        if credential_resolver is not None:
            self._credential_resolver = credential_resolver
        elif not hasattr(self, "_credential_resolver"):
            self._credential_resolver = None
        if preprocessor is not None:
            self._preprocessor = preprocessor
        elif not hasattr(self, "_preprocessor"):
            self._preprocessor = MediaPreprocessor()
        if access_policy is not None:
            self._access_policy = access_policy
        elif not hasattr(self, "_access_policy"):
            self._access_policy = TranscriptionAccessPolicy()
        if not self._directory_manager_initialized:
            from ..managers.directory_manager import DirectoryManager

            self._directory_manager = DirectoryManager()
            self._directory_manager_initialized = True
            self.logger.debug("DirectoryManager initialized")

    def set_credential_resolver(self, credential_resolver: Any) -> None:
        self._credential_resolver = credential_resolver

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

    def _provider_for(
        self, provider: TranscriptionProviderType
    ) -> TranscriptionProvider:
        if provider is TranscriptionProviderType.LOCAL_WHISPER:
            return LocalWhisperTranscriptionProvider()
        if provider is TranscriptionProviderType.OPENAI:
            return OpenAITranscriptionProvider(self._credential_resolver)
        if provider is TranscriptionProviderType.GOOGLE:
            return GoogleTranscriptionProvider(self._credential_resolver)
        if provider is TranscriptionProviderType.XAI:
            return XAITranscriptionProvider(self._credential_resolver)
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_UNKNOWN)

    async def generate_transcription(
        self,
        audio_path: str,
        destination_path: str,
        language: LanguageType,
        provider: Optional[str | TranscriptionProviderType] = None,
        user_id: Optional[str] = None,
        enforce_user_access: bool = True,
        skip_if_exists: bool = True,
        model: Optional[str] = None,
    ) -> str:
        transcription_path = os.path.join(
            destination_path, Constants.TRANSCRIPTION_FILE
        )
        try:
            self.logger.info(
                "Starting transcription for %s in %s",
                audio_path,
                language.value,
            )
            self._validate_paths(audio_path, destination_path)
            if skip_if_exists and await asyncio.to_thread(
                _nonempty_file, transcription_path
            ):
                self.logger.info(
                    "Reusing existing transcription at %s", transcription_path
                )
                return await asyncio.to_thread(_read_text, transcription_path)

            selected = resolve_media_provider(
                provider.value
                if isinstance(provider, TranscriptionProviderType)
                else provider,
                policy=self._access_policy,
                enforce_user_access=enforce_user_access,
            )
            selected_model = resolve_transcription_model(selected, model)
            engine = self._provider_for(selected)
            prepared: Optional[PreparedAudio] = None
            try:
                prepared = await self._preprocessor.prepare(
                    audio_path, destination_path, selected
                )
                result = await engine.transcribe(
                    prepared.path,
                    language,
                    user_id=user_id,
                    model=selected_model.vendor_model_id or selected_model.id,
                )
            finally:
                if prepared is not None:
                    await self._preprocessor.cleanup(prepared)

            transcription_text = format_transcription(result)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._write_transcription(
                    transcription_path, transcription_text
                ),
            )
            self.logger.info("Transcription completed successfully")
            return transcription_text
        except TranscriptionError:
            raise
        except FileNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error in transcription: %s",
                redact_secrets(str(e)),
            )
            raise
