import sys
import os
from typing import Dict, List
from backend.brevio.enums.content import ContentType
from backend.models.brevio.brevio_generate import BrevioGenerate
from .models.config_model import ConfigModel as Config
from .generate import Generate
from .enums.model import ModelType
from .enums.language import LanguageType
from .constants.type_messages import TypeMessages
from .services.yt_service import YTService

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class Main:
    def __init__(self, argv = None):
        self.argv = argv

    async def count_media_in_yt_playlist(self, url: str):
        return await YTService().count_media_in_yt_playlist(url)

    async def get_media_duration(self, url: str):
        return await YTService().get_media_duration(url)

    @staticmethod
    def get_languages():
        return [key for key, member in LanguageType.__members__.items()]

    @staticmethod
    def get_models():
        return [key for key, member in ModelType.__members__.items()]

    async def generate(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, user_id: str) -> Dict:
        generate = Generate()
        return await generate._process_online_audio_data(data, _create_data_result, current_folder_entry_id, _user_folder_id, user_id)

    async def generate_pdf_summary(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, user_id: str) -> Dict:
        generate = Generate()
        return await generate._process_pdf(data, _create_data_result, current_folder_entry_id, _user_folder_id, user_id)

    async def generate_docx_summary(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, user_id: str) -> Dict:
        generate = Generate()
        return await generate._process_docx(data, _create_data_result, current_folder_entry_id, _user_folder_id, user_id)

    def run(self):
        """Main entry point for the script."""
        self.parse_arguments()
        return self.organize_audio_files()


if __name__ == "__main__":
    main_app = Main(sys.argv[1:])
    result = main_app.run()
    print(result)
