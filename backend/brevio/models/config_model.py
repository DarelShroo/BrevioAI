from os import getenv
from typing import Optional

from dotenv import load_dotenv

from brevio.constants.constants import Constants
from brevio.enums import LanguageType, ModelType


class ConfigModel:
    def __init__(
        self,
        url: str = "",
        content: str = "",
        model: Optional[ModelType] = None,
        language: Optional[LanguageType] = None,
    ) -> None:
        self._url = url
        self._language = language
        self._content = content
        self._model = model

        self._transcription_file = Constants.TRANSCRIPTION_FILE
        self._summary_file = Constants.SUMMARY_FILE
        self._all_transcriptions = Constants.ALL_TRANSCRIPTIONS
        self._all_summaries = Constants.ALL_SUMMARIES
        self._dest_folder = Constants.DESTINATION_FOLDER

        load_dotenv()

        self._api_key: str = getenv("OPENAI_API_KEY", "")

        self._max_tokens: int = self._safe_cast_int(getenv("MAX_TOKENS", "4096"))
        self._tokens_per_minute: int = self._safe_cast_int(
            getenv("TOKENS_PER_MINUTE", "200000")
        )
        self._temperature: float = self._safe_cast_float(getenv("TEMPERATURE", "0.2"))

    @staticmethod
    def _safe_cast_int(value: str) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _safe_cast_float(value: str) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def tokens_per_minute(self) -> int:
        return self._tokens_per_minute

    @property
    def model(self) -> Optional[ModelType]:
        return self._model

    @model.setter
    def model(self, value: Optional[ModelType]) -> None:
        self._model = value

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        self._temperature = value

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, value: str) -> None:
        self._content = value

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        self._url = value

    @property
    def language(self) -> Optional[LanguageType]:
        return self._language

    @language.setter
    def language(self, value: Optional[LanguageType]) -> None:
        self._language = value

    @property
    def dest_folder(self) -> str:
        return self._dest_folder

    @property
    def transcription_file(self) -> str:
        return self._transcription_file

    @property
    def summary_file(self) -> str:
        return self._summary_file

    @property
    def all_transcriptions(self) -> str:
        return self._all_transcriptions

    @property
    def all_summaries(self) -> str:
        return self._all_summaries
