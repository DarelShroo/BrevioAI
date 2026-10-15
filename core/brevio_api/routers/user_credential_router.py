from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException

from core.brevio.services.provider_registry import (
    InvalidProviderCredential,
    ProviderRegistry,
    get_provider_base_url,
    normalize_api_key,
)
from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.user.credential_model import (
    CredentialStatus,
    UserCredentialDocument,
    UserCredentialResponse,
)
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.brevio_api.services.encryption_service import EncryptionService
from core.shared.utils.model_catalog import (
    is_known_provider,
    is_local_provider,
    provider_requires_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-credentials", tags=["credentials"])


def get_credential_repository(db: AsyncIOMotorDatabase = Depends(get_db)):
    encryption_service = EncryptionService()
    return UserCredentialRepository(db, encryption_service)


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


class CredentialCreateRequest(BaseModel):
    provider: str
    api_key: str
    name: str = Field(min_length=1, max_length=80)
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(ApiErrorCode.CREDENTIAL_NAME_REQUIRED.value)
        return cleaned


class CredentialUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(ApiErrorCode.CREDENTIAL_NAME_REQUIRED.value)
        return cleaned


def _to_response(doc: UserCredentialDocument) -> UserCredentialResponse:
    return UserCredentialResponse(
        _id=doc.id,
        user_id=doc.user_id,
        provider=doc.provider,
        name=doc.name or "",
        is_default=doc.is_default,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get(
    "", response_model=List[UserCredentialResponse], response_model_by_alias=False
)
async def list_all_credentials(
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
):
    docs = await repo.get_active_credentials_for_user(str(_current_user), None)
    return [_to_response(doc) for doc in docs]


@router.get(
    "/{provider}",
    response_model=List[UserCredentialResponse],
    response_model_by_alias=False,
)
async def list_credentials(
    provider: str,
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
):
    credentials = await repo.get_active_credentials_for_user(
        str(_current_user), provider.strip().lower()
    )
    return [_to_response(doc) for doc in credentials]


@router.post(
    "",
    response_model=UserCredentialResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
async def create_credential(
    http_request: Request,
    request: CredentialCreateRequest,
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    from core.brevio_api.services.anti_abuse import enforce_account_mutation_rate_limit

    enforce_account_mutation_rate_limit(http_request, str(_current_user))
    provider = request.provider.strip().lower()
    api_key = normalize_api_key(request.api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave API es obligatoria.",
        )
    if not is_known_provider(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown provider",
        )
    if is_local_provider(provider) or not provider_requires_api_key(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este proveedor no admite claves API de usuario.",
        )

    adapter = registry.get_adapter(provider)
    try:
        is_valid = await adapter.validate_credential(
            api_key, get_provider_base_url(provider)
        )
    except InvalidProviderCredential as exc:
        logger.info(
            "event=credential_rejected provider=%s reason=%s key_prefix=%s",
            provider,
            exc.message[:160],
            api_key[:12],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not is_valid:
        logger.info(
            "event=credential_invalid provider=%s key_prefix=%s",
            provider,
            api_key[:12],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave API no es válida para este proveedor.",
        )

    try:
        credential = await repo.create_credential(
            user_id=str(_current_user),
            provider=provider,
            api_key=api_key,
            name=request.name,
            is_default=request.is_default,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _to_response(credential)


@router.post(
    "/{credential_id}/default",
    response_model=UserCredentialResponse,
    response_model_by_alias=False,
)
async def set_default_credential(
    http_request: Request,
    credential_id: str,
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
):
    from core.brevio_api.services.anti_abuse import enforce_account_mutation_rate_limit

    enforce_account_mutation_rate_limit(http_request, str(_current_user))
    credential_id = credential_id.strip()
    if not credential_id:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.CREDENTIAL_ID_INVALID,
        )

    current = await repo.get_credential(credential_id)
    if (
        current is None
        or current.user_id != str(_current_user)
        or current.status != CredentialStatus.ACTIVE
    ):
        raise CodedHTTPException(
            status_code=404,
            code=ApiErrorCode.CREDENTIAL_NOT_FOUND,
        )

    try:
        updated = await repo.set_default_credential(
            user_id=str(_current_user),
            credential_id=credential_id,
            provider=current.provider,
        )
    except ValueError as exc:
        raise CodedHTTPException(
            status_code=404,
            code=ApiErrorCode.CREDENTIAL_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return _to_response(updated)


@router.patch(
    "/{credential_id}",
    response_model=UserCredentialResponse,
    response_model_by_alias=False,
)
async def update_credential(
    http_request: Request,
    credential_id: str,
    request: CredentialUpdateRequest,
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
):
    from core.brevio_api.services.anti_abuse import enforce_account_mutation_rate_limit

    enforce_account_mutation_rate_limit(http_request, str(_current_user))
    credential_id = credential_id.strip()
    if not credential_id:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.CREDENTIAL_ID_INVALID,
        )
    if request.name is None:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.NOTHING_TO_UPDATE,
        )

    try:
        updated = await repo.update_credential_name(
            user_id=str(_current_user),
            credential_id=credential_id,
            name=request.name,
        )
    except ValueError as exc:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.CREDENTIAL_NAME_REQUIRED,
            detail=str(exc),
        ) from exc

    if updated is None:
        raise CodedHTTPException(
            status_code=404,
            code=ApiErrorCode.CREDENTIAL_NOT_FOUND,
        )
    return _to_response(updated)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    http_request: Request,
    credential_id: str,
    _current_user: str = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
):
    from core.brevio_api.services.anti_abuse import enforce_account_mutation_rate_limit

    enforce_account_mutation_rate_limit(http_request, str(_current_user))
    credential_id = credential_id.strip()
    if not credential_id:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.CREDENTIAL_ID_INVALID,
        )

    revoked = await repo.revoke_credential(credential_id, str(_current_user))
    if not revoked:
        raise CodedHTTPException(
            status_code=404,
            code=ApiErrorCode.CREDENTIAL_NOT_FOUND,
        )
    return
