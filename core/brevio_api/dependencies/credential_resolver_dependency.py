from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio.services.credential_resolver import CredentialResolver
from core.brevio.services.platform_access_policy import PlatformAccessPolicy
from core.brevio.services.provider_registry import ProviderRegistry
from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.brevio_api.services.encryption_service import EncryptionService


async def get_credential_resolver(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CredentialResolver:
    encryption_service = EncryptionService()
    user_credential_repository = UserCredentialRepository(db, encryption_service)
    platform_policy = PlatformAccessPolicy()
    provider_registry = ProviderRegistry()
    return CredentialResolver(
        user_credential_repository, platform_policy, provider_registry
    )
