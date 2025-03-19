import logging
import whisper
from os import path
from os.path import exists
from ..constants.constants import Constants
from ..utils.utils import format_time
from ..enums.language import LanguageType
from ..managers.directory_manager import DirectoryManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class TranscriptionService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TranscriptionService, cls).__new__(cls)
            logger.info("Creating new instance of TranscriptionService")
        else:
            logger.debug("Reusing existing instance of TranscriptionService")
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_directory_manager'):
            self._directory_manager = DirectoryManager()
            logger.debug("DirectoryManager initialized")
        self._format_time = format_time

    def _validate_paths(self, audio_path: str, destination_path: str) -> None:
        if not exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        if not exists(destination_path):
            error_msg = f"Destination directory not found: {destination_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

    def generate_transcription(self, audio_path: str, destination_path: str, language: LanguageType) -> str:
        logger.info(f"Starting transcription for {audio_path} in {language.value}")

        self._validate_paths(audio_path, destination_path)

        try:
            logger.debug("Loading Whisper 'small' model")
            model = whisper.load_model("small")
            logger.debug("Whisper model loaded successfully")

            logger.info(f"Transcribing audio: {audio_path}")
            result = model.transcribe(audio_path, language=language.value)
            logger.info("Transcription completed successfully")

            transcription_text = "\n".join(
                f"{self._format_time(segment['start'])} {segment['text']}"
                for segment in result.get("segments", [])
            )

            transcription_path = path.join(destination_path, Constants.TRANSCRIPTION_FILE)
            logger.debug(f"Writing transcription to {transcription_path}")
            with open(transcription_path, "w", encoding="utf-8") as file:
                file.write(transcription_text)
            logger.info(f"Transcription written to {transcription_path}")

            transcription = self._directory_manager.read_transcription(transcription_path)
            logger.debug("Transcription read successfully")
            logger.info(f"Transcription process completed: {transcription_path}")
            return transcription
        
        except RuntimeError as e:
            logger.error(f"Whisper transcription failed: {str(e)}", exc_info=True)
            raise
        except IOError as e:
            logger.error(f"IO error during transcription: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in transcription: {str(e)}", exc_info=True)
            raise