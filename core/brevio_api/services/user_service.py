import logging
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, status
from pydantic import EmailStr, ValidationError
from pymongo.errors import PyMongoError

from core.brevio_api.events.publisher import publish_summary_job_event
from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.utils.password_utils import hash_password
from core.shared.enums.job_status import JobStatus, can_transition_status
from core.shared.models.user.data_result import DataResult
from core.shared.utils.source_names import (
    NameValidationError,
    require_editable_name,
    resolve_entry_display_name,
)

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self, user_repository: UserRepository, _folder_entry_repo: FolderEntryRepository
    ):
        self._folder_entry_repo = _folder_entry_repo
        self.user_repo = user_repository
        logger.info("UserService initialized with UserRepository")

    async def get_user_by_id(self, user_id: str) -> User | None:
        try:
            logger.debug(f"Fetching user with ID: {user_id}")
            user = await self.user_repo.get_user_by_field("_id", user_id)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            logger.info(f"User retrieved successfully with ID: {user_id}")

            return user
        except HTTPException:
            raise
        except ValidationError as e:
            logger.error(f"Invalid user data for _id={user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user data: {str(e)}",
            )
        except Exception as e:
            logger.error(
                f"Error retrieving user by ID {user_id}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by ID: {str(e)}",
            )

    async def get_user_by_email(self, email: EmailStr) -> User | None:
        try:
            logger.debug(f"Fetching user with email: {email}")
            user = await self.user_repo.get_user_by_field("email", email)
            logger.info(f"User found with email: {email}")

            return user
        except Exception as e:
            logger.error(
                f"Error retrieving user by email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by email: {str(e)}",
            )

    async def get_user_by_username(self, username: str) -> User | None:
        try:
            logger.debug(f"Fetching user with username: {username}")

            user = await self.user_repo.get_user_by_field("username", username)

            logger.info(f"User found with username: {username}")

            return user
        except Exception as e:
            logger.error(
                f"Error retrieving user by username {username}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by username",
            )

    async def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")
            user_exist = await self.user_repo.get_user_by_field(
                "email", user.email
            ) or await self.user_repo.get_user_by_field("username", user.username)
            if user_exist:
                logger.warning(
                    f"User already exists with email: {user.email} or username: {user.username}"
                )
                raise HTTPException(status_code=400, detail="User already exists")
            created_user = await self.user_repo.create_user(user)
            logger.info(f"User created successfully with ID: {created_user.id}")
            return created_user
        except ValidationError as e:
            logger.error(f"Invalid user data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid user data: {str(e)}")
        except PyMongoError as e:
            logger.error(f"Database error creating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    async def initiate_password_recovery(self, email: EmailStr) -> None:
        try:
            logger.debug(f"Initiating password recovery for email: {email}")
            user = await self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            otp_code = str(random.randint(100000, 999999))
            otp_expiration = datetime.now(timezone.utc) + timedelta(minutes=10)

            await self.user_repo.update_user(
                user.id,
                {
                    "otp": otp_code,
                    "exp": otp_expiration,
                },
            )
            logger.info(
                f"Password recovery initiated for email: {email}, OTP: {otp_code}"
            )
        except Exception as e:
            logger.error(
                f"Error initiating password recovery for email {email}: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initiating password recovery: {str(e)}",
            )

    async def verify_otp(self, email: EmailStr, otp_code: str) -> bool:
        try:
            logger.debug(f"Verifying OTP for email: {email}, OTP: {otp_code}")
            user = await self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            if user.otp != otp_code:
                logger.warning(f"Invalid OTP for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OTP",
                )

            if user.exp is None:
                logger.warning(f"Missing expiration for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP expiration not set",
                )

            if datetime.now(timezone.utc) > datetime.fromtimestamp(
                user.exp, timezone.utc
            ):
                logger.warning(f"Expired OTP for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expired OTP",
                )

            await self.user_repo.update_user(user.id, {"is_otp_verified": True})
            logger.info(f"OTP verified successfully for email: {email}")
            return True
        except Exception as e:
            logger.error(
                f"Error verifying OTP for email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying OTP: {str(e)}",
            )

    async def change_password(self, email: EmailStr, new_password: str) -> User:
        try:
            logger.debug(f"Changing password for email: {email}")
            user = await self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            updated_user = await self.user_repo.update_user(
                user.id,
                {"password": hash_password(new_password), "otp": None, "exp": 0},
            )

            if not updated_user:
                logger.warning(f"Failed to change password for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to change password",
                )
            logger.info(f"Password changed successfully for email: {email}")

            return updated_user
        except Exception as e:
            logger.error(
                f"Error changing password for email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error changing password: {str(e)}",
            )

    async def create_folder_entry(
        self,
        user_id: str,
        *,
        name: str = "",
        original_name: str | None = None,
        library_folder_id: str | ObjectId | None = None,
        language: str | None = None,
        model: str | None = None,
        category: str | None = None,
        style: str | None = None,
        format: str | None = None,
        summary_level: str | None = None,
        source_type: str | None = None,
    ) -> str:
        try:
            logger.debug(f"Creating FolderEntry for user ID: {user_id}")

            user = await self.user_repo.get_user_by_field("_id", user_id)

            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")

            if user.folder is None:
                user.folder = UserFolder(entries=[])
            elif user.folder.entries is None:
                user.folder.entries = []

            now = datetime.now(timezone.utc)
            folder_oid = None
            if library_folder_id:
                folder_oid = ObjectId(str(library_folder_id))
            entry = FolderEntry(
                user_id=user.id,
                name=name or "",
                original_name=original_name,
                library_folder_id=folder_oid,
                results=[],
                created_at=now,
                updated_at=now,
                language=language,
                model=model,
                category=category,
                style=style,
                format=format,
                summary_level=summary_level,
                source_type=source_type,
            )

            created_entry = await self._folder_entry_repo.create_folder_entry(entry)

            resolved_name = resolve_entry_display_name(
                entry_id=str(created_entry.id),
                name=created_entry.name,
                original_name=created_entry.original_name,
                results=created_entry.results,
            )
            if resolved_name != (created_entry.name or "").strip():
                created_entry = await self._folder_entry_repo.update_folder_entry(
                    str(created_entry.id),
                    {
                        "$set": {
                            "name": resolved_name,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )

            entry_ref = ObjectId(created_entry.id)

            user.folder.entries.append(entry_ref)

            update_data = {"folder.entries": user.folder.entries}

            updated_user = await self.user_repo.update_user(user.id, update_data)

            if not updated_user:
                logger.error(f"Failed to update user {user_id} with new folder entry")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update user with new folder entry",
                )

            logger.info(f"FolderEntry {entry_ref} created and linked to user {user_id}")
            return str(entry_ref)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error creating FolderEntry for user {user_id}: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Error creating FolderEntry: {str(e)}"
            )

    async def require_owned_entry(
        self, user_id: str, folder_entry_id: str
    ) -> FolderEntry:
        if not ObjectId.is_valid(folder_entry_id):
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.ENTRY_NOT_FOUND
            )
        try:
            entry = await self._folder_entry_repo.get_folder_entry_by_id(
                folder_entry_id
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise CodedHTTPException(
                    status.HTTP_404_NOT_FOUND, ApiErrorCode.ENTRY_NOT_FOUND
                ) from exc
            raise
        except ValueError as exc:
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.ENTRY_NOT_FOUND
            ) from exc
        if str(entry.user_id) != str(user_id):
            raise CodedHTTPException(
                status.HTTP_403_FORBIDDEN, ApiErrorCode.ENTRY_FORBIDDEN
            )
        return entry

    async def rename_folder_entry(
        self, user_id: str, folder_entry_id: str, name: str
    ) -> FolderEntry:
        await self.require_owned_entry(user_id, folder_entry_id)
        try:
            cleaned = require_editable_name(
                name,
                code_empty=ApiErrorCode.ENTRY_NAME_INVALID.value,
                code_too_long=ApiErrorCode.ENTRY_NAME_TOO_LONG.value,
            )
        except NameValidationError as exc:
            raise CodedHTTPException(status.HTTP_400_BAD_REQUEST, exc.code) from exc
        try:
            return await self._folder_entry_repo.update_folder_entry(
                folder_entry_id,
                {"$set": {"name": cleaned, "updated_at": datetime.now(timezone.utc)}},
            )
        except ValueError as exc:
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.ENTRY_NOT_FOUND
            ) from exc

    async def move_folder_entries(
        self,
        user_id: str,
        entry_ids: list[str],
        library_folder_id: ObjectId | None,
    ) -> dict:
        unique_ids = list(dict.fromkeys(entry_ids or []))
        if not unique_ids:
            raise CodedHTTPException(
                status.HTTP_400_BAD_REQUEST, ApiErrorCode.ENTRY_IDS_REQUIRED
            )
        succeeded: list[str] = []
        failed: list[dict] = []
        owned: list[ObjectId] = []
        for raw_id in unique_ids:
            try:
                entry = await self.require_owned_entry(user_id, raw_id)
                owned.append(ObjectId(str(entry.id)))
                succeeded.append(str(entry.id))
            except CodedHTTPException as exc:
                failed.append({"id": raw_id, "code": exc.code})
        if owned:
            await self._folder_entry_repo.set_library_folder(
                user_id, owned, library_folder_id
            )
        return {"succeeded": succeeded, "failed": failed}

    async def delete_folder_entries_for_user(
        self, user_id: str, entry_ids: list[str]
    ) -> dict:
        unique_ids = list(dict.fromkeys(entry_ids or []))
        if not unique_ids:
            raise CodedHTTPException(
                status.HTTP_400_BAD_REQUEST, ApiErrorCode.ENTRY_IDS_REQUIRED
            )
        succeeded: list[str] = []
        failed: list[dict] = []
        for raw_id in unique_ids:
            try:
                await self.require_owned_entry(user_id, raw_id)
                await self.delete_folder_entry_for_user(user_id, raw_id)
                succeeded.append(raw_id)
            except CodedHTTPException as exc:
                failed.append({"id": raw_id, "code": exc.code})
            except HTTPException as exc:
                code = (
                    ApiErrorCode.ENTRY_FORBIDDEN.value
                    if exc.status_code == status.HTTP_403_FORBIDDEN
                    else ApiErrorCode.ENTRY_NOT_FOUND.value
                )
                failed.append({"id": raw_id, "code": code})
        return {"succeeded": succeeded, "failed": failed}

    async def update_folder_entry_metadata(
        self,
        folder_entry_id: str,
        *,
        name: str | None = None,
        language: str | None = None,
        model: str | None = None,
        category: str | None = None,
        style: str | None = None,
        format: str | None = None,
        summary_level: str | None = None,
        source_type: str | None = None,
    ) -> FolderEntry:
        fields: dict = {"updated_at": datetime.now(timezone.utc)}
        if name is not None:
            fields["name"] = name
        if language is not None:
            fields["language"] = language
        if model is not None:
            fields["model"] = model
        if category is not None:
            fields["category"] = category
        if style is not None:
            fields["style"] = style
        if format is not None:
            fields["format"] = format
        if summary_level is not None:
            fields["summary_level"] = summary_level
        if source_type is not None:
            fields["source_type"] = source_type
        try:
            return await self._folder_entry_repo.update_folder_entry(
                folder_entry_id, {"$set": fields}
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "Error updating FolderEntry metadata %s: %s",
                folder_entry_id,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Error updating folder entry metadata"
            ) from e

    async def delete_folder_entry_for_user(
        self, user_id: str, folder_entry_id: str
    ) -> None:
        if not ObjectId.is_valid(folder_entry_id):
            raise HTTPException(status_code=400, detail="Invalid entry ID format")
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        try:
            entry = await self._folder_entry_repo.get_folder_entry_by_id(
                folder_entry_id
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        if str(entry.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not own this folder entry",
            )

        user = await self.user_repo.get_user_by_field("_id", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.folder and user.folder.entries:
            entry_oid = ObjectId(folder_entry_id)
            remaining = [
                ref for ref in user.folder.entries if ObjectId(str(ref)) != entry_oid
            ]
            await self.user_repo.update_user(user.id, {"folder.entries": remaining})

        try:
            await self._folder_entry_repo.delete_folder_entry(folder_entry_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "Error deleting FolderEntry %s: %s",
                folder_entry_id,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Error deleting folder entry"
            ) from e

        # Best-effort filesystem cleanup; DB delete already succeeded.
        try:
            import shutil
            from pathlib import Path

            from core.brevio.constants.constants import Constants

            if user.folder and user.folder.id:
                entry_dir = Path(
                    f"{Constants.DESTINATION_FOLDER}/{user.folder.id}/{folder_entry_id}"
                )
                if entry_dir.exists() and entry_dir.is_dir():
                    shutil.rmtree(entry_dir, ignore_errors=True)
        except Exception as cleanup_error:
            logger.warning(
                "Filesystem cleanup failed for entry %s: %s",
                folder_entry_id,
                cleanup_error,
            )

    async def create_data_result(
        self, user_id: str, folder_entry_id: str, result: DataResult
    ) -> DataResult:
        try:
            logger.debug(
                f"Creating DataResult for user ID: {user_id}, FolderEntry ID: {folder_entry_id}"
            )

            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid user ID format: {user_id}")
                raise HTTPException(status_code=400, detail="Invalid user ID format")
            user_id_obj = ObjectId(user_id)

            if not ObjectId.is_valid(folder_entry_id):
                logger.warning(f"Invalid FolderEntry ID format: {folder_entry_id}")
                raise HTTPException(
                    status_code=400, detail="Invalid FolderEntry ID format"
                )

            from core.brevio_api.repositories.folder_entry_repository import (
                data_result_to_mongo,
            )

            result_dict = data_result_to_mongo(result)
            logger.debug(f"Serialized DataResult: {result_dict}")

            user = await self.user_repo.get_user_by_field("_id", user_id_obj)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")

            folder_entry = await self._folder_entry_repo.get_folder_entry_by_id(
                folder_entry_id
            )
            if not folder_entry:
                logger.warning(
                    f"FolderEntry not found. Requested ID: {folder_entry_id}"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"FolderEntry with ID {folder_entry_id} not found",
                )

            update_data = {
                "$push": {"results": {"$each": [result_dict]}},
                "$set": {"updated_at": datetime.now(ZoneInfo("UTC"))},
            }

            update_result = await self._folder_entry_repo.update_folder_entry(
                folder_entry_id, update_data
            )
            if not update_result:
                logger.error(f"Failed to update FolderEntry {folder_entry_id}")
                raise HTTPException(
                    status_code=500, detail="Failed to update folder entry"
                )

            logger.info(
                f"DataResult added to FolderEntry {folder_entry_id} for user {user_id}"
            )
            return result
        except PyMongoError as e:
            logger.error(f"MongoDB error creating DataResult: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Database error while creating DataResult: {str(e)}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error creating DataResult: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error creating DataResult: {str(e)}",
            )

    async def update_data_result_status(
        self,
        user_id: str,
        folder_entry_id: str,
        result: DataResult,
        *,
        status: str,
        phase: str,
        success: bool,
        error_type: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        download_location: str | None = None,
        name: str | None = None,
        index: int | None = None,
    ) -> DataResult:
        """Idempotent terminal/status write. Never demotes COMPLETED ↔ FAILED."""
        try:
            folder_entry = await self._folder_entry_repo.get_folder_entry_by_id(
                folder_entry_id
            )
            current = None
            for item in folder_entry.results or []:
                if str(item.id) == str(result.id):
                    current = item.status
                    break
            if not can_transition_status(current, status):
                logger.error(
                    "Rejected DataResult status transition result=%s current=%s new=%s "
                    "folder=%s user=%s",
                    result.id,
                    current,
                    status,
                    folder_entry_id,
                    user_id,
                )
                return result

            fields: dict = {
                "status": status,
                "phase": phase,
                "success": success,
            }
            if error_type is not None:
                fields["error_type"] = error_type
            if error_code is not None:
                fields["error_code"] = error_code
            if error_message is not None:
                fields["error_message"] = error_message
            if download_location is not None:
                fields["download_location"] = download_location
            if name is not None:
                fields["name"] = name
            if index is not None:
                fields["index"] = index
            if status == JobStatus.COMPLETED.value:
                fields["error_type"] = None
                fields["error_code"] = None
                fields["error_message"] = None

            await self._folder_entry_repo.update_data_result(
                folder_entry_id, result.id, fields
            )
            result.status = status
            result.phase = phase
            result.success = success
            result.error_type = (
                None if status == JobStatus.COMPLETED.value else error_type
            )
            result.error_code = (
                None if status == JobStatus.COMPLETED.value else error_code
            )
            result.error_message = (
                None if status == JobStatus.COMPLETED.value else error_message
            )
            if download_location is not None:
                result.download_location = download_location
            logger.info(
                "DataResult %s status=%s phase=%s success=%s folder=%s",
                result.id,
                status,
                phase,
                success,
                folder_entry_id,
            )
            if current != status:
                document_name = name or result.name or folder_entry.name or ""
                self._publish_terminal_event(
                    user_id=str(folder_entry.user_id or user_id),
                    job_id=str(folder_entry_id),
                    document_id=str(result.id),
                    status=status,
                    document_name=document_name,
                    error_code=None
                    if status == JobStatus.COMPLETED.value
                    else error_code,
                    error_message=(
                        None if status == JobStatus.COMPLETED.value else error_message
                    ),
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to persist DataResult status result=%s folder=%s status=%s: %s",
                getattr(result, "id", None),
                folder_entry_id,
                status,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to persist DataResult status: {e}",
            )

    async def fail_processing_results(
        self,
        folder_entry_id: str,
        error: BaseException,
        *,
        phase: str = "FAILED",
    ) -> None:
        """Mark leftover PROCESSING rows FAILED if the job died without a terminal write."""
        try:
            folder_entry = await self._folder_entry_repo.get_folder_entry_by_id(
                folder_entry_id
            )
        except Exception as e:
            logger.error(
                "Cannot fail open PROCESSING results for folder %s: %s",
                folder_entry_id,
                e,
                exc_info=True,
            )
            return
        for item in folder_entry.results or []:
            if item.status != JobStatus.PROCESSING.value:
                continue
            try:
                fallback_fields = {
                    "status": JobStatus.FAILED.value,
                    "phase": item.phase or phase,
                    "success": False,
                    "error_type": type(error).__name__,
                    "error_code": phase,
                    "error_message": str(error),
                }
                if item.index is not None:
                    fallback_fields["index"] = item.index
                if item.download_location:
                    fallback_fields["download_location"] = item.download_location
                if item.name:
                    fallback_fields["name"] = item.name
                await self._folder_entry_repo.update_data_result(
                    folder_entry_id,
                    item.id,
                    fallback_fields,
                )
                self._publish_terminal_event(
                    user_id=str(folder_entry.user_id),
                    job_id=str(folder_entry_id),
                    document_id=str(item.id),
                    status=JobStatus.FAILED.value,
                    document_name=item.name or folder_entry.name or "",
                    error_code=phase,
                    error_message=str(error),
                )
            except Exception as persist_err:
                logger.error(
                    "Failed to mark PROCESSING DataResult %s as FAILED: %s",
                    item.id,
                    persist_err,
                    exc_info=True,
                )

    @staticmethod
    def _publish_terminal_event(
        *,
        user_id: str,
        job_id: str,
        document_id: str,
        status: str,
        document_name: str = "",
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status not in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
            return
        publish_summary_job_event(
            user_id=user_id,
            job_id=job_id,
            document_id=document_id,
            status=status,
            document_name=document_name,
            error_code=error_code,
            error_message=error_message,
        )
