import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from bson import ObjectId
from fastapi.exceptions import HTTPException
from pydantic import HttpUrl

from core.brevio.enums import LanguageType, ModelType, SourceType
from core.brevio.services.advanced_content_generator import AdvancedContentGenerator

from .generate import Generate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Main:
    def __init__(self, argv: Optional[List[str]] = None) -> None:
        self.argv = argv
        try:
            self._generate = Generate()
            from .services.yt_service import YTService

            self._yt_service = YTService()
        except Exception as e:
            logger.error(f"Failed to initialize Main class: {str(e)}", exc_info=True)
            raise RuntimeError(f"Initialization failed: {str(e)}")

    async def count_media_in_yt_playlist(self, url: HttpUrl) -> int:
        try:
            result: int = await self._yt_service.count_media_in_yt_playlist(url)
            logger.debug(f"Successfully counted media in playlist: {url}")
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error counting media in playlist {url}: {str(e)}",
                exc_info=True,
            )
            raise Exception(f"Unexpected error counting media: {str(e)}")

    async def get_media_duration(self, url: HttpUrl) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = await self._yt_service.get_media_duration(url)
            logger.debug(f"Successfully got duration for media: {url}")
            return result
        except ValueError as e:
            logger.error(f"Invalid URL format for media {url}: {str(e)}")
            raise ValueError(f"Invalid media URL: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error getting duration for {url}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail=f"Unexpected error getting duration"
            )

    @staticmethod
    def get_languages() -> List[str]:
        try:
            languages = [language.name for language in LanguageType]

            print(languages)
            logger.debug(f"Retrieved {len(languages)} languages")
            return languages
        except Exception as e:
            logger.error(f"Unexpected error getting languages: {str(e)}", exc_info=True)
            raise Exception(f"Unexpected error getting languages: {str(e)}")

    @staticmethod
    def get_models() -> List[str]:
        try:
            models = [key for key, member in ModelType.__members__.items()]
            logger.debug(f"Retrieved {len(models)} models")
            return models
        except Exception as e:
            logger.error(f"Unexpected error getting models: {str(e)}", exc_info=True)
            raise Exception(f"Unexpected error getting models: {str(e)}")

    @staticmethod
    def get_all_category_style_combinations() -> (
        Dict[str, List[Dict[str, Union[str, List[str]]]]]
    ):
        try:
            acg = AdvancedContentGenerator()
            # Type hint reflects that source_types is a list of strings
            combinations: List[
                Tuple[str, str, List[str]]
            ] = acg.get_all_category_style_combinations()

            logger.debug(f"Combinations fetched: {combinations}")

            dic_combinations: Dict[str, List[Dict[str, Union[str, List[str]]]]] = {}

            for category, style, source_types in combinations:
                dic_combinations.setdefault(category, []).append(
                    {"style": style, "source_types": source_types}
                )

            return dic_combinations

        except Exception as e:
            logger.error(
                f"Unexpected error getting combinations: {str(e)}", exc_info=True
            )
            raise HTTPException(500, f"Unexpected error getting combinations")

    async def generate(
        self,
        data: Any,
        _create_data_result: Any,
        current_folder_entry_id: ObjectId,
        _user_folder_id: ObjectId,
        user_id: ObjectId,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = await self._generate._process_online_audio_data(
                data,
                _create_data_result,
                current_folder_entry_id,
                _user_folder_id,
                user_id,
            )
            logger.debug(f"Successfully generated audio data for user {user_id}")
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error generating audio data: {str(e)}", exc_info=True
            )
            raise Exception(f"Unexpected error generating data: {str(e)}")

    async def generate_summary_documents(
        self,
        _data: Any,
        current_folder_entry_id: ObjectId,
        _user_folder_id: ObjectId,
        user_id: ObjectId,
        _create_data_result: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = await self._generate._process_documents(
                _data,
                current_folder_entry_id,
                _user_folder_id,
                user_id,
                _create_data_result,
            )
            logger.debug(f"Successfully generated summary for user {user_id}")
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error generating summary: {str(e)}", exc_info=True
            )
            raise Exception(f"Unexpected error generating summary: {str(e)}")
