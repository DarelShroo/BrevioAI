from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.repositories import (
    folder_entry_repository as folder_entry_repository_module,
)
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository


class FakeFindQuery:
    def __init__(self, entries: List["FakeFolderEntryDocument"]) -> None:
        self._entries = entries

    async def to_list(self) -> List["FakeFolderEntryDocument"]:
        return self._entries


class FakeFolderEntryDocument:
    _storage: list["FakeFolderEntryDocument"] = []

    def __init__(
        self,
        id: ObjectId,
        user_id: Any,
        name: str = "",
        results: Optional[List[Any]] = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.name = name
        self.results = results or []

    async def insert(self) -> None:
        self.__class__._storage.append(self)

    @classmethod
    async def get(cls, object_id: ObjectId) -> Optional["FakeFolderEntryDocument"]:
        for entry in cls._storage:
            if entry.id == object_id:
                return entry
        return None

    @classmethod
    def find(cls, query: Dict[str, Any]) -> FakeFindQuery:
        filtered: List[FakeFolderEntryDocument] = []

        for entry in cls._storage:
            match = True
            for key, value in query.items():
                attr_name = "id" if key == "_id" else key
                entry_value = getattr(entry, attr_name, None)
                if isinstance(value, dict) and "$in" in value:
                    if entry_value not in value["$in"]:
                        match = False
                        break
                elif entry_value != value:
                    match = False
                    break

            if match:
                filtered.append(entry)

        return FakeFindQuery(filtered)

    async def update(self, update_data: Dict[str, Any]) -> None:
        set_data = update_data.get("$set", {})
        for key, value in set_data.items():
            setattr(self, key, value)

        push_data = update_data.get("$push", {})
        for key, value in push_data.items():
            current = getattr(self, key, [])
            if isinstance(value, dict) and "$each" in value:
                current.extend(value["$each"])
            else:
                current.append(value)
            setattr(self, key, current)

    async def delete(self) -> None:
        self.__class__._storage = [e for e in self.__class__._storage if e.id != self.id]


@pytest.fixture
def patch_folder_entry_document(
    monkeypatch: pytest.MonkeyPatch,
) -> type[FakeFolderEntryDocument]:
    FakeFolderEntryDocument._storage = []
    monkeypatch.setattr(
        folder_entry_repository_module,
        "FolderEntryDocument",
        FakeFolderEntryDocument,
    )
    return FakeFolderEntryDocument


@pytest.fixture
def folder_entry_repository(
    patch_folder_entry_document: type[FakeFolderEntryDocument],
) -> FolderEntryRepository:
    return FolderEntryRepository()


@pytest.fixture
def dummy_entry() -> FolderEntry:
    return FolderEntry(
        _id=ObjectId(),
        name="Test Entry",
        user_id=ObjectId(),
        results=[],
    )


@pytest.mark.asyncio
async def test_create_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    patch_folder_entry_document: type[FakeFolderEntryDocument],
    dummy_entry: FolderEntry,
) -> None:
    created = await folder_entry_repository.create_folder_entry(dummy_entry)

    assert created.id == dummy_entry.id
    assert created.user_id == dummy_entry.user_id
    assert len(patch_folder_entry_document._storage) == 1


@pytest.mark.asyncio
async def test_get_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
) -> None:
    entry_doc = FakeFolderEntryDocument(
        id=dummy_entry.id,
        user_id=dummy_entry.user_id,
        name=dummy_entry.name,
        results=dummy_entry.results,
    )
    await entry_doc.insert()

    retrieved = await folder_entry_repository.get_folder_entry_by_id(str(dummy_entry.id))

    assert retrieved.id == dummy_entry.id
    assert retrieved.user_id == dummy_entry.user_id


@pytest.mark.asyncio
async def test_get_folder_entry_not_found(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_folder_entry_by_id(str(ObjectId()))

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_folder_entry_invalid_id(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(ValueError) as exc:
        await folder_entry_repository.get_folder_entry_by_id("invalid_object_id")

    assert "Invalid entry ID format" in str(exc.value)


@pytest.mark.asyncio
async def test_update_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
) -> None:
    entry_doc = FakeFolderEntryDocument(
        id=dummy_entry.id,
        user_id=dummy_entry.user_id,
        name=dummy_entry.name,
        results=dummy_entry.results,
    )
    await entry_doc.insert()

    updated = await folder_entry_repository.update_folder_entry(
        str(dummy_entry.id),
        {"$set": {"name": "Updated Name"}},
    )

    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_folder_entry_with_plain_dict_autoset(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
) -> None:
    entry_doc = FakeFolderEntryDocument(
        id=dummy_entry.id,
        user_id=dummy_entry.user_id,
        name=dummy_entry.name,
        results=dummy_entry.results,
    )
    await entry_doc.insert()

    updated = await folder_entry_repository.update_folder_entry(
        str(dummy_entry.id),
        {"name": "Updated By Plain Dict"},
    )

    assert updated.name == "Updated By Plain Dict"


@pytest.mark.asyncio
async def test_update_folder_entry_not_found(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(RuntimeError) as exc:
        await folder_entry_repository.update_folder_entry(
            str(ObjectId()),
            {"$set": {"name": "No entry"}},
        )

    assert "Folder entry not found" in str(exc.value)


@pytest.mark.asyncio
async def test_delete_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    patch_folder_entry_document: type[FakeFolderEntryDocument],
    dummy_entry: FolderEntry,
) -> None:
    entry_doc = FakeFolderEntryDocument(
        id=dummy_entry.id,
        user_id=dummy_entry.user_id,
        name=dummy_entry.name,
        results=dummy_entry.results,
    )
    await entry_doc.insert()

    result = await folder_entry_repository.delete_folder_entry(str(dummy_entry.id))

    assert result == {"message": "FolderEntry eliminado exitosamente"}
    assert len(patch_folder_entry_document._storage) == 0


@pytest.mark.asyncio
async def test_delete_folder_entry_not_found(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(RuntimeError) as exc:
        await folder_entry_repository.delete_folder_entry(str(ObjectId()))

    assert "FolderEntry not found" in str(exc.value)


@pytest.mark.asyncio
async def test_get_entries_by_user_success(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
) -> None:
    entry_doc = FakeFolderEntryDocument(
        id=dummy_entry.id,
        user_id=dummy_entry.user_id,
        name=dummy_entry.name,
        results=dummy_entry.results,
    )
    await entry_doc.insert()

    entries = await folder_entry_repository.get_entries_by_user(str(dummy_entry.user_id))

    assert len(entries) == 1
    assert entries[0].id == dummy_entry.id


@pytest.mark.asyncio
async def test_create_entry_database_error(
    folder_entry_repository: FolderEntryRepository,
    patch_folder_entry_document: type[FakeFolderEntryDocument],
    dummy_entry: FolderEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_folder_entry_document,
        "insert",
        AsyncMock(side_effect=Exception("Simulated DB error")),
    )

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.create_folder_entry(dummy_entry)

    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_success(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    user_id = ObjectId()
    entry_1 = FakeFolderEntryDocument(id=ObjectId(), user_id=user_id, name="Entry 1")
    entry_2 = FakeFolderEntryDocument(id=ObjectId(), user_id=user_id, name="Entry 2")
    await entry_1.insert()
    await entry_2.insert()

    entries = await folder_entry_repository.get_entries_ids_by_user_id(
        str(user_id), [entry_1.id, entry_2.id]
    )

    assert len(entries) == 2
    assert {e.id for e in entries} == {entry_1.id, entry_2.id}


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_empty_list(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    user_id = ObjectId()
    entries = await folder_entry_repository.get_entries_ids_by_user_id(str(user_id), [])

    assert entries == []


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_db_error(
    folder_entry_repository: FolderEntryRepository,
    patch_folder_entry_document: type[FakeFolderEntryDocument],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_folder_entry_document,
        "find",
        lambda query: (_ for _ in ()).throw(Exception("Simulated DB error")),
    )

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(ObjectId()),
            [ObjectId()],
        )

    assert exc.value.status_code == 500
    assert "Simulated DB error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_validation_error(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    bad_entry = FakeFolderEntryDocument(
        id=ObjectId(),
        user_id="invalid_object_id",
        name="Bad Entry",
        results=[],
    )
    await bad_entry.insert()

    with pytest.raises(HTTPException) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(ObjectId()),
            [bad_entry.id],
        )

    assert exc.value.status_code == 422
    assert "Validation error" in exc.value.detail


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_invalid_user_id(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(ValueError) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id("invalid", [ObjectId()])

    assert "Invalid user ID format" in str(exc.value)


@pytest.mark.asyncio
async def test_get_entries_ids_by_user_id_invalid_refs(
    folder_entry_repository: FolderEntryRepository,
) -> None:
    with pytest.raises(ValueError) as exc:
        await folder_entry_repository.get_entries_ids_by_user_id(
            str(ObjectId()),
            [ObjectId(), "not_object_id"],  # type: ignore[list-item]
        )

    assert "Invalid ObjectId" in str(exc.value)
