import subprocess
from os import path, rename

from ..constants.transcription_messages import TranscriptionMessages
from ..enums.extension import ExtensionType
from ..enums.language import LanguageType
from ..models.response_model import TranscriptionResponse
from ..managers.directory_manager import DirectoryManager
from ..models.config_model import ConfigModel as Config
class Transcription:
    def __init__(self, audio_path, language: LanguageType, destination_path, transcription_file, config: Config):
        self._audio_path = audio_path
        self._language = str(language.value)
        self._destination_path = destination_path
        self._transcription_file = transcription_file
        self.config = config
    
    def generateTranscription(self):
        command = [
            "whisper", self._audio_path, 
            "--language", self._language, 
            "--output_format", str(ExtensionType.TXT.value), 
            "--output_dir", self._destination_path 
        ]
        
        try:
            subprocess.run(command, check=True)
            
            generated_file = path.join(self._destination_path, f"{path.basename(self._audio_path)[:-4]}.{str(ExtensionType.TXT.value)}")
            
            transcription_path = path.join(self._destination_path, self._transcription_file)
            transcription = DirectoryManager(self.config).read_transcription(transcription_path)


            if path.exists(generated_file):
                rename(generated_file, transcription_path)
                transcription = DirectoryManager(self.config).read_transcription(transcription_path)
                return TranscriptionResponse(
                    True, 
                    str(transcription), 
                    str(TranscriptionMessages.SUCCESS_TRANSCRIPTION_FILE_GENERATED.format(transcription_path))
                    )
            else:
                return TranscriptionResponse(
                    False, 
                    "", 
                    TranscriptionMessages.ERROR_TRANSCRIPTION_FILE_NOT_FOUND.format(generated_file)
                )

        except subprocess.CalledProcessError as e:
            print(e)
            return TranscriptionResponse(
                    False, 
                    "", 
                    TranscriptionMessages.ERROR_ON_EXECUTING_WHISPER.format(e)
                )

        except Exception as e:
            print(e)

            return TranscriptionResponse(
                    False, 
                    "", 
                    "Error inesperado: {e}"
                )
            
