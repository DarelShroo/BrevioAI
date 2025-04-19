import json
from typing import Dict, List, Union

from core.brevio.enums.language import LanguageType
from core.brevio.enums.model import ModelType
from core.brevio.models.base_model import BaseModel


class SummaryResponse:
    def __init__(
        self,
        success: bool,
        summary: str = "",
        message: str = "",
        error_message: str = "",
    ) -> None:
        self.success: bool = success
        self.summary: str = summary
        self.message: str = message
        self.error_message: str = error_message

    def to_dict(self) -> Dict[str, Union[bool, str]]:
        response: Dict[str, Union[bool, str]] = {
            "success": self.success,
            "summary": self.summary,
            "message": self.message,
        }
        if self.error_message:
            response["error_message"] = self.error_message
        return response

    def __str__(self) -> str:
        return f"SummaryResponse(success={self.success}, summary={self.summary}, message={self.message}, error_message={self.error_message})"


class TranscriptionResponse:
    def __init__(
        self,
        success: bool,
        transcription: str = "",
        message: str = "",
        error_message: str = "",
    ) -> None:
        self.success: bool = success
        self.transcription: str = transcription
        self.message: str = message
        self.error_message: str = error_message

    def to_dict(self) -> Dict[str, Union[bool, str]]:
        response: Dict[str, Union[bool, str]] = {
            "success": self.success,
            "transcription": self.transcription,
            "message": self.message,
        }
        if self.error_message:
            response["error_message"] = self.error_message
        return response

    def __str__(self) -> str:
        return f"TranscriptionResponse(success={self.success}, transcription={self.transcription}, message={self.message}, error_message={self.error_message})"


class DownloadResponse:
    def __init__(self, success: bool, message: str) -> None:
        self.success: bool = success
        self.message: str = message

    def to_dict(self) -> Dict[str, Union[bool, str]]:
        return {"success": self.success, "message": self.message}

    def __str__(self) -> str:
        return f"DownloadResponse(success={self.success}, message={self.message})"


class FolderResponse(BaseModel):
    success: bool
    message: str

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Union[bool, str]]:
        return {"success": self.success, "message": self.message}

    def __str__(self) -> str:
        return f"FolderResponse(success={self.success}, message={self.message})"


class GenerateResponse:
    def __init__(
        self,
        folder_response: FolderResponse,
        download_response: DownloadResponse,
        transcription_response: Union[
            TranscriptionResponse, List[TranscriptionResponse]
        ],
        summary_response: Union[SummaryResponse, List[SummaryResponse]],
        error_message: str = "",
    ) -> None:
        self.folder_response: FolderResponse = folder_response
        self.download_response: DownloadResponse = download_response
        self.transcription_response: List[TranscriptionResponse] = (
            transcription_response
            if isinstance(transcription_response, list)
            else [transcription_response]
        )
        self.summary_response: List[SummaryResponse] = (
            summary_response
            if isinstance(summary_response, list)
            else [summary_response]
        )
        self.error_message: str = error_message

    def to_dict(self) -> Dict[str, Union[List[Dict[str, Union[bool, str]]], str]]:
        response: Dict[str, Union[List[Dict[str, Union[bool, str]]], str]] = {
            "download_result": [
                self.download_response.to_dict()
            ],  # Envuelto en una lista
            "transcription_result": [
                tr.to_dict() for tr in self.transcription_response
            ],
            "summary_result": [sr.to_dict() for sr in self.summary_response],
        }
        if self.error_message:
            response["error_message"] = self.error_message
        return response

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=4)


class LanguageResponse:
    def __init__(self) -> None:
        self.response: Dict[str, str] = {
            language.name: language.value for language in LanguageType
        }

    def get_languages(self) -> Dict[str, str]:
        return self.response

    def __str__(self) -> str:
        return json.dumps(self.response, indent=4)


class ModelResponse:
    def __init__(self) -> None:
        self.response: Dict[str, str] = {model.name: model.value for model in ModelType}

    def get_models(self) -> Dict[str, str]:
        return self.response

    def __str__(self) -> str:
        return json.dumps(self.response, indent=4)
