import json

class SummaryResponse:
    def __init__(self, success: bool, summary: str = "", message: str = "", error_message: str = None):
        self.success = success
        self.summary = summary
        self.message = message
        self.error_message = error_message

    def to_dict(self):
        response = {
            "success": self.success,
            "summary": self.summary,
            "message": self.message
        }
        if self.error_message:
            response["error_message"] = self.error_message
        return response

    def __str__(self):
        return f"SummaryResponse(success={self.success}, summary={self.summary}, message={self.message}, error_message={self.error_message})"


class TranscriptionResponse:
    def __init__(self, success: bool, transcription: str = "", message: str = "", error_message: str = None):
        self.success = success
        self.transcription = transcription
        self.message = message
        self.error_message = error_message 


    def to_dict(self):
        response = {
            "success": self.success,
            "transcription": str(self.transcription),
            "message": self.message
        }
        if self.error_message:
            response["error_message"] = self.error_message 
        return response

    def __str__(self):
        return f"TranscriptionResponse(success={self.success}, transcription={str(self.transcription)}, message={self.message}, error_message={self.error_message})"

class DownloadResponse:
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message

    def to_dict(self):
        return {"success": self.success, "message": self.message}

    def __str__(self):
        return f"DownloadResponse(success={self.success}, message={self.message})"


class FolderResponse:
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message

    def to_dict(self):
        return {"success": self.success, "message": self.message}

    def __str__(self):
        return f"FolderResponse(success={self.success}, message={self.message})"


class GenerateResponse:
    def __init__(self, folder_response, download_response, transcription_response, summary_response, error_message=None):
        self.folder_response = folder_response
        self.download_response = download_response
        self.transcription_response = transcription_response if isinstance(transcription_response, list) else [transcription_response]
        self.summary_response = summary_response if isinstance(summary_response, list) else [summary_response]
        self.error_message = error_message 

    def to_dict(self):

        response = {
            "download_result": self.download_response,
            "transcription_result": self.transcription_response,
            "summary_result": self.summary_response
        }
        
        if self.error_message:
            response["error_message"] = self.error_message
        return response
    
    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


from ..enums.language import LanguageType
from typing import List, Dict
class LanguageResponse:
    def __str__(self):
        response: Dict[str, str] = {language.name: language.value for language in LanguageType}
        return json.dumps(response,indent=4)
    
from ..enums.model import ModelType
class ModelResponse:
    def __str__(self):
        response: Dict[str, str] = {model.name: model.value for model in ModelType}
        return json.dumps(response,indent=4)