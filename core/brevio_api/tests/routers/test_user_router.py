from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.folder_entry_service_dependency import (
    folder_entry_service_dependency,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_current_user_profile() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    folder_id = ObjectId("507f1f77bcf86cd799439022")
    mock_user = MagicMock()
    mock_user.id = mock_user_id
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.user_credit = 42.5
    mock_user.plan_id = "free"
    mock_user.plan_version = "1"
    mock_user.folder = MagicMock()
    mock_user.folder.id = folder_id

    mock_service = AsyncMock()
    mock_service.get_user_by_id.return_value = mock_user
    mock_service.user_repo = MagicMock()
    # Missing nested attributes → profile falls back to legacy user_credit.
    mock_service.user_repo.collection = None


    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[user_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["id"] == str(mock_user_id)
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["user_credit"] == 42.5
    assert data["folder_id"] == str(folder_id)
    assert data["plan_id"] == "free"
    assert data["plan_name"] == "Free"
    assert data["plan_version"] == "1"
    assert data.get("entitlements") is None
    assert "password" not in body["data"]
    assert "otp" not in body["data"]
    mock_service.get_user_by_id.assert_awaited_once_with(str(mock_user_id))


@pytest.mark.asyncio
async def test_get_current_user_profile_not_found() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    mock_service.get_user_by_id.side_effect = HTTPException(
        status_code=404, detail="User not found"
    )

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[user_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/users/me")

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == "User not found"


@pytest.mark.asyncio
async def test_list_user_entries() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    mock_service.list_entries_for_user.return_value = [
        {
            "_id": ObjectId(),
            "user_id": mock_user_id,
            "name": "Test Entry",
            "results": [],
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[folder_entry_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/users/entries")

    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert data["entries"]
    assert data["entries"][0]["user_id"] == str(mock_user_id)
    assert data["entries"][0]["name"] == "Test Entry"
    mock_service.list_entries_for_user.assert_awaited_once_with(
        str(mock_user_id), folder_id=None
    )


@pytest.mark.asyncio
async def test_list_user_entries_empty() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    mock_service.list_entries_for_user.return_value = []

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[folder_entry_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/users/entries")

    assert response.status_code == 200
    assert response.json() == {"entries": []}


@pytest.mark.asyncio
async def test_delete_user_entry() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    entry_id = str(ObjectId())
    mock_service = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[user_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.delete(f"/users/entries/{entry_id}")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Entry deleted",
        "id": entry_id,
    }
    mock_service.delete_folder_entry_for_user.assert_awaited_once_with(
        str(mock_user_id), entry_id
    )


@pytest.mark.asyncio
async def test_delete_user_entry_forbidden() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    entry_id = str(ObjectId())
    mock_service = AsyncMock()
    mock_service.delete_folder_entry_for_user.side_effect = HTTPException(
        status_code=404, detail="FolderEntry not found"
    )

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[user_service_dependency] = lambda: mock_service

    client = TestClient(app)
    response = client.delete(f"/users/entries/{entry_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_entries() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    mock_service.get_entries.return_value = [
        {
            "_id": ObjectId(),
            "user_id": mock_user_id,
            "name": "Test Entry",
            "results": [],
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: str(mock_user_id)
    app.dependency_overrides[folder_entry_service_dependency] = lambda: mock_service

    entries_refs = [str(ObjectId()), str(ObjectId())]
    payload = {"entries_refs": entries_refs}

    client = TestClient(app)
    response = client.post("/users/entries", json=payload)

    if response.status_code != 200:
        print("Response status:", response.status_code)
        print("Response text:", response.text)

    assert response.status_code == 200

    data = response.json()
    assert "entries" in data, "La respuesta debe contener la clave 'entries'"
    entries = data["entries"]
    assert isinstance(entries, list), "'entries' debe ser una lista"
    assert entries, "La lista 'entries' no debe estar vacía"

    first = entries[0]
    assert first["user_id"] == str(mock_user_id)
    assert first["name"] == "Test Entry"
    assert first["results"] == []
