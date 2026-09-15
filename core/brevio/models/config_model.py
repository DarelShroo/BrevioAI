from typing import Optional

from dotenv import load_dotenv

from core.brevio.constants.constants import Constants
from core.brevio.enums.language import LanguageType
from core.shared.enums.model import ModelType
from core.shared.utils.environment import max_tokens_fallback, tokens_per_minute
from core.shared.utils.model_capabilities import (
    generation_temperature,
    get_model_capabilities,
)


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

        self._max_tokens: int = max_tokens_fallback()
        self._tokens_per_minute: int = tokens_per_minute()
        self._temperature: float = 1.0

    @property
    def max_tokens(self) -> int:
        if self._model:
            from core.shared.utils.model_capabilities import get_model_capabilities

            try:
                return get_model_capabilities(self._model).native_max_output_tokens
            except ValueError:
                pass
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
        if self._model:
            try:
                return generation_temperature(get_model_capabilities(self._model))
            except ValueError:
                pass
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
