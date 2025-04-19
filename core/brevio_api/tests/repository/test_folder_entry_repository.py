from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from core.brevio_api.core.database import Database
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository


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
        "core.brevio_api.repositories.folder_entry_repository.Database",
        return_value=mock_db,
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


def test_get_entries_ids_by_user_id_success(
    folder_entry_repository: FolderEntryRepository,
    folder_entry_data: dict,
    mock_db: MagicMock,
) -> None:
    """Should retrieve entries by IDs successfully."""
    # Setup test data
    user_id = ObjectId()
    entry_id1 = ObjectId()
    entry_id2 = ObjectId()
    entries_refs = [entry_id1, entry_id2]

    # Mock database response
    mock_db.__getitem__.return_value.find.return_value = [
        {**folder_entry_data, "_id": entry_id1, "user_id": user_id},
        {**folder_entry_data, "_id": entry_id2, "user_id": user_id},
    ]

    # Call the method
    entries = folder_entry_repository.get_entries_ids_by_user_id(user_id, entries_refs)

    # Assertions
    assert len(entries) == 2
    assert entries[0].id == entry_id1
    assert entries[1].id == entry_id2
    mock_db.__getitem__.return_value.find.assert_called_once()


def test_get_entries_ids_by_user_id_empty_list(
    folder_entry_repository: FolderEntryRepository,
    mock_db: MagicMock,
) -> None:
    """Should return empty list when no IDs are provided."""
    user_id = ObjectId()
    # Call with empty list
    entries = folder_entry_repository.get_entries_ids_by_user_id(user_id, [])

    # Assertions
    assert entries == []
    mock_db.__getitem__.return_value.find.assert_called_once()


def test_get_entries_ids_by_user_id_db_error(
    folder_entry_repository: FolderEntryRepository,
    mock_db: MagicMock,
) -> None:
    """Should raise HTTPException when a database error occurs."""
    # Setup test data
    user_id = ObjectId()
    entry_id = ObjectId()

    # Mock database error
    mock_db.__getitem__.return_value.find.side_effect = PyMongoError(
        "Simulated DB error"
    )

    # Assertions
    with pytest.raises(HTTPException) as exc:
        folder_entry_repository.get_entries_ids_by_user_id(user_id, [entry_id])
    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail


def test_get_entries_ids_by_user_id_unexpected_error(
    folder_entry_repository: FolderEntryRepository,
    mock_db: MagicMock,
) -> None:
    """Should handle unexpected errors gracefully."""
    # Setup test data
    user_id = ObjectId()
    entry_id = ObjectId()

    # Mock an unexpected error
    mock_db.__getitem__.return_value.find.side_effect = Exception("Unexpected error")

    # Assertions
    with pytest.raises(HTTPException) as exc:
        folder_entry_repository.get_entries_ids_by_user_id(user_id, [entry_id])
    assert exc.value.status_code == 500
    assert "Unexpected error" in exc.value.detail


def test_get_entries_ids_by_user_id_multiple_users(
    folder_entry_repository: FolderEntryRepository, mock_db: MagicMock
) -> None:
    """Should retrieve entries by user ID successfully for multiple entries."""
    # Setup test data
    user_id = ObjectId()
    entry_id1 = ObjectId()
    entry_id2 = ObjectId()

    # Mock database response
    mock_entries = [
        {"_id": entry_id1, "name": "Entry 1", "user_id": user_id},
        {"_id": entry_id2, "name": "Entry 2", "user_id": user_id},
    ]
    mock_db.__getitem__.return_value.find.return_value = mock_entries

    # Call the method
    entries = folder_entry_repository.get_entries_ids_by_user_id(
        user_id, [entry_id1, entry_id2]
    )

    # Assertions
    assert len(entries) == 2
    assert entries[0].user_id == user_id
    assert entries[1].user_id == user_id
    mock_db.__getitem__.return_value.find.assert_called_once_with(
        {"_id": {"$in": [entry_id1, entry_id2]}, "user_id": user_id}
    )


def test_get_entries_ids_by_user_id_validation_error(
    folder_entry_repository: FolderEntryRepository, mock_db: MagicMock
) -> None:
    """Should raise HTTPException when entry data contains an invalid user_id."""
    user_id = ObjectId()
    entry_id = ObjectId()

    # Mock invalid entry data (invalid user_id format)
    mock_db.__getitem__.return_value.find.return_value = [
        {
            "_id": entry_id,
            "user_id": "invalid_object_id",  # Not a valid ObjectId
            "name": "Test Entry",
            "results": [],
        }
    ]

    with pytest.raises(HTTPException) as exc:
        folder_entry_repository.get_entries_ids_by_user_id(user_id, [entry_id])
    assert exc.value.status_code == 400
    assert "Invalid folder entry data" in exc.value.detail


def test_get_entries_ids_by_user_id_no_valid_ids(
    folder_entry_repository: FolderEntryRepository, mock_db: MagicMock
) -> None:
    """Should return empty list when no entries are found."""
    user_id = ObjectId()
    entry_id1 = ObjectId()
    entry_id2 = ObjectId()

    # Mock empty response (no entries found)
    mock_db.__getitem__.return_value.find.return_value = []

    entries = folder_entry_repository.get_entries_ids_by_user_id(
        user_id, [entry_id1, entry_id2]
    )
    assert entries == []
    mock_db.__getitem__.return_value.find.assert_called_once()
