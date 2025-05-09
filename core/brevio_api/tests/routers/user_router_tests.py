from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import (  # ← Ajusta la ruta si tu app está en otro módulo
    app,
)
from core.brevio_api.dependencies.get_folder_entry_service_dependency import (
    get_folder_entry_service,
)
from core.brevio_api.dependencies.user_dependency import get_current_user


@pytest.mark.asyncio
async def test_get_user_entries() -> None:
    # 1. Preparamos el user_id y el servicio mockeado
    mock_user_id = ObjectId("507f1f77bcf86cd799439011")
    mock_service = AsyncMock()
    # Retornamos una lista con un dict que represente un FolderEntry válido
    mock_service.get_entries.return_value = [
        {
            "_id": ObjectId(),
            "user_id": mock_user_id,  #
            "name": "Test Entry",
            "results": [],
        }
    ]

    # 2. Sobrescribimos las dependencias para que no toquen la DB real
    app.dependency_overrides[get_current_user] = lambda: mock_user_id
    app.dependency_overrides[get_folder_entry_service] = lambda: mock_service

    # 3. Preparamos el payload con ObjectIds válidos
    entries_refs = [str(ObjectId()), str(ObjectId())]
    payload = {"entries_refs": entries_refs}

    # 4. Llamamos al endpoint
    client = TestClient(app)
    response = client.post("/users/entries", json=payload)

    # 5. Debug en caso de fallo
    if response.status_code != 200:
        print("Response status:", response.status_code)
        print("Response text:", response.text)

    # 6. Aserciones
    assert response.status_code == 200

    data = response.json()
    # Ahora esperamos un dict con key "entries"
    assert "entries" in data, "La respuesta debe contener la clave 'entries'"
    entries = data["entries"]
    assert isinstance(entries, list), "'entries' debe ser una lista"
    assert entries, "La lista 'entries' no debe estar vacía"

    first = entries[0]
    assert first["user_id"] == str(mock_user_id)
    assert first["name"] == "Test Entry"  # Verificamos el campo 'name'
    assert first["results"] == []

    # 7. Limpiamos los overrides para no afectar otros tests
    app.dependency_overrides.clear()
