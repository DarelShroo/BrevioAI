from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import (  # ← Ajusta la ruta si tu app está en otro módulo
    app,
)
from core.brevio_api.dependencies.folder_entry_service_dependency import (
    FolderEntryServiceDependency,
)
from core.brevio_api.dependencies.user_dependency import get_current_user


@pytest.mark.asyncio
async def test_get_user_entries() -> None:
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    mock_service.get_entries.return_value = [
        {
            "_id": ObjectId(),
            "user_id": mock_user_id,  #
            "name": "Test Entry",
            "results": [],
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: mock_user_id
    app.dependency_overrides[FolderEntryServiceDependency] = lambda: mock_service

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

    app.dependency_overrides.clear()
