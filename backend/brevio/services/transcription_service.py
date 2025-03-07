import logging
import whisper
from os import path
from os.path import exists
from backend.brevio.constants.constants import Constants
from ..constants.transcription_messages import TranscriptionMessages
from ..enums.language import LanguageType
from ..managers.directory_manager import DirectoryManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class TranscriptionService:
    _instance = None 
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TranscriptionService, cls).__new__(cls)
            logger.info("Creating new instance of TranscriptionService.")
        else:
            logger.info("Using existing instance of TranscriptionService.")
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_directory_manager'):
            self._directory_manager = DirectoryManager()
            logger.info("DirectoryManager initialized.")

    def generate_transcription(self, audio_path, destination_path, language: LanguageType):
        logger.info(f"Starting transcription process for audio file: {audio_path} with language: {language.value}.")
        
        if not exists(audio_path):
            error_message = f"Audio file not found at the path: {audio_path}"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        if not exists(destination_path):
            error_message = f"Destination path does not exist: {destination_path}"
            logger.error(error_message)
            raise FileNotFoundError(error_message)

        try:
            logger.info("Loading Whisper model 'tiny'.")
            model = whisper.load_model("tiny")
            logger.info("Whisper model loaded successfully.")

            logger.info(f"Transcribing audio file: {audio_path}.")
            result = model.transcribe(audio_path)
            logger.info("Transcription completed.")

            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                seconds = int(seconds % 60)
                return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

            segments = result.get("segments", [])
            transcription_text = ""
            for segment in segments:
                start_time = format_time(segment["start"])
                text = segment["text"]
                transcription_text += f"{start_time} {text}\n"

            transcription_path = path.join(destination_path, Constants.TRANSCRIPTION_FILE)
            logger.info(f"Writing transcription to file: {transcription_path}.")

            try:
                with open(transcription_path, "w", encoding="utf-8") as file:
                    file.write(transcription_text)
                logger.info("Transcription file written successfully.")
            except Exception as e:
                logger.error(f"Error writing transcription file: {e}", exc_info=True)
                raise IOError(f"Error al escribir el archivo de transcripción: {e}")

            transcription = self._directory_manager.read_transcription(transcription_path)
            logger.info("Transcription read successfully from file.")

            response_message = TranscriptionMessages.SUCCESS_TRANSCRIPTION_FILE_GENERATED.format(transcription_path)
            logger.info(f"Transcription process completed successfully. {response_message}")
            return transcription
        except whisper.exceptions.WhisperError as e:
            logger.error(f"Whisper error during transcription: {e}", exc_info=True)
            raise Exception(f"Error al transcribir con Whisper: {e}")
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}", exc_info=True)
            raise FileNotFoundError(f"Archivo no encontrado: {e}")
        except PermissionError as e:
            logger.error(f"Permission error: {e}", exc_info=True)
            raise PermissionError(f"Error de permisos: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during transcription process: {e}", exc_info=True)
            raise Exception(f"Error inesperado: {e}")
