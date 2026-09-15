import base64
import os
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.repositories.user_credential_repository import (
    UserCredentialRepository,
)
from core.brevio_api.routers.user_credential_router import get_credential_repository
from core.brevio_api.services.encryption_service import EncryptionService

client = TestClient(app)


@pytest.fixture
def repository() -> UserCredentialRepository:
    db = AsyncMongoMockClient().get_database("test_db")
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    return UserCredentialRepository(db, EncryptionService(key=key))


@pytest.fixture
def authed_repo(
    repository: UserCredentialRepository,
) -> Generator[UserCredentialRepository, None, None]:
    app.dependency_overrides[get_current_user] = lambda: "u1"
    app.dependency_overrides[get_credential_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_create_rejects_invalid_api_key(authed_repo: UserCredentialRepository):
    with patch(
        "core.brevio.services.provider_registry.OpenAIAdapter.validate_credential",
        new=AsyncMock(return_value=False),
    ):
        response = client.post(
            "/user-credentials",
            json={
                "provider": "openai",
                "api_key": "sk-invalid",
                "name": "Bad key",
                "is_default": False,
            },
        )
    assert response.status_code == 400
    assert "no es válida" in response.json()["message"]
    listed = client.get("/user-credentials/openai")
    assert listed.json() == []


def test_create_validates_then_stores_key(authed_repo: UserCredentialRepository):
    with patch(
        "core.brevio.services.provider_registry.OpenAIAdapter.validate_credential",
        new=AsyncMock(return_value=True),
    ) as validate:
        response = client.post(
            "/user-credentials",
            json={
                "provider": "openai",
                "api_key": "sk-live",
                "name": "Prod OpenAI",
                "is_default": True,
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["provider"] == "openai"
    assert body["name"] == "Prod OpenAI"
    assert body["is_default"] is True
    assert "encrypted_key" not in body
    validate.assert_awaited_once()
    listed = client.get("/user-credentials/openai")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert listed.json()[0]["name"] == "Prod OpenAI"


def test_create_rejects_missing_name(authed_repo: UserCredentialRepository):
    with patch(
        "core.brevio.services.provider_registry.OpenAIAdapter.validate_credential",
        new=AsyncMock(return_value=True),
    ):
        response = client.post(
            "/user-credentials",
            json={"provider": "openai", "api_key": "sk-live", "name": "   "},
        )
    assert response.status_code == 422


def test_create_rejects_local_provider(authed_repo: UserCredentialRepository):
    response = client.post(
        "/user-credentials",
        json={
            "provider": "ollama",
            "api_key": "anything",
            "name": "Local",
            "is_default": False,
        },
    )
    assert response.status_code == 400
    assert "no admite" in response.json()["message"]


def test_set_default_and_rename(authed_repo: UserCredentialRepository):
    with patch(
        "core.brevio.services.provider_registry.OpenAIAdapter.validate_credential",
        new=AsyncMock(return_value=True),
    ):
        first = client.post(
            "/user-credentials",
            json={
                "provider": "openai",
                "api_key": "sk-1",
                "name": "First",
                "is_default": True,
            },
        )
        second = client.post(
            "/user-credentials",
            json={
                "provider": "openai",
                "api_key": "sk-2",
                "name": "Second",
                "is_default": False,
            },
        )
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    renamed = client.patch(
        f"/user-credentials/{second_id}", json={"name": "Backup key"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Backup key"

    made_default = client.post(f"/user-credentials/{second_id}/default")
    assert made_default.status_code == 200
    assert made_default.json()["is_default"] is True

    listed = client.get("/user-credentials/openai")
    by_id = {item["id"]: item for item in listed.json()}
    assert by_id[first_id]["is_default"] is False
    assert by_id[second_id]["is_default"] is True
    assert by_id[second_id]["name"] == "Backup key"


def test_delete_revokes_uuid_credential(authed_repo: UserCredentialRepository):
    with patch(
        "core.brevio.services.provider_registry.OpenAIAdapter.validate_credential",
        new=AsyncMock(return_value=True),
    ):
        created = client.post(
            "/user-credentials",
            json={
                "provider": "openai",
                "api_key": "sk-live",
                "name": "Temp",
                "is_default": False,
            },
        )
    credential_id = created.json()["id"]
    deleted = client.delete(f"/user-credentials/{credential_id}")
    assert deleted.status_code == 204
    listed = client.get("/user-credentials/openai")
    assert listed.status_code == 200
    assert listed.json() == []


def test_delete_unknown_credential(authed_repo: UserCredentialRepository):
    response = client.delete("/user-credentials/not-a-real-id")
    assert response.status_code == 404
