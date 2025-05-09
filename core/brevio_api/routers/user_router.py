import logging
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from core.brevio_api.dependencies.get_folder_entry_service_dependency import (
    get_folder_entry_service,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.responses.folder_entry_response import GetEntriesResponse
from core.brevio_api.models.user.entry_ref import EntryRef
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.services.folder_entry_service import FolderEntryService

logger = logging.getLogger(__name__)


class UserRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/users", tags=["user"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post("/")
        async def get_user_profile() -> None:
            pass

        @self.router.post(
            "/entries",
            status_code=status.HTTP_200_OK,
            description="Get user entries",
            responses={
                200: {"description": "Successfully retrieved entries"},
                400: {"description": "Invalid ObjectId format"},
                401: {"description": "Unauthorized"},
                403: {"description": "Forbidden"},
                404: {"description": "No entries found"},
                422: {"description": "Validation error for request body"},
                500: {"description": "Internal server error"},
            },
        )
        async def get_user_entries(
            entry_data: EntryRef,
            _current_user: ObjectId = Depends(get_current_user),
            folder_entry_service: FolderEntryService = Depends(
                get_folder_entry_service
            ),
        ) -> GetEntriesResponse:
            try:
                result = await folder_entry_service.get_entries(
                    _user_id=_current_user, _entries_refs=entry_data.entries_refs
                )
                return GetEntriesResponse(entries=result)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in get_user_entries: {str(e)}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected error occurred",
                )


user_router = UserRouter().router
