from typing import Dict
from backend.models.brevio.brevio_generate import BrevioGenerate
from backend.models.user.folder_entry import FolderEntry
from backend.repositories.user_repository import UserRepository
from ..brevio import __main__ as Brevio
from ..services.user_service import UserService
from ..core.database import DB
class BrevioService:
    def __init__(self):
        self._db = DB()
        user_repository = UserRepository(self._db.database())  # Instantiate UserRepository
        self._user_service = UserService(user_repository)  # Pass it to UserServic
    async def count_media_in_yt_playlist(self, url: str):
        return Brevio.count_media_in_yt_playlist(url)

    async def get_media_duration(self, url: str):
        return Brevio.get_media_duration(url)

    async def get_languages(self):
        return Brevio.get_languages()

    async def get_models(self):
        return Brevio.get_models()

    async def generate(self, data: BrevioGenerate, _current_user_id: str, name: str) -> Dict:
        folder_entry = self._user_service.create_folder_entry(_current_user_id, name)
        return await Brevio.generate(data, _current_user_id, self._user_service.create_data_result, folder_entry)
