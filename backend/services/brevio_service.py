import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import shutil
from typing import Dict, List

from fastapi import HTTPException, UploadFile
from backend.brevio.constants.constants import Constants
from backend.brevio.managers.directory_manager import DirectoryManager
from backend.models.brevio.brevio_generate import BrevioGenerate
from backend.models.user.folder_entry import FolderEntry
from backend.models.user.user_folder import UserFolder
from backend.repositories.user_repository import UserRepository
from backend.utils.string_utils import secure_filename
from ..brevio import __main__ as Brevio
from ..services.user_service import UserService
from ..core.database import DB
class BrevioService:
    def __init__(self):
        self._db = DB()
        user_repository = UserRepository(self._db.database())
        self._user_service = UserService(user_repository)
        self.executor = ThreadPoolExecutor()
        self.directory_manager = DirectoryManager()

    async def count_media_in_yt_playlist(self, url: str):
        return Brevio.count_media_in_yt_playlist(url)

    async def get_media_duration(self, url: str):
        return await Brevio.get_media_duration(url)

    async def get_languages(self):
        return Brevio.get_languages()

    async def get_models(self):
        return Brevio.get_models()

    async def generate(self, data: BrevioGenerate, _current_user_id: str, name: str) -> Dict:
        current_folder_entry: FolderEntry = self._user_service.create_folder_entry(_current_user_id, name)
        _user_folder: UserFolder = self._user_service.get_user_by_id(_current_user_id).folder
        return await Brevio.generate(data, self._user_service.create_data_result, current_folder_entry, _user_folder)

    async def generate_summary_media(self, files: List[UploadFile], _current_user_id: str, name: str = "") -> Dict:
        current_folder_entry: FolderEntry = self._user_service.create_folder_entry(_current_user_id, name)
        _user_folder: UserFolder = self._user_service.get_user_by_id(_current_user_id).folder

        uploads_dir = f"{Constants.DESTINATION_FOLDER}/{_user_folder.id}/{current_folder_entry.id}/"
        try:
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error creating upload directory.")

        saved_files = []

        for index, file in enumerate(files):
            try:
                await asyncio.get_running_loop().run_in_executor(self.executor, self.download_media, file, saved_files, uploads_dir)
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                raise HTTPException(status_code=500, detail="Error processing file uploads.")

        return {
                "filenames": saved_files,
                "message": "Files uploaded successfully"
        }
    
    def download_media(self, file: UploadFile, saved_files: List, _uploads_dir: str):
        safe_filename = secure_filename(file.filename)
        file_path = os.path.join(_uploads_dir, safe_filename)

        self.directory_manager.createFolder(_uploads_dir)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file.file.close()

        saved_files.append(safe_filename)
