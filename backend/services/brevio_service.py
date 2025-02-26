import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
from pathlib import Path
from fastapi import HTTPException, Path, UploadFile
from backend.brevio.constants.constants import Constants
from backend.brevio.enums.content import ContentType
from backend.brevio.enums.extension import ExtensionType
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType
from backend.brevio.managers.directory_manager import DirectoryManager
from backend.brevio.services.pdf_service import PdfService
from backend.models.brevio.brevio_generate import BrevioGenerate, BrevioGenerateContent, MediaEntry
from backend.models.user.folder_entry import FolderEntry
from backend.models.user.user_folder import UserFolder
from backend.repositories.user_repository import UserRepository
from backend.utils.string_utils import secure_filename
from ..brevio.__main__ import Main as Brevio
from ..services.user_service import UserService
from ..core.database import DB
from pathlib import Path as FilePath

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
        return await self._brevio.count_media_in_yt_playlist(url)

    async def get_media_duration(self, url: str):
        return await self._brevio.get_media_duration(url)

    async def get_languages(self):
        return self._brevio.get_languages()

    async def get_models(self):
        return self._brevio.get_models()

    async def generate(self, data: BrevioGenerate, _current_user_id: str, name: str) -> Dict:
        current_folder_entry: str = self._user_service.create_folder_entry(_current_user_id, name).id
        _user_folder: str = self._user_service.get_user_by_id(_current_user_id).folder.id
        return await self._brevio.generate(data, self._user_service.create_data_result, current_folder_entry, _user_folder, _current_user_id)

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]], 
        _current_user_id: str,
        brevio_generate_content: BrevioGenerateContent,
        name: str = ""
    ) -> Dict:

        current_folder_entry_id: FolderEntry = self._user_service.create_folder_entry(_current_user_id, name).id
        _user_folder_id: UserFolder = self._user_service.get_user_by_id(_current_user_id).folder.id
        uploads_dir = FilePath(f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/")
        
        try:
            uploads_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error creating upload directory.")
        
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
                print(f"Error processing file {filename}: {e}")
                raise HTTPException(status_code=500, detail="Error processing file uploads.")
        
        data = BrevioGenerate(
            data=saved_files,
            language=brevio_generate_content.language.name,
            model=brevio_generate_content.model.name,
            content=brevio_generate_content.content.name
        )
        
        return await self._brevio.generate(data, self._user_service.create_data_result, current_folder_entry_id, _user_folder_id, _current_user_id)
    
    async def generate_summary_pdf(
        self,
        files_data: List[Tuple[str, bytes]], 
        _current_user_id: str,
        brevio_generate_content: BrevioGenerateContent,
        name: str = ""
    ) -> Dict:
        current_folder_entry_id = self._user_service.create_folder_entry(_current_user_id, name).id
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
        
        try:
            saved_files = await asyncio.gather(*tasks)
            saved_files = [MediaEntry(path=uploads_dir / str(index) / f"{filename}") 
                         for index, (filename, _) in enumerate(files_data)]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file uploads: {str(e)}")

        data = BrevioGenerate(
            data=saved_files,
            language=brevio_generate_content.language.name,
            model=brevio_generate_content.model.name,
            content=brevio_generate_content.content.name
        )

        return await self._brevio.generate_pdf_summary(
            data, 
            self._user_service.create_data_result, 
            current_folder_entry_id, 
            _user_folder_id, 
            _current_user_id
        )

    async def generate_summary_docx(
        self,
        files_data: List[Tuple[str, bytes]], 
        _current_user_id: str,
        brevio_generate_content: BrevioGenerateContent,
        name: str = ""
    ) -> Dict:
        current_folder_entry_id = self._user_service.create_folder_entry(_current_user_id, name).id
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
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file uploads: {str(e)}")

        saved_files = [MediaEntry(path=uploads_dir / str(index) / filename) for index, (filename, _) in enumerate(files_data)]

        data = BrevioGenerate(
            data=saved_files,
            language=brevio_generate_content.language.name,
            model=brevio_generate_content.model.name,
            content=brevio_generate_content.content.name
        )
        return await self._brevio.generate_docx_summary(data, self._user_service.create_data_result, current_folder_entry_id, _user_folder_id, _current_user_id)
    
    def save_media(self, content: bytes, file_path: FilePath):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(content) 