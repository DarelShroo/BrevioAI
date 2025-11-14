from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.user_repository import UserRepository


# Mock para AsyncIOMotorCollection
class MockAsyncCollection:
    def __init__(self) -> None:
        self._data: List[Dict[str, Any]] = []  # Simula documentos en la colección

    async def insert_one(self, document: Dict) -> Any:
        inserted_id = document.get("_id", ObjectId())
        document["_id"] = inserted_id
        self._data.append(document)
        mock_result = MagicMock()
        mock_result.inserted_id = inserted_id
        return mock_result

    async def find_one(self, query: Dict) -> Optional[Dict[str, Any]]:
        for doc in self._data:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                return doc.copy()
        return None

    async def update_one(self, query: Dict, update: Dict) -> Any:
        for doc in self._data:
            if all(doc.get(k) == v for k, v in query.items()):
                set_fields = update.get("$set", {})
                doc.update(set_fields)
                mock_result = MagicMock()
                mock_result.modified_count = 1
                return mock_result
        mock_result = MagicMock()
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


# Fixtures
@pytest.fixture
def mock_collection() -> MockAsyncCollection:
    """Provide a mock async collection for testing."""
    return MockAsyncCollection()


@pytest.fixture
def sample_user() -> User:
    """Provide a sample user for testing."""
    return User(
        _id=ObjectId(),
        username="test_user",
        email="test@example.com",
        password="hashed_password",
        folder=UserFolder(_id=ObjectId(), entries=[]),
    )


@pytest.fixture
def user_repo(mock_collection: AsyncIOMotorCollection) -> UserRepository:
    """Provide a UserRepository instance with a mock async collection."""
    return UserRepository(mock_collection)


def test_init_success(mock_collection: AsyncIOMotorCollection) -> None:
    """Should initialize UserRepository successfully with a valid collection."""
    repo = UserRepository(mock_collection)
    assert repo.collection is not None


# Tests de Recuperación por ID (Adaptados a get_user_by_field)
@pytest.mark.asyncio
async def test_get_user_by_id_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should retrieve a user by ID successfully using get_user_by_field."""
    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = await user_repo.get_user_by_field("_id", str(sample_user.id))
    assert result is not None
    assert result.id == sample_user.id
    assert result.username == sample_user.username
    assert result.email == sample_user.email


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_repo: UserRepository) -> None:
    """Should return None when user is not found by ID using get_user_by_field."""
    result = await user_repo.get_user_by_field("_id", str(ObjectId()))
    assert result is None


# Tests de Recuperación por Campo
@pytest.mark.asyncio
async def test_get_user_by_field_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should retrieve a user by a specific field successfully."""
    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    # Test con ObjectId para el campo _id
    result = await user_repo.get_user_by_field("_id", sample_user.id)
    assert result is not None
    assert result.id == sample_user.id
    # Test con string para el campo email
    result = await user_repo.get_user_by_field("email", sample_user.email)
    assert result is not None
    assert result.email == sample_user.email


@pytest.mark.asyncio
async def test_get_user_by_field_not_found(user_repo: UserRepository) -> None:
    """Should return None when no user is found by field."""
    result = await user_repo.get_user_by_field("_id", str(ObjectId()))
    assert result is None
    result = await user_repo.get_user_by_field("email", "nonexistent@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_database_error(
    user_repo: UserRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_find_one = AsyncMock(side_effect=PyMongoError("Simulated database error"))
    monkeypatch.setattr(user_repo.collection, "find_one", mock_find_one)

    with pytest.raises(HTTPException) as exc:
        await user_repo.get_user_by_field("_id", str(ObjectId()))
    assert exc.value.status_code == 500
    assert exc.value.detail == "Database error while fetching user"


@pytest.mark.asyncio
async def test_get_user_by_field_database_error(
    user_repo: UserRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during field retrieval."""
    mock_find_one = AsyncMock(side_effect=PyMongoError("Simulated database error"))
    monkeypatch.setattr(user_repo.collection, "find_one", mock_find_one)

    with pytest.raises(HTTPException) as exc:
        await user_repo.get_user_by_field("email", "test@example.com")
    assert exc.value.status_code == 500
    assert exc.value.detail == "Database error while fetching user"


# Tests de Creación
@pytest.mark.asyncio
async def test_create_user_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should create a user successfully and return it."""
    result = await user_repo.create_user(sample_user)
    assert result is not None
    assert result.username == sample_user.username
    assert result.email == sample_user.email
    assert result.id is not None

    # Verificar que está en la "base de datos"
    found = await user_repo.collection.find_one({"email": sample_user.email})
    assert found is not None


@pytest.mark.asyncio
async def test_create_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during creation."""
    mock_insert_one = AsyncMock(side_effect=PyMongoError("Simulated database error"))
    monkeypatch.setattr(user_repo.collection, "insert_one", mock_insert_one)

    with pytest.raises(HTTPException) as exc:
        await user_repo.create_user(sample_user)
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


# Tests de Actualización
@pytest.mark.asyncio
async def test_update_user_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should update a user successfully and return the updated user."""
    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    updated_fields = {"username": "updated_user"}
    result = await user_repo.update_user(sample_user.id, updated_fields)
    assert result is not None
    assert result.username == "updated_user"
    assert result.email == sample_user.email


@pytest.mark.asyncio
async def test_update_user_not_found(user_repo: UserRepository) -> None:
    """Should raise HTTPException when user to update is not found."""
    with pytest.raises(HTTPException) as exc:
        await user_repo.update_user(ObjectId(), {"username": "updated"})
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_update_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during update."""
    mock_update_one = AsyncMock(side_effect=PyMongoError("Simulated database error"))
    monkeypatch.setattr(user_repo.collection, "update_one", mock_update_one)

    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))

    with pytest.raises(HTTPException) as exc:
        await user_repo.update_user(sample_user.id, {"username": "updated"})
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


# Tests de Eliminación
@pytest.mark.asyncio
async def test_delete_user_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should delete a user successfully."""
    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = await user_repo.delete_user(sample_user.id)
    assert result["message"] == "User deleted successfully"

    found = await user_repo.collection.find_one({"_id": sample_user.id})
    assert found is None


@pytest.mark.asyncio
async def test_delete_user_not_found(user_repo: UserRepository) -> None:
    """Should handle user not found during deletion."""
    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user(ObjectId())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_invalid_id(user_repo: UserRepository) -> None:
    """Should raise HTTPException for invalid ID format."""
    invalid_id = "invalid_object_id"
    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user(invalid_id)
    assert exc.value.status_code == 400
    assert "Invalid user ID" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during deletion."""
    mock_delete_one = AsyncMock(side_effect=PyMongoError("Simulated database error"))
    monkeypatch.setattr(user_repo.collection, "delete_one", mock_delete_one)

    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))

    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user(sample_user.id)
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


@pytest.mark.asyncio
async def test_delete_user_with_objectid_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should delete a user successfully when passing ObjectId directly."""
    await user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = await user_repo.delete_user(sample_user.id)
    assert result == {"message": "User deleted successfully"}
    found = await user_repo.collection.find_one({"_id": sample_user.id})
    assert found is None
