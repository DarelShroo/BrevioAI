from os import rename, path, listdir
from .constants.constants import Constants
from .constants.download_messages import DownloadMessages
from .constants.directory_messages import DirectoryMessages
from .constants.transcription_messages import TranscriptionMessages
from .enums.extension import ExtensionType
from .services.transcription_service import Transcription
from .services.summary_service import Summary
from .enums.model import ModelType
from .services.download_service import Download as AudioDownload
from .managers.directory_manager import DirectoryManager
from .models.config_model import ConfigModel as Config
from .models.response_model import SummaryResponse, GenerateResponse, TranscriptionResponse

class Generate:
    def __init__(self, config: Config):
        self._config = config
        self.directory_manager = DirectoryManager(config)

    def organize_audio_files_into_folders(self):
        folder_response = None
        download_response = None
        transcriptions_response = []
        summaries_response = []

        try:
            folder_response = self.create_folder()

            download_response = self.download()

            if path.exists(self._config.dest_folder):
                audio_files = [f for f in listdir(self._config.dest_folder) if path.isfile(path.join(self._config.dest_folder, f)) and f.lower().endswith(f".{str(ExtensionType.MP3.value)}")]
                audio_files.sort()
                count = 1

                for audio_file in audio_files:
                    source_path = path.join(self._config.dest_folder, audio_file)
                    destination_path = path.join(self._config.dest_folder, str(count))
                    transcription_path = path.join(destination_path, self._config.transcription_file)
                    summary_path = path.join(destination_path, self._config.summary_file)
                    audio_path = path.join(destination_path, audio_file)
                    destination_audio_path = path.join(destination_path, audio_file)

                    self.directory_manager.createFolder(destination_path)
                    
                    if not path.exists(destination_audio_path):
                        rename(source_path, destination_audio_path)

                    transcription_response = self.transcription(audio_path, self._config.language, destination_path, self._config.transcription_file, self._config)
                    transcriptions_response.append(transcription_response)

                    self.directory_manager.deleteFile(audio_path)

                    summary_response = self.summary(transcription_path, summary_path, Constants.CONTENT, self._config)
                    summaries_response.append(summary_response)

                    count += 1

            return GenerateResponse(
                folder_response=folder_response,
                download_response=download_response,
                transcription_response=[str(t) for t in transcriptions_response if t is not None],
                summary_response=[str(s) for s in summaries_response if s is not None]
            )

        except Exception as e:
            return GenerateResponse(
                folder_response=folder_response,
                download_response=download_response,
                transcription_response=transcriptions_response,
                summary_response=summaries_response,
                error_message=str(e)
            )
        #finally:
            #self.directory_manager.deleteFolder()

    def create_folder(self):
        if not path.exists(self._config.dest_folder):
            self.directory_manager.createFolder()
        return self.directory_manager.createFolder()

    def download(self):
        _download = AudioDownload(self._config.url, self._config.dest_folder)
        return _download.download()

    def transcription(self, audio_path, language, destination_path, transcription_file, config: Config):
        try:
            return str(Transcription(audio_path, language, destination_path, transcription_file, config).generateTranscription())
        except Exception as e:
            return TranscriptionResponse(success=False, error_message=str(e))

    def summary(self,transcription_path, summary_path, content, config: Config):
        try:
            return str(Summary(transcription_path, summary_path, content, config).generate_summary())
        except Exception as e:
            return SummaryResponse(success=False, error_message=str(e))
