import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from bson import ObjectId
from fastapi.exceptions import HTTPException
from pydantic import HttpUrl

from core.brevio.enums import LanguageType, ModelType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import WORD_LIMITS_BY_SUMMARY_LEVEL, SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

from .generate import Generate

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
    def get_languages() -> Any:
        try:
            value_map = defaultdict(list)
            for name, member in LanguageType.__members__.items():
                value_map[member.value].append(name)

            languages: List[str] = []

            for value, names in value_map.items():
                languages.append(names[0])

            logger.debug(f"Retrieved {len(languages)} languages")
            return languages
        except Exception as e:
            logger.error(f"Unexpected error getting languages: {str(e)}", exc_info=True)
            raise Exception(f"Unexpected error getting languages: {str(e)}")

    @staticmethod
    def get_models() -> List[str]:
        try:
            models = [member.value for member in ModelType]
            logger.debug(f"Retrieved {len(models)} models")
            return models
        except Exception as e:
            logger.error(f"Unexpected error getting models: {str(e)}", exc_info=True)
            raise Exception(f"Unexpected error getting models: {str(e)}")

    @staticmethod
    async def get_all_category_style_combinations() -> (
        Dict[str, List[Dict[str, Union[str, List[str]]]]]
    ):
        try:
            acg = AdvancedPromptGenerator()
            combinations: List[
                Tuple[str, str, List[str]]
            ] = await acg.get_all_category_style_combinations()

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

    def get_all_summary_levels(self) -> Any:
        try:
            return {"summary_levels": WORD_LIMITS_BY_SUMMARY_LEVEL}
        except Exception as e:
            logger.error(
                f"Unexpected error getting summary levels: {str(e)}", exc_info=True
            )
            raise Exception(f"Unexpected error getting summary levels: {str(e)}")

    def get_all_formats(self) -> Any:
        try:
            return {"output_format_types": list(OutputFormatType)}
        except Exception as e:
            logger.error(
                f"Unexpected error getting summary levels: {str(e)}", exc_info=True
            )
            raise Exception(f"Unexpected error getting summary levels: {str(e)}")

    async def generate(
        self,
        data: Any,
        _create_data_result: Any,
        current_folder_entry_id: str,
        _user_folder_id: str,
        user_id: str,
        _usage_cost_tracker: Any,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = await self._generate._process_online_audio_data(
                data,
                _create_data_result,
                current_folder_entry_id,
                _user_folder_id,
                user_id,
                _usage_cost_tracker,
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
        current_folder_entry_id: str,
        _user_folder_id: str,
        user_id: str,
        _create_data_result: Optional[Callable] = None,
        _usage_cost_tracker: Any = None,
    ) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = await self._generate._process_documents(
                _data,
                current_folder_entry_id,
                _user_folder_id,
                user_id,
                _create_data_result,
                _usage_cost_tracker,
            )
            logger.debug(f"Successfully generated summary for user {user_id}")
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error generating summary: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail=f"Unexpected error generating summary"
            )
