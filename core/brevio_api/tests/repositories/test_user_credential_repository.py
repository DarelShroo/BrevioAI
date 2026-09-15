import pytest
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.user.credential_model import CredentialStatus
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.brevio_api.services.encryption_service import EncryptionService


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client.get_database("test_db")


@pytest.fixture
def encryption_service():
    import base64
    import os

    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    return EncryptionService(key=key)


@pytest.fixture
def repository(db, encryption_service):
    return UserCredentialRepository(db, encryption_service)


@pytest.mark.asyncio
async def test_create_and_get_credential(repository):
    await repository.ensure_indexes()
    doc = await repository.create_credential(
        user_id="user1",
        provider="openai",
        api_key="sk-test",
        name="Work OpenAI",
        is_default=True,
    )
    assert doc.user_id == "user1"
    assert doc.provider == "openai"
    assert doc.name == "Work OpenAI"
    assert doc.is_default is True
    assert doc.status == CredentialStatus.ACTIVE

    fetched = await repository.get_credential(doc.id)
    assert fetched is not None
    assert fetched.id == doc.id
    assert fetched.name == "Work OpenAI"

    decrypted = repository.decrypt_credential(fetched)
    assert decrypted == "sk-test"


@pytest.mark.asyncio
async def test_first_credential_becomes_default(repository):
    await repository.ensure_indexes()
    doc = await repository.create_credential(
        "u1", "openai", "k1", name="Primary", is_default=False
    )
    assert doc.is_default is True


@pytest.mark.asyncio
async def test_set_default_credential_demotes_others(repository):
    await repository.ensure_indexes()
    doc1 = await repository.create_credential(
        "u1", "openai", "k1", name="A", is_default=True
    )
    doc2 = await repository.create_credential(
        "u1", "openai", "k2", name="B", is_default=False
    )

    await repository.set_default_credential("u1", doc2.id, "openai")

    f1 = await repository.get_credential(doc1.id)
    f2 = await repository.get_credential(doc2.id)

    assert f1.is_default is False
    assert f2.is_default is True


@pytest.mark.asyncio
async def test_update_credential_name(repository):
    await repository.ensure_indexes()
    doc = await repository.create_credential(
        "u1", "openai", "k1", name="Old", is_default=True
    )
    updated = await repository.update_credential_name("u1", doc.id, "  New label  ")
    assert updated is not None
    assert updated.name == "New label"


@pytest.mark.asyncio
async def test_revoke_default_promotes_another(repository):
    await repository.ensure_indexes()
    doc1 = await repository.create_credential(
        "u1", "openai", "k1", name="A", is_default=True
    )
    doc2 = await repository.create_credential(
        "u1", "openai", "k2", name="B", is_default=False
    )

    revoked = await repository.revoke_credential(doc1.id, "u1")
    assert revoked is True

    f1 = await repository.get_credential(doc1.id)
    f2 = await repository.get_credential(doc2.id)
    assert f1.status == CredentialStatus.REVOKED
    assert f1.is_default is False
    assert f2.is_default is True


@pytest.mark.asyncio
async def test_revoke_credential(repository):
    await repository.ensure_indexes()
    doc = await repository.create_credential(
        "u1", "openai", "k1", name="Only", is_default=True
    )

    revoked = await repository.revoke_credential(doc.id, "u1")

    f = await repository.get_credential(doc.id)
    assert f.status == CredentialStatus.REVOKED
    assert f.is_default is False
    assert revoked is True

    missing = await repository.revoke_credential("missing-id", "u1")
    assert missing is False
