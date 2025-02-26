import logging
import whisper
from os import path
from backend.brevio.constants.constants import Constants
from ..constants.transcription_messages import TranscriptionMessages
from ..enums.language import LanguageType
from ..models.response_model import TranscriptionResponse
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
        try:
            logger.info("Loading Whisper model 'tiny'.")
            model = whisper.load_model("tiny")
            print(whisper.available_models())
            logger.info("Whisper model loaded successfully.")

            logger.info(f"Transcribing audio file: {audio_path}.")
            result = model.transcribe(audio_path)
            logger.info("Transcription completed.")

            # Definir la función para formatear el tiempo
            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                seconds = int(seconds % 60)
                return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

            # Construir el texto con timestamps
            segments = result.get("segments", [])
            transcription_text = ""
            for segment in segments:
                start_time = format_time(segment["start"])
                text = segment["text"]
                transcription_text += f"{start_time} {text}\n"

            transcription_path = path.join(destination_path, Constants.TRANSCRIPTION_FILE)
            logger.info(f"Writing transcription to file: {transcription_path}.")

            with open(transcription_path, "w", encoding="utf-8") as file:
                file.write(transcription_text)
            logger.info("Transcription file written successfully.")

            transcription = self._directory_manager.read_transcription(transcription_path)
            logger.info("Transcription read successfully from file.")

            response_message = TranscriptionMessages.SUCCESS_TRANSCRIPTION_FILE_GENERATED.format(transcription_path)
            logger.info(f"Transcription process completed successfully. {response_message}")
            return TranscriptionResponse(
                True,
                str(transcription),
                response_message
            )
        except Exception as e:
            logger.error(f"Error during transcription process: {e}", exc_info=True)
            return TranscriptionResponse(
                False,
                "",
                f"Error inesperado: {e}"
            )