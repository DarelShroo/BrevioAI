import sys
import os
from typing import Dict, List
from backend.brevio.services.advanced_content_generator import AdvancedContentGenerator
from backend.models.brevio.brevio_generate import BrevioGenerate
from .generate import Generate
from .enums.model import ModelType
from .enums.language import LanguageType
from .services.yt_service import YTService

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class Main:
    def __init__(self, argv=None):
        self.argv = argv
        self._generate = Generate()
        self._yt_service = YTService()

    async def count_media_in_yt_playlist(self, url: str):
        try:
            return await self._yt_service.count_media_in_yt_playlist(url)
        except Exception as e:
            print(f"Error al contar los medios en la lista de reproducción de YouTube: {str(e)}")
            return {"error": f"Error al contar los medios: {str(e)}"}

    async def get_media_duration(self, url: str):
        try:
            return await self._yt_service.get_media_duration(url)
        except Exception as e:
            print(f"Error al obtener la duración del medio de YouTube: {str(e)}")
            return {"error": f"Error al obtener la duración: {str(e)}"}

    @staticmethod
    def get_languages():
        try:
            return [key for key, member in LanguageType.__members__.items()]
        except Exception as e:
            print(f"Error al obtener los idiomas: {str(e)}")
            return {"error": f"Error al obtener los idiomas: {str(e)}"}

    @staticmethod
    def get_models():
        try:
            return [key for key, member in ModelType.__members__.items()]
        except Exception as e:
            print(f"Error al obtener los modelos: {str(e)}")
            return {"error": f"Error al obtener los modelos: {str(e)}"}

    @staticmethod
    def get_all_category_style_combinations():
        try:
            acg = AdvancedContentGenerator()
            combinations = acg.get_all_category_style_combinations()
            dic_combinations: Dict[str, List] = {}

            for category, style in combinations:
                if category not in dic_combinations:
                    dic_combinations[category] = []
                dic_combinations[category].append(style)

            return dic_combinations
        except Exception as e:
            print(f"Error al obtener combinaciones de categoría y estilo: {str(e)}")
            return {"error": f"Error al obtener combinaciones: {str(e)}"}

    async def generate(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, user_id: str) -> Dict:
        try:
            return await self._generate._process_online_audio_data(data, _create_data_result, current_folder_entry_id, _user_folder_id, user_id)
        except Exception as e:
            print(f"Error al generar datos de audio: {str(e)}")
            return {"error": f"Error al generar datos: {str(e)}"}

    async def generate_summary_documents(self, _data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, user_id: str) -> Dict:
        try:
            return await self._generate._process_documents(_data, _create_data_result, current_folder_entry_id, _user_folder_id, user_id)
        except Exception as e:
            print(f"Error al generar documentos de resumen: {str(e)}")
            return {"error": f"Error al generar resumen: {str(e)}"}