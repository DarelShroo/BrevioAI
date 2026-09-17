import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.brevio_api.dependencies.folder_entry_service_dependency import (
    folder_entry_service_dependency,
)
from core.brevio_api.dependencies.library_folder_service_dependency import (
    library_folder_service_dependency,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency
from core.brevio_api.models.responses.folder_entry_response import GetEntriesResponse
from core.brevio_api.models.responses.user_profile_response import (
    UserProfileDataResponse,
    UserProfileResponse,
)
from core.brevio_api.models.user.entry_ref import EntryRef
from core.brevio_api.models.user.library_dtos import (
    BulkDeleteEntriesRequest,
    BulkEntriesResponse,
    CreateLibraryFolderRequest,
    LibraryFolderView,
    ListLibraryFoldersResponse,
    MoveFolderEntriesRequest,
    PatchFolderEntryRequest,
    RenameLibraryFolderRequest,
)
from core.brevio_api.services.folder_entry_service import FolderEntryService
from core.brevio_api.services.library_folder_service import LibraryFolderService
from core.brevio_api.services.user_service import UserService

logger = logging.getLogger(__name__)


class UserRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/users", tags=["user"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/me",
            status_code=status.HTTP_200_OK,
            response_model=UserProfileDataResponse,
            description="Get the authenticated user's profile",
            responses={
                200: {"description": "Successfully retrieved profile"},
                401: {"description": "Unauthorized"},
                404: {"description": "User not found"},
                500: {"description": "Internal server error"},
            },
        )
        async def get_current_user_profile(
            _current_user: str = Depends(get_current_user),
            user_service: UserService = Depends(user_service_dependency),
        ) -> UserProfileDataResponse:
            from core.brevio_api.services.billing.credit_service import CreditService
            from core.brevio_api.services.billing.product_limit_service import (
                ProductLimitService,
            )

            user = await user_service.get_user_by_id(_current_user)
            folder_id = str(user.folder.id) if user.folder and user.folder.id else None
            balance = float(user.user_credit or 0)
            entitlements = None
            raw_plan = getattr(user, "plan_id", None)
            plan_id = (
                str(raw_plan)
                if isinstance(raw_plan, str) and raw_plan
                else "free"
            )
            plan_name = "Free"
            raw_ver = getattr(user, "plan_version", None)
            plan_version = (
                str(raw_ver) if isinstance(raw_ver, str) and raw_ver else "1"
            )
            try:
                db = user_service.user_repo.collection.database
                credits = CreditService.from_db(db, user_repo=user_service.user_repo)
                products = ProductLimitService.from_db(db)
                if not getattr(user, "plan_id", None):
                    from core.brevio_api.services.billing.plan_registry import (
                        default_plan,
                    )

                    plan = default_plan()
                    await user_service.user_repo.collection.update_one(
                        {"_id": user.id},
                        {
                            "$set": {
                                "plan_id": plan.plan_id,
                                "plan_version": plan.version,
                            }
                        },
                    )
                    user.plan_id = plan.plan_id
                    user.plan_version = plan.version
                from core.brevio_api.services.billing.plan_registry import get_plan

                try:
                    user_plan = get_plan(str(getattr(user, "plan_id", None) or "free"))
                except KeyError:
                    from core.brevio_api.services.billing.plan_registry import (
                        default_plan,
                    )

                    user_plan = default_plan()
                await credits.ensure_period_credits(
                    str(user.id), user_plan, user=user
                )
                balance = float(await credits.get_balance(str(user.id)))
                entitlements = await products.entitlements(
                    user, credit_balance=int(balance)
                )
                plan_id = entitlements["plan_id"]
                plan_name = entitlements["plan_name"]
                plan_version = entitlements["plan_version"]
            except Exception:
                logger.exception(
                    "event=credit_balance_profile_fallback user_id=%s", user.id
                )
            return UserProfileDataResponse(
                status="success",
                data=UserProfileResponse(
                    id=str(user.id),
                    username=user.username,
                    email=user.email,
                    user_credit=balance,
                    folder_id=folder_id,
                    plan_id=plan_id,
                    plan_name=plan_name,
                    plan_version=plan_version,
                    entitlements=entitlements,
                ),
            )

        @self.router.get(
            "/folders",
            status_code=status.HTTP_200_OK,
            response_model=ListLibraryFoldersResponse,
            description="List library folders for the authenticated user",
        )
        async def list_library_folders(
            _current_user: str = Depends(get_current_user),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> ListLibraryFoldersResponse:
            folders = await library_folders.list_folders(_current_user)
            unfiled = await library_folders.unfiled_count(_current_user)
            return ListLibraryFoldersResponse(
                folders=[LibraryFolderView(**item) for item in folders],
                unfiled_count=unfiled,
            )

        @self.router.post(
            "/folders",
            status_code=status.HTTP_201_CREATED,
            description="Create a library folder",
        )
        async def create_library_folder(
            body: CreateLibraryFolderRequest,
            _current_user: str = Depends(get_current_user),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> dict:
            folder = await library_folders.create_folder(_current_user, body.name)
            return {
                "id": str(folder.id),
                "name": folder.name,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "entry_count": 0,
            }

        @self.router.patch(
            "/folders/{folder_id}",
            status_code=status.HTTP_200_OK,
            description="Rename a library folder",
        )
        async def rename_library_folder(
            folder_id: str,
            body: RenameLibraryFolderRequest,
            _current_user: str = Depends(get_current_user),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> dict:
            folder = await library_folders.rename_folder(
                _current_user, folder_id, body.name
            )
            return {
                "id": str(folder.id),
                "name": folder.name,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
            }

        @self.router.delete(
            "/folders/{folder_id}",
            status_code=status.HTTP_200_OK,
            description="Delete a library folder without deleting its summaries",
        )
        async def delete_library_folder(
            folder_id: str,
            _current_user: str = Depends(get_current_user),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> dict:
            await library_folders.delete_folder(_current_user, folder_id)
            return {"status": "success", "id": folder_id}

        @self.router.get(
            "/entries",
            status_code=status.HTTP_200_OK,
            description="List all folder entries for the authenticated user",
            responses={
                200: {"description": "Successfully retrieved entries"},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"},
            },
        )
        async def list_user_entries(
            folder_id: Optional[str] = Query(None),
            _current_user: str = Depends(get_current_user),
            folder_entry_service: FolderEntryService = Depends(
                folder_entry_service_dependency
            ),
        ) -> GetEntriesResponse:
            try:
                result = await folder_entry_service.list_entries_for_user(
                    _current_user, folder_id=folder_id
                )
                return GetEntriesResponse(entries=result)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in list_user_entries: {str(e)}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected error occurred",
                )

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
            _current_user: str = Depends(get_current_user),
            folder_entry_service: FolderEntryService = Depends(
                folder_entry_service_dependency
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

        @self.router.post(
            "/entries/move",
            status_code=status.HTTP_200_OK,
            response_model=BulkEntriesResponse,
            description="Move one or more summaries to a folder or unfiled",
        )
        async def move_user_entries(
            body: MoveFolderEntriesRequest,
            _current_user: str = Depends(get_current_user),
            user_service: UserService = Depends(user_service_dependency),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> BulkEntriesResponse:
            folder_oid = await library_folders.resolve_optional_folder(
                _current_user, body.library_folder_id
            )
            result = await user_service.move_folder_entries(
                _current_user, body.entry_ids, folder_oid
            )
            return BulkEntriesResponse(**result)

        @self.router.post(
            "/entries/delete",
            status_code=status.HTTP_200_OK,
            response_model=BulkEntriesResponse,
            description="Delete one or more summaries owned by the authenticated user",
        )
        async def bulk_delete_user_entries(
            body: BulkDeleteEntriesRequest,
            _current_user: str = Depends(get_current_user),
            user_service: UserService = Depends(user_service_dependency),
        ) -> BulkEntriesResponse:
            result = await user_service.delete_folder_entries_for_user(
                _current_user, body.entry_ids
            )
            return BulkEntriesResponse(**result)

        @self.router.patch(
            "/entries/{entry_id}",
            status_code=status.HTTP_200_OK,
            description="Rename and/or move a summary",
        )
        async def patch_user_entry(
            entry_id: str,
            body: PatchFolderEntryRequest,
            _current_user: str = Depends(get_current_user),
            user_service: UserService = Depends(user_service_dependency),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> dict:
            entry = await user_service.require_owned_entry(_current_user, entry_id)
            if "name" in body.model_fields_set and body.name is not None:
                entry = await user_service.rename_folder_entry(
                    _current_user, entry_id, body.name
                )
            if "library_folder_id" in body.model_fields_set:
                folder_oid = await library_folders.resolve_optional_folder(
                    _current_user, body.library_folder_id
                )
                await user_service.move_folder_entries(
                    _current_user, [entry_id], folder_oid
                )
                entry = await user_service.require_owned_entry(_current_user, entry_id)
            return entry.model_dump(mode="json")

        @self.router.delete(
            "/entries/{entry_id}",
            status_code=status.HTTP_200_OK,
            description="Delete a folder entry owned by the authenticated user",
            responses={
                200: {"description": "Entry deleted"},
                400: {"description": "Invalid entry ID"},
                401: {"description": "Unauthorized"},
                403: {"description": "Forbidden"},
                404: {"description": "Entry not found"},
                500: {"description": "Internal server error"},
            },
        )
        async def delete_user_entry(
            entry_id: str,
            _current_user: str = Depends(get_current_user),
            user_service: UserService = Depends(user_service_dependency),
        ) -> dict:
            await user_service.delete_folder_entry_for_user(_current_user, entry_id)
            return {"status": "success", "message": "Entry deleted", "id": entry_id}


user_router = UserRouter().router
