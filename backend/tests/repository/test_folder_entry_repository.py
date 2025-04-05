from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from core.database import Database
from models.user.folder_entry import FolderEntry
from repositories.folder_entry_repository import FolderEntryRepository


@pytest.fixture
def mock_db() -> MagicMock:
    # Create a mock database with a mock collection
    mock_db = MagicMock(spec=Database)
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection  # For db['entries'] access
    return mock_db


@pytest.fixture
def folder_entry_repository(mock_db: MagicMock) -> FolderEntryRepository:
    # Patch the database access in the repository
    with patch(
        "backend.repositories.folder_entry_repository.Database", return_value=mock_db
    ):
        return FolderEntryRepository(mock_db)


@pytest.fixture
def folder_entry_data() -> dict:
    return {
        "_id": ObjectId(),
        "name": "Test Folder",
        "path": "/test/path",
        "user_id": ObjectId(),
        "parent_id": ObjectId(),
    }


@pytest.fixture
def dummy_entry() -> FolderEntry:
    return FolderEntry(name="Test Entry", user_id=ObjectId())


def test_create_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
    mock_db: MagicMock,
) -> None:
    """Should create a FolderEntry successfully and return it with an assigned ID."""
    mock_result = MagicMock(spec=InsertOneResult)
    mock_result.inserted_id = ObjectId()
    mock_db.__getitem__.return_value.insert_one.return_value = mock_result

    result = folder_entry_repository.create_folder_entry(dummy_entry)

    assert isinstance(result.id, ObjectId)
    assert result.name == dummy_entry.name
    assert result.user_id == dummy_entry.user_id
    mock_db.__getitem__.return_value.insert_one.assert_called_once()


def test_get_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
    mock_db: MagicMock,
) -> None:
    """Should retrieve the correct FolderEntry by its ID."""
    entry_id = ObjectId()
    mock_db.__getitem__.return_value.find_one.return_value = {
        **folder_entry_data,
        "_id": entry_id,
    }

    retrieved = folder_entry_repository.get_folder_entry_by_id(entry_id)

    assert retrieved is not None
    assert retrieved.id == entry_id
    assert retrieved.name == folder_entry_data["name"]
    assert retrieved.user_id == folder_entry_data["user_id"]


def test_get_folder_entry_not_found(
    folder_entry_repository: FolderEntryRepository, mock_db: MagicMock
) -> None:
    """Should raise HTTPException with status 404 when FolderEntry is not found."""
    mock_db.__getitem__.return_value.find_one.return_value = None

    with pytest.raises(HTTPException) as exc:
        folder_entry_repository.get_folder_entry_by_id(ObjectId())
    assert exc.value.status_code == 404


def test_update_folder_entry_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
    mock_db: MagicMock,
) -> None:
    """Should update the FolderEntry successfully and return the updated entry."""
    entry_id = ObjectId()
    update_data = {"name": "Updated Name"}

    update_result = MagicMock(spec=UpdateResult)
    update_result.modified_count = 1
    mock_db.__getitem__.return_value.update_one.return_value = update_result
    mock_db.__getitem__.return_value.find_one.return_value = {
        **folder_entry_data,
        "_id": entry_id,
        "name": "Updated Name",
    }

    updated = folder_entry_repository.update_folder_entry(entry_id, update_data)

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.id == entry_id


def test_delete_folder_entry_success(
    folder_entry_repository: FolderEntryRepository, mock_db: MagicMock
) -> None:
    """Should delete the FolderEntry successfully and confirm deletion."""
    entry_id = ObjectId()
    delete_result = MagicMock(spec=DeleteResult)
    delete_result.deleted_count = 1
    mock_db.__getitem__.return_value.delete_one.return_value = delete_result

    result = folder_entry_repository.delete_folder_entry(entry_id)
    assert result["message"] == "FolderEntry eliminado exitosamente"
    mock_db.__getitem__.return_value.delete_one.assert_called_once()


def test_get_entries_by_user_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
    mock_db: MagicMock,
) -> None:
    """Should retrieve all FolderEntries for a specific user."""
    user_id = ObjectId()
    mock_db.__getitem__.return_value.find.return_value = [
        {**folder_entry_data, "user_id": user_id}
    ]

    entries = folder_entry_repository.get_entries_by_user(user_id)
    assert len(entries) == 1
    assert entries[0].user_id == user_id


def test_create_entry_database_error(
    folder_entry_repository: FolderEntryRepository,
    dummy_entry: FolderEntry,
    mock_db: MagicMock,
) -> None:
    """Should raise HTTPException with status 500 when a database error occurs during creation."""
    mock_db.__getitem__.return_value.insert_one.side_effect = PyMongoError(
        "Simulated DB error"
    )

    with pytest.raises(HTTPException) as exc:
        folder_entry_repository.create_folder_entry(dummy_entry)
    assert exc.value.status_code == 500
