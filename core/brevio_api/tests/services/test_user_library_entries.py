from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException, status

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.services.user_service import UserService


def _service() -> tuple[UserService, AsyncMock, AsyncMock]:
    users = AsyncMock()
    entries = AsyncMock()
    return UserService(users, entries), users, entries


@pytest.mark.asyncio
async def test_create_folder_entry_with_filename_and_folder() -> None:
    service, users, entries = _service()
    user = MagicMock()
    user.id = ObjectId()
    user.folder = MagicMock()
    user.folder.entries = []
    users.get_user_by_field = AsyncMock(return_value=user)
    created = FolderEntry(
        user_id=user.id,
        name="using-asyncio-python-understanding-asynchronous.pdf",
        original_name="using-asyncio-python-understanding-asynchronous.pdf",
    )
    stabilized = FolderEntry(
        id=created.id,
        user_id=user.id,
        name=f"Summary {str(created.id)[-6:]}",
        original_name="using-asyncio-python-understanding-asynchronous.pdf",
        library_folder_id=ObjectId(),
    )
    entries.create_folder_entry = AsyncMock(return_value=created)
    entries.update_folder_entry = AsyncMock(return_value=stabilized)
    users.update_user = AsyncMock(return_value=user)
    folder_id = ObjectId()

    result = await service.create_folder_entry(
        str(user.id),
        name="using-asyncio-python-understanding-asynchronous.pdf",
        original_name="using-asyncio-python-understanding-asynchronous.pdf",
        library_folder_id=folder_id,
        source_type="documents",
    )

    payload = entries.create_folder_entry.await_args.args[0]
    assert (
        payload.original_name == "using-asyncio-python-understanding-asynchronous.pdf"
    )
    assert str(payload.library_folder_id) == str(folder_id)
    entries.update_folder_entry.assert_awaited()
    set_fields = entries.update_folder_entry.await_args.args[1]["$set"]
    assert set_fields["name"] == f"Summary {str(created.id)[-6:]}"
    assert set_fields["name"] != "using-asyncio-python-understanding-asynchronous.pdf"
    assert result == str(created.id)


@pytest.mark.asyncio
async def test_create_folder_entry_keeps_custom_name() -> None:
    service, users, entries = _service()
    user = MagicMock()
    user.id = ObjectId()
    user.folder = MagicMock()
    user.folder.entries = []
    users.get_user_by_field = AsyncMock(return_value=user)
    created = FolderEntry(
        user_id=user.id,
        name="Mi carpeta",
        original_name="a.pdf; b.pdf",
    )
    entries.create_folder_entry = AsyncMock(return_value=created)
    entries.update_folder_entry = AsyncMock()
    users.update_user = AsyncMock(return_value=user)

    result = await service.create_folder_entry(
        str(user.id),
        name="Mi carpeta",
        original_name="a.pdf; b.pdf",
    )
    entries.update_folder_entry.assert_not_awaited()
    assert result == str(created.id)


@pytest.mark.asyncio
async def test_create_folder_entry_without_folder() -> None:
    service, users, entries = _service()
    user = MagicMock()
    user.id = ObjectId()
    user.folder = MagicMock()
    user.folder.entries = []
    users.get_user_by_field = AsyncMock(return_value=user)
    created = FolderEntry(
        user_id=user.id,
        name="notes.pdf",
        original_name="notes.pdf",
    )
    stabilized = FolderEntry(
        id=created.id,
        user_id=user.id,
        name=f"Summary {str(created.id)[-6:]}",
        original_name="notes.pdf",
    )
    entries.create_folder_entry = AsyncMock(return_value=created)
    entries.update_folder_entry = AsyncMock(return_value=stabilized)
    users.update_user = AsyncMock(return_value=user)

    await service.create_folder_entry(
        str(user.id),
        name="notes.pdf",
        original_name="notes.pdf",
    )
    payload = entries.create_folder_entry.await_args.args[0]
    assert payload.library_folder_id is None
    entries.update_folder_entry.assert_awaited()


@pytest.mark.asyncio
async def test_rename_move_and_unfile_entries() -> None:
    service, _users, entries = _service()
    user_id = str(ObjectId())
    entry = FolderEntry(user_id=ObjectId(user_id), name="old.pdf")
    entries.get_folder_entry_by_id = AsyncMock(return_value=entry)
    entries.update_folder_entry = AsyncMock(return_value=entry)
    entries.set_library_folder = AsyncMock(return_value=1)

    renamed = await service.rename_folder_entry(
        user_id, str(entry.id), "Asyncio - Apuntes"
    )
    assert renamed is entry
    set_fields = entries.update_folder_entry.await_args.args[1]["$set"]
    assert set_fields["name"] == "Asyncio - Apuntes"
    assert "original_name" not in set_fields

    folder_id = ObjectId()
    moved = await service.move_folder_entries(user_id, [str(entry.id)], folder_id)
    assert moved["succeeded"] == [str(entry.id)]
    entries.set_library_folder.assert_awaited()

    unfiled = await service.move_folder_entries(user_id, [str(entry.id)], None)
    assert unfiled["failed"] == []


@pytest.mark.asyncio
async def test_move_partial_missing_and_foreign_entry() -> None:
    service, _users, entries = _service()
    owner = ObjectId()
    other = ObjectId()
    owned = FolderEntry(user_id=owner, name="mine.pdf")
    foreign = FolderEntry(user_id=other, name="theirs.pdf")
    missing_id = str(ObjectId())

    async def fetch(entry_id: str) -> FolderEntry:
        if entry_id == str(owned.id):
            return owned
        if entry_id == str(foreign.id):
            return foreign
        raise HTTPException(status_code=404, detail="FolderEntry not found")

    entries.get_folder_entry_by_id = AsyncMock(side_effect=fetch)
    entries.set_library_folder = AsyncMock(return_value=1)

    result = await service.move_folder_entries(
        str(owner), [str(owned.id), str(foreign.id), missing_id], None
    )
    assert result["succeeded"] == [str(owned.id)]
    codes = {item["id"]: item["code"] for item in result["failed"]}
    assert codes[str(foreign.id)] == ApiErrorCode.ENTRY_FORBIDDEN.value
    assert codes[missing_id] == ApiErrorCode.ENTRY_NOT_FOUND.value


@pytest.mark.asyncio
async def test_bulk_delete_and_validation() -> None:
    service, users, entries = _service()
    user_id = str(ObjectId())
    entry = FolderEntry(user_id=ObjectId(user_id), name="gone.pdf")
    entries.get_folder_entry_by_id = AsyncMock(return_value=entry)
    users.get_user_by_field = AsyncMock(
        return_value=MagicMock(id=ObjectId(user_id), folder=None)
    )
    entries.delete_folder_entry = AsyncMock(return_value={"message": "ok"})

    deleted = await service.delete_folder_entries_for_user(user_id, [str(entry.id)])
    assert deleted["succeeded"] == [str(entry.id)]

    with pytest.raises(CodedHTTPException) as empty:
        await service.move_folder_entries(user_id, [], None)
    assert empty.value.code == ApiErrorCode.ENTRY_IDS_REQUIRED.value

    with pytest.raises(CodedHTTPException) as invalid:
        await service.rename_folder_entry(user_id, str(entry.id), "   ")
    assert invalid.value.code == ApiErrorCode.ENTRY_NAME_INVALID.value
