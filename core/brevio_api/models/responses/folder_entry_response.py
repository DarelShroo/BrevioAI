from typing import List

from core.brevio_api.models.responses.base_response_model import BaseResponseModel
from core.brevio_api.models.user.folder_entry import FolderEntry


class GetEntriesResponse(BaseResponseModel):
    entries: List[FolderEntry]
