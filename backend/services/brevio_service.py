import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
from pathlib import Path as FilePath
from fastapi import HTTPException, status
from backend.brevio.constants.constants import Constants
from backend.brevio.enums.content import ContentType
from backend.brevio.enums.extension import ExtensionType
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType
from backend.brevio.managers.directory_manager import DirectoryManager
from backend.brevio.models.prompt_config_model import PromptConfig
from backend.brevio.models.summary_config_model import SummaryConfig
from backend.brevio.services.pdf_service import PdfService
from backend.models.brevio.brevio_generate import BrevioGenerate, BaseBrevioGenerate, MediaEntry
from backend.models.user.folder_entry import FolderEntry
from backend.models.user.user_folder import UserFolder
from backend.repositories.user_repository import UserRepository
from backend.utils.string_utils import secure_filename
from ..brevio.__main__ import Main as Brevio
from ..services.user_service import UserService
from ..core.database import DB

class BrevioService:
    def __init__(self):
        self._db = DB()
        user_repository = UserRepository(self._db.database())
        self._user_service = UserService(user_repository)
        self.executor = ThreadPoolExecutor()
        self.directory_manager = DirectoryManager()
        self._pdf_service = PdfService()
        self._brevio = Brevio()

    async def count_media_in_yt_playlist(self, url: str):
        try:
            return await self._brevio.count_media_in_yt_playlist(url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error counting media in YouTube playlist: {str(e)}"
            )

    async def get_media_duration(self, url: str):
        try:
            return await self._brevio.get_media_duration(url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving media duration: {str(e)}"
            )

    async def get_languages(self):
        try:
            return await self._brevio.get_languages()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving languages: {str(e)}"
            )
    
    async def get_all_category_style_combinations(self):
        try:
            return await self._brevio.get_all_category_style_combinations()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving category style combinations: {str(e)}"
            )

    async def get_models(self):
        try:
            return await self._brevio.get_models()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving models: {str(e)}"
            )

    async def generate(self, data: BrevioGenerate, _current_user_id: str) -> Dict:
        try:
            _current_folder_entry_id: str = self._user_service.create_folder_entry(_current_user_id).id
            _user_folder_id: str = self._user_service.get_user_by_id(_current_user_id).folder.id
            return await self._brevio.generate(data, self._user_service.create_data_result, _current_folder_entry_id, _user_folder_id, _current_user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating Brevio data: {str(e)}"
            )

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]], 
        _current_user_id: str,
        _summary_config: SummaryConfig,
        _prompt_config: PromptConfig
    ) -> Dict:
        try:
            current_folder_entry_id: FolderEntry = self._user_service.create_folder_entry(_current_user_id).id
            _user_folder_id: UserFolder = self._user_service.get_user_by_id(_current_user_id).folder.id
            uploads_dir = FilePath(f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/")
            
            uploads_dir.mkdir(parents=True, exist_ok=True)

            saved_files: List[MediaEntry] = []

            for index, (filename, file_content) in enumerate(files_data):
                try:
                    file_path = uploads_dir / str(index) / f"{filename}"
                    await asyncio.get_running_loop().run_in_executor(
                        self.executor,
                        self.save_media,
                        file_content, 
                        file_path
                    )
                    saved_files.append(MediaEntry(path=file_path))
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error processing file {filename}: {str(e)}"
                    )
            
            _data = BrevioGenerate(
                data=saved_files,
                summary_config=_summary_config,
                prompt_config=_prompt_config
            )
            
            return await self._brevio.generate(_data, self._user_service.create_data_result, current_folder_entry_id, _user_folder_id, _current_user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during summary media upload: {str(e)}"
            )

    async def generate_summary_documents(
        self,
        files_data: List[Tuple[str, bytes]], 
        _current_user_id: str,
        _summary_config: SummaryConfig,
        _prompt_config: PromptConfig
    ) -> Dict:
        try:
            current_folder_entry_id = self._user_service.create_folder_entry(_current_user_id).id
            _user_folder_id = self._user_service.get_user_by_id(_current_user_id).folder.id
            uploads_dir = FilePath(f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/")
            
            saved_files: List[MediaEntry] = []
            loop = asyncio.get_event_loop()
            tasks = []

            for index, (filename, file_content) in enumerate(files_data):
                file_path = uploads_dir / str(index) / f"{filename}"
                task = loop.run_in_executor(
                    None, 
                    self.save_media,
                    file_content,
                    file_path
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            saved_files = [MediaEntry(path=uploads_dir / str(index) / filename) for index, (filename, _) in enumerate(files_data)]

            _data = BrevioGenerate(
                data=saved_files,
                summary_config=_summary_config,
                prompt_config=_prompt_config
            )

            return await self._brevio.generate_summary_documents(_data, self._user_service.create_data_result, current_folder_entry_id, _user_folder_id, _current_user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing summary documents: {str(e)}"
            )

    def save_media(self, content: bytes, file_path: FilePath):
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as buffer:
                buffer.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving media file {file_path}: {str(e)}"
            )
