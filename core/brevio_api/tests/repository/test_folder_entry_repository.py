from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository


# Mock para AsyncIOMotorCollection
class MockAsyncCollection:
    def __init__(self) -> None:
        self._data: List[Dict[str, Any]] = []  # Simula documentos en la colección

    async def insert_one(self, document: Dict) -> Any:
        inserted_id = document.get("_id", ObjectId())
        document["_id"] = inserted_id
        self._data.append(document.copy())
        mock_result = MagicMock()
        mock_result.inserted_id = inserted_id
        return mock_result

    async def find_one(self, query: Dict) -> Dict | None:
        for doc in self._data:
            match = True
            for k, v in query.items():
                if isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc.copy()
        return None

    def find(self, query: Dict) -> "MockAsyncCursor":
        results: List[Dict[str, Any]] = []
        for doc in self._data:
            match = True
            for k, v in query.items():
                if isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(doc.copy())
        return MockAsyncCursor(results)

    async def update_one(self, query: Dict, update: Dict) -> Any:
        for doc in self._data:
            if all(doc.get(k) == v for k, v in query.items()):
                set_fields = update.get("$set", {})
                doc.update(set_fields)
                mock_result = MagicMock()
                mock_result.matched_count = 1
                mock_result.modified_count = 1
                return mock_result
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_result.modified_count = 0
        return mock_result

    async def delete_one(self, query: Dict) -> Any:
        for i, doc in enumerate(self._data):
            if all(doc.get(k) == v for k, v in query.items()):
                del self._data[i]
                mock_result = MagicMock()
                mock_result.deleted_count = 1
                return mock_result
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        return mock_result


class MockAsyncCursor:
    def __init__(self, results: List[Dict[str, Any]]) -> None:
        self._results = results

    async def to_list(self, length: int | None = None) -> List[Dict[str, Any]]:
        return self._results


# Fixtures
@pytest.fixture
def mock_collection() -> MockAsyncCollection:
    """Provide a mock async collection for testing."""
    return MockAsyncCollection()


@pytest.fixture
def folder_entry_repository(
    mock_collection: MockAsyncCollection,
) -> FolderEntryRepository:
    """Provide a FolderEntryRepository instance with a mock async collection."""
    return FolderEntryRepository(mock_collection)  # type: ignore


@pytest.fixture
def folder_entry_data() -> dict:
    return {
        "_id": ObjectId(),
        "name": "Test Folder",
        "path": "/test/path",
        "user_id": ObjectId(),
        "parent_id": ObjectId(),
        "results": [],
    }


@pytest.fixture
def dummy_entry() -> FolderEntry:
    entry_id = ObjectId()
    user_id = ObjectId()
    return FolderEntry(
        _id=entry_id,
        name="Test Entry",
        user_id=user_id,
        results=[],
    )


# Tests
@pytest.mark.asyncio
async def test_create_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
) -> None:
    """Should create a FolderEntry successfully and return it with an assigned ID."""
    result = await folder_entry_repository.create_folder_entry(dummy_entry)

    assert isinstance(result.id, ObjectId)
    assert result.name == dummy_entry.name
    assert result.user_id == dummy_entry.user_id


@pytest.mark.asyncio
async def test_get_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
) -> None:
    """Should retrieve the correct FolderEntry by its ID."""
    # Insertar dato primero
    await folder_entry_repository.collection.insert_one(folder_entry_data)
    entry_id = folder_entry_data["_id"]

    retrieved = await folder_entry_repository.get_folder_entry_by_id(str(entry_id))

    assert retrieved is not None
    assert retrieved.id == entry_id
    assert retrieved.name == folder_entry_data["name"]
    assert retrieved.user_id == folder_entry_data["user_id"]


@pytest.mark.asyncio
async def test_get_folder_entry_not_found(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    """Should raise HTTPException with status 404 when FolderEntry is not found."""
    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_folder_entry_by_id(str(ObjectId()))
    assert exc.value.status_code == 404
    assert "not found" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_update_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
) -> None:
    """Should update the FolderEntry successfully and return the updated entry."""
    await folder_entry_repository.collection.insert_one(folder_entry_data)
    entry_id = folder_entry_data["_id"]
    update_data = {"$set": {"name": "Updated Name"}}

    updated = await folder_entry_repository.update_folder_entry(
        str(entry_id), update_data
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.id == entry_id


@pytest.mark.asyncio
async def test_delete_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
) -> None:
    """Should delete the FolderEntry successfully and confirm deletion."""
    await folder_entry_repository.collection.insert_one(folder_entry_data)
    entry_id = folder_entry_data["_id"]

    result = await folder_entry_repository.delete_folder_entry(str(entry_id))
    assert result["message"] == "FolderEntry eliminado exitosamente"

    # Verificar que ya no existe
    found = await folder_entry_repository.collection.find_one({"_id": entry_id})
    assert found is None


@pytest.mark.asyncio
async def test_get_entries_by_user_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
) -> None:
    """Should retrieve all FolderEntries for a specific user."""
    user_id = folder_entry_data["user_id"]
    await folder_entry_repository.collection.insert_one(folder_entry_data)

    entries = await folder_entry_repository.get_entries_by_user(str(user_id))
    assert len(entries) == 1
    assert entries[0].user_id == user_id


@pytest.mark.asyncio
async def test_create_entry_database_error(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should raise HTTPException with status 500 when a database error occurs during creation."""
    mock_insert_one = AsyncMock(side_effect=Exception("Simulated DB error"))
    monkeypatch.setattr(
        folder_entry_repository.collection, "insert_one", mock_insert_one
    )

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.create_folder_entry(dummy_entry)
    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
) -> None:
    """Should retrieve entries by IDs successfully."""
    user_id = folder_entry_data["user_id"]
    entry_id1 = ObjectId()
    entry_id2 = ObjectId()

    # Insertar datos
    doc1 = {**folder_entry_data, "_id": entry_id1}
    doc2 = {**folder_entry_data, "_id": entry_id2, "name": "Entry 2"}
    await folder_entry_repository.collection.insert_one(doc1)
    await folder_entry_repository.collection.insert_one(doc2)

    entries = await folder_entry_repository.get_entries_ids_by_user_id(
        str(user_id), [entry_id1, entry_id2]
    )

    assert len(entries) == 2
    assert entries[0].id == entry_id1 or entries[1].id == entry_id1
    assert entries[0].id == entry_id2 or entries[1].id == entry_id2


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_empty_list(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    """Should return empty list when no IDs are provided."""
    user_id = ObjectId()
    entries = await folder_entry_repository.get_entries_ids_by_user_id(str(user_id), [])
    assert entries == []


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_db_error(
    folder_entry_repository: FolderEntryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should raise HTTPException when a database error occurs."""
    user_id = ObjectId()
    entry_id = ObjectId()

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Simulated DB error"))
    monkeypatch.setattr(
        folder_entry_repository.collection, "find", MagicMock(return_value=mock_cursor)
    )

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(user_id), [entry_id]
        )
    assert exc.value.status_code == 500
    assert "Simulated DB error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_unexpected_error(
    folder_entry_repository: FolderEntryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should handle unexpected errors gracefully."""
    user_id = ObjectId()
    entry_id = ObjectId()

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(side_effect=Exception("Unexpected error"))
    monkeypatch.setattr(
        folder_entry_repository.collection, "find", MagicMock(return_value=mock_cursor)
    )

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(user_id), [entry_id]
        )
    assert exc.value.status_code == 500
    assert "Unexpected error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_validation_error(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    """Should raise HTTPException when entry data contains an invalid user_id."""
    user_id = ObjectId()
    entry_id = ObjectId()

    # Insertar dato inválido
    invalid_doc = {
        "_id": entry_id,
        "name": "Invalid Entry",
        "user_id": "invalid_object_id",  # ¡Inválido!
        "results": [],
    }
    await folder_entry_repository.collection.insert_one(invalid_doc)

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(user_id), [entry_id]
        )
    assert exc.value.status_code == 422  # Pydantic Validation -> 422
    assert "validation error" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_no_valid_ids(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    """Should return empty list when no entries are found."""
    user_id = ObjectId()
    entry_id1 = ObjectId()
    entry_id2 = ObjectId()

    entries = await folder_entry_repository.get_entries_ids_by_user_id(
        str(user_id), [entry_id1, entry_id2]
    )
    assert entries == []
