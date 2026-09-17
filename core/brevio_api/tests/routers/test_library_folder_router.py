from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.folder_entry_service_dependency import (
    folder_entry_service_dependency,
)
from core.brevio_api.dependencies.library_folder_service_dependency import (
    library_folder_service_dependency,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency
from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.models.user.library_folder import LibraryFolder


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _client(
    user_id: str,
    folders: AsyncMock | None = None,
    users: AsyncMock | None = None,
    entries: AsyncMock | None = None,
) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: user_id
    if folders is not None:
        app.dependency_overrides[library_folder_service_dependency] = lambda: folders
    if users is not None:
        app.dependency_overrides[user_service_dependency] = lambda: users
    if entries is not None:
        app.dependency_overrides[folder_entry_service_dependency] = lambda: entries
    return TestClient(app)


def test_create_list_rename_delete_folder() -> None:
    user_id = str(ObjectId())
    folder = LibraryFolder(
        user_id=ObjectId(user_id), name="Backend", name_key="backend"
    )
    folders = AsyncMock()
    folders.create_folder = AsyncMock(return_value=folder)
    folders.list_folders = AsyncMock(
        return_value=[
            {
                "id": str(folder.id),
                "name": folder.name,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "entry_count": 0,
            }
        ]
    )
    folders.unfiled_count = AsyncMock(return_value=4)
    folders.rename_folder = AsyncMock(return_value=folder)
    folders.delete_folder = AsyncMock(return_value=None)

    client = _client(user_id, folders=folders)
    created = client.post("/users/folders", json={"name": "Backend"})
    assert created.status_code == 201
    assert created.json()["name"] == "Backend"

    listed = client.get("/users/folders")
    assert listed.status_code == 200
    body = listed.json()
    assert body["unfiled_count"] == 4
    assert body["folders"][0]["name"] == "Backend"

    renamed = client.patch(f"/users/folders/{folder.id}", json={"name": "Universidad"})
    assert renamed.status_code == 200
    deleted = client.delete(f"/users/folders/{folder.id}")
    assert deleted.status_code == 200


def test_folder_forbidden_and_not_found() -> None:
    user_id = str(ObjectId())
    folders = AsyncMock()
    folders.require_owned_folder = AsyncMock(
        side_effect=CodedHTTPException(404, ApiErrorCode.FOLDER_NOT_FOUND)
    )
    folders.rename_folder = AsyncMock(
        side_effect=CodedHTTPException(404, ApiErrorCode.FOLDER_NOT_FOUND)
    )
    client = _client(user_id, folders=folders)
    response = client.patch(f"/users/folders/{ObjectId()}", json={"name": "Hack"})
    assert response.status_code == 404
    assert response.json()["code"] == ApiErrorCode.FOLDER_NOT_FOUND.value

    folders.rename_folder = AsyncMock(
        side_effect=CodedHTTPException(404, ApiErrorCode.FOLDER_NOT_FOUND)
    )
    missing = client.patch(f"/users/folders/{ObjectId()}", json={"name": "Hack"})
    assert missing.status_code == 404
    assert missing.json()["code"] == ApiErrorCode.FOLDER_NOT_FOUND.value


def test_move_bulk_delete_and_list_unfiled() -> None:
    user_id = str(ObjectId())
    entry = FolderEntry(user_id=ObjectId(user_id), name="FastAPI")
    folders = AsyncMock()
    folders.resolve_optional_folder = AsyncMock(return_value=None)
    users = AsyncMock()
    users.move_folder_entries = AsyncMock(
        return_value={"succeeded": [str(entry.id)], "failed": []}
    )
    users.delete_folder_entries_for_user = AsyncMock(
        return_value={"succeeded": [str(entry.id)], "failed": []}
    )
    users.require_owned_entry = AsyncMock(return_value=entry)
    users.rename_folder_entry = AsyncMock(return_value=entry)
    entries = AsyncMock()
    entries.list_entries_for_user = AsyncMock(return_value=[entry])

    client = _client(user_id, folders=folders, users=users, entries=entries)
    moved = client.post(
        "/users/entries/move",
        json={"entry_ids": [str(entry.id)], "library_folder_id": None},
    )
    assert moved.status_code == 200
    assert moved.json()["succeeded"] == [str(entry.id)]

    renamed = client.patch(
        f"/users/entries/{entry.id}", json={"name": "Asyncio - Apuntes"}
    )
    assert renamed.status_code == 200

    deleted = client.post("/users/entries/delete", json={"entry_ids": [str(entry.id)]})
    assert deleted.status_code == 200

    listed = client.get("/users/entries", params={"folder_id": "unfiled"})
    assert listed.status_code == 200
    entries.list_entries_for_user.assert_awaited()
    assert entries.list_entries_for_user.await_args.kwargs["folder_id"] == "unfiled"


def test_blank_folder_name_rejected() -> None:
    user_id = str(ObjectId())
    folders = AsyncMock()
    folders.create_folder = AsyncMock(
        side_effect=CodedHTTPException(400, ApiErrorCode.FOLDER_NAME_INVALID)
    )
    client = _client(user_id, folders=folders)
    response = client.post("/users/folders", json={"name": "   "})
    assert response.status_code == 400
    assert response.json()["code"] == ApiErrorCode.FOLDER_NAME_INVALID.value
