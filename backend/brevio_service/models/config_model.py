from ..constants.constants import Constants 
from ..constants.type_messages import TypeMessages
from ..random_name import generate_random_name
from ..enums.language import LanguageType
from ..enums.model import ModelType
from dotenv import load_dotenv
from os import path, getenv

class ConfigModel:
    def __init__(self, url: str, content: str, model: ModelType, language: LanguageType):
        self._url = url
        self._language = language
        self._dest_folder = path.join(".", Constants.DESTINATION_FOLDER, generate_random_name())
        self._transcription_file = Constants.TRANSCRIPTION_FILE
        self._summary_file = Constants.SUMMARY_FILE
        self._all_transcriptions = Constants.ALL_TRANSCRIPTIONS
        self._all_summaries = Constants.ALL_SUMMARIES
        self._content = content
        self._model = model

        load_dotenv()

        self._api_key: str = getenv("OPENAI_API_KEY")
        self._max_tokens: int = getenv("MAX_TOKENS")
        self._tokens_per_minute: int = getenv("TOKENS_PER_MINUTE")
        self._temperature: float = getenv("TEMPERATURE")

    @property
    def api_key(self):
        return self._api_key

    @property
    def max_tokens(self):
        return self._max_tokens

    @property
    def tokens_per_minute(self):
        return self._tokens_per_minute
    
    @property
    def model(self):
        return self._model
    
    @model.setter
    def model(self, value):
        self._model = value

    @property
    def temperature(self):
        return self._temperature
    
    @temperature.setter
    def temperature(self, value):
        self._temperature = value


    @property
    def model(self):
        return self._model
    
    @model.setter
    def model(self, value):
        self._model = value

    @property
    def content(self):
        return self._content
    
    @content.setter
    def content(self, value):
        self._content = value

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        self._language = value

    @property
    def dest_folder(self):
        return self._dest_folder

    @property
    def transcription_file(self):
        return self._transcription_file

    @property
    def summary_file(self):
        return self._summary_file

    @property
    def all_transcriptions(self):
        return self._all_transcriptions

    @property
    def all_summaries(self):
        return self._all_summaries

