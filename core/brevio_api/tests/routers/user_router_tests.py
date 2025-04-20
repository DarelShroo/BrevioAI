from typing import Any, List

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.get_folder_entry_service_dependency import (
    get_folder_entry_service,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.user.folder_entry import FolderEntry


# Stub FolderEntryService para simular la respuesta de la base de datos
class StubFolderEntryService:
    def get_entries(
        self, _user_id: ObjectId, _entries_refs: List[str]
    ) -> List[FolderEntry] | List[None]:
        if _user_id == ObjectId("507f1f77bcf86cd799439011"):
            return [FolderEntry(name="test_entry")]
        return []


@pytest.fixture(scope="function")
def override_dependencies() -> Any:
    # Sobrescribir las dependencias para cada test
    app.dependency_overrides[get_current_user] = lambda: ObjectId(
        "507f1f77bcf86cd799439011"
    )
    app.dependency_overrides[
        get_folder_entry_service
    ] = lambda: StubFolderEntryService()
    yield
    # Limpiar las dependencias después de cada prueba
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_dependencies: Any) -> TestClient:
    return TestClient(app)


def test_get_user_entries_success(client: Any) -> None:
    payload = {"entries_refs": [str(ObjectId()), str(ObjectId())]}
    response = client.post("/users/entries", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("entries"), list)
    assert data["entries"][0].get("name") == "test_entry"
