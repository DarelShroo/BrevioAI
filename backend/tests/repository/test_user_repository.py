from typing import Any

import mongomock
import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import database
from pymongo.errors import PyMongoError

from backend.core import database as db_module
from backend.models.user.user_model import User
from backend.repositories.user_repository import UserRepository
from models.user.user_folder import UserFolder


# Fixtures
@pytest.fixture
def mock_db():
    """Provide a mock database for testing."""
    mock_client = mongomock.MongoClient()
    mock_db_name = "test_db"
    return mock_client[mock_db_name]  # Returns a mongomock.Database object


@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    return User(
        _id=ObjectId(),
        username="test_user",
        email="test@example.com",
        password="hashed_password",
        folder=UserFolder(_id=ObjectId(), entries=[]).model_dump(),
    )


@pytest.fixture
def user_repo(mock_db: db_module.Database) -> UserRepository:
    """Provide a UserRepository instance with a mock database."""
    return UserRepository(mock_db)


# Tests de Inicialización
def test_init_database_error(monkeypatch):
    """Should raise HTTPException when database initialization fails."""

    def mock_getitem(self, key):
        if key == "users":
            raise Exception("Database connection failed")
        return self._collections.get(key)

    monkeypatch.setattr("mongomock.database.Database.__getitem__", mock_getitem)
    with pytest.raises(HTTPException) as exc:
        UserRepository(mongomock.MongoClient()["test_db"])
    assert exc.value.status_code == 500
    assert "Database initialization error" in exc.value.detail


def test_init_success(mock_db: db_module.Database) -> None:
    """Should initialize UserRepository successfully with a valid database."""
    repo = UserRepository(mock_db)
    assert repo.collection.name == "users"


# Tests de Recuperación por ID (Adaptados a get_user_by_field)
def test_get_user_by_id_success(user_repo: UserRepository, sample_user: User) -> None:
    """Should retrieve a user by ID successfully using get_user_by_field."""
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = user_repo.get_user_by_field("_id", str(sample_user.id))
    assert result is not None
    assert result.id == sample_user.id
    assert result.username == sample_user.username
    assert result.email == sample_user.email


def test_get_user_by_id_not_found(user_repo: UserRepository) -> None:
    """Should return None when user is not found by ID using get_user_by_field."""
    result = user_repo.get_user_by_field("_id", str(ObjectId()))
    assert result is None


def test_get_user_by_id_invalid_id(user_repo: UserRepository) -> None:
    """Should raise HTTPException for invalid ID format using get_user_by_field."""
    with pytest.raises(HTTPException) as exc:
        user_repo.get_user_by_field("_id", "invalid_id")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid user ID format"


def test_get_user_by_id_database_error(
    user_repo: UserRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs using get_user_by_field."""

    def mock_find_one(*args: Any, **kwargs: Any) -> None:
        raise PyMongoError("Simulated database error")

    monkeypatch.setattr(user_repo.collection, "find_one", mock_find_one)
    with pytest.raises(HTTPException) as exc:
        user_repo.get_user_by_field("_id", str(ObjectId()))
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error while fetching user:")


# Tests de Recuperación por Campo
def test_get_user_by_field_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should retrieve a user by a specific field successfully."""
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    # Test con ObjectId para el campo _id
    result = user_repo.get_user_by_field("_id", sample_user.id)
    assert result is not None
    assert result.id == sample_user.id
    # Test con string para el campo email
    result = user_repo.get_user_by_field("email", sample_user.email)
    assert result is not None
    assert result.email == sample_user.email


def test_get_user_by_field_not_found(user_repo: UserRepository) -> None:
    """Should return None when no user is found by field."""
    result = user_repo.get_user_by_field("_id", str(ObjectId()))
    assert result is None
    result = user_repo.get_user_by_field("email", "nonexistent@example.com")
    assert result is None


def test_get_user_by_field_invalid_id(user_repo: UserRepository) -> None:
    """Should raise HTTPException for invalid ID format."""
    with pytest.raises(HTTPException) as exc:
        user_repo.get_user_by_field("_id", "invalid_id")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid user ID format"


def test_get_user_by_field_database_error(
    user_repo: UserRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during field retrieval."""

    def mock_find_one(*args: Any, **kwargs: Any) -> None:
        raise PyMongoError("Simulated database error")

    monkeypatch.setattr(user_repo.collection, "find_one", mock_find_one)
    with pytest.raises(HTTPException) as exc:
        user_repo.get_user_by_field("email", "test@example.com")
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error while fetching user:")


# Tests de Creación
def test_create_user_success(user_repo: UserRepository, sample_user: User) -> None:
    """Should create a user successfully and return it."""
    result = user_repo.create_user(sample_user)
    assert result is not None
    assert result.username == sample_user.username
    assert result.email == sample_user.email
    assert result.id is not None
    assert user_repo.collection.find_one({"email": sample_user.email}) is not None


def test_create_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during creation."""

    def mock_insert_one(*args: Any, **kwargs: Any) -> None:
        raise PyMongoError("Simulated database error")

    monkeypatch.setattr(user_repo.collection, "insert_one", mock_insert_one)
    with pytest.raises(HTTPException) as exc:
        user_repo.create_user(sample_user)
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


# Tests de Actualización
def test_update_user_success(user_repo: UserRepository, sample_user: User) -> None:
    """Should update a user successfully and return the updated user."""
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    updated_fields = {"username": "updated_user"}
    result = user_repo.update_user(sample_user.id, updated_fields)
    assert result is not None
    assert result.username == "updated_user"
    assert result.email == sample_user.email


def test_update_user_not_found(user_repo: UserRepository) -> None:
    """Should raise HTTPException when user to update is not found."""
    with pytest.raises(HTTPException) as exc:
        user_repo.update_user(ObjectId(), {"username": "updated"})
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


def test_user_model_invalid_id():
    """Should raise ValidationError for invalid ID format during User model creation."""
    with pytest.raises(ValidationError):
        User(
            id="invalid_id",
            username="testuser",
            email="test@example.com",
            password="hashed_password",
            folder=UserFolder(),
        )


def test_update_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during update."""

    def mock_update_one(*args: Any, **kwargs: Any) -> None:
        raise PyMongoError("Simulated database error")

    monkeypatch.setattr(user_repo.collection, "update_one", mock_update_one)
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    with pytest.raises(HTTPException) as exc:
        user_repo.update_user(sample_user.id, {"username": "updated"})
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


# Tests de Eliminación
def test_delete_user_success(user_repo: UserRepository, sample_user: User) -> None:
    """Should delete a user successfully."""
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = user_repo.delete_user(sample_user.id)
    assert result["message"] == "User deleted successfully"
    assert user_repo.collection.find_one({"_id": sample_user.id}) is None


def test_delete_user_not_found(user_repo: UserRepository) -> None:
    """Should handle user not found during deletion."""
    with pytest.raises(HTTPException) as exc:
        user_repo.delete_user(ObjectId())
    assert exc.value.status_code == 404


def test_delete_user_invalid_id(user_repo: UserRepository) -> None:
    """Should raise HTTPException for invalid ID format."""
    invalid_id = "invalid_object_id"
    with pytest.raises(HTTPException) as exc:
        user_repo.delete_user(invalid_id)
    assert exc.value.status_code == 400
    assert "Invalid user ID" in exc.value.detail


def test_delete_user_database_error(
    user_repo: UserRepository, sample_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should raise HTTPException when a database error occurs during deletion."""

    def mock_delete_one(*args: Any, **kwargs: Any) -> None:
        raise PyMongoError("Simulated database error")

    monkeypatch.setattr(user_repo.collection, "delete_one", mock_delete_one)
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    with pytest.raises(HTTPException) as exc:
        user_repo.delete_user(sample_user.id)
    assert exc.value.status_code == 500
    assert exc.value.detail.startswith("Database error:")


def test_delete_user_with_objectid_success(
    user_repo: UserRepository, sample_user: User
) -> None:
    """Should delete a user successfully when passing ObjectId directly."""
    user_repo.collection.insert_one(sample_user.model_dump(by_alias=True))
    result = user_repo.delete_user(sample_user.id)
    assert result == {"message": "User deleted successfully"}
    assert user_repo.collection.find_one({"_id": sample_user.id}) is None
