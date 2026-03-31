from typing import Any, Dict, Optional
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories import user_repository as user_repository_module
from core.brevio_api.repositories.user_repository import UserRepository


class FakeUserDocument:
    _storage: list["FakeUserDocument"] = []

    def __init__(
        self,
        id: ObjectId,
        username: str,
        email: str,
        password: str,
        user_credit: float = 0,
        folder: Optional[UserFolder] = None,
        otp: Optional[int] = None,
        exp: Optional[int] = None,
    ) -> None:
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.user_credit = user_credit
        self.folder = folder
        self.otp = otp
        self.exp = exp

    @classmethod
    async def find_one(cls, query: Dict[str, Any]) -> Optional["FakeUserDocument"]:
        for doc in cls._storage:
            if all(getattr(doc, "id" if k == "_id" else k, None) == v for k, v in query.items()):
                return doc
        return None

    async def insert(self) -> None:
        self.__class__._storage.append(self)

    async def update(self, update_data: Dict[str, Any]) -> None:
        set_fields = update_data.get("$set", {})
        for key, value in set_fields.items():
            if key == "folder.entries":
                if self.folder is None:
                    self.folder = UserFolder(_id=ObjectId(), entries=[])
                self.folder.entries = value
                continue
            setattr(self, key, value)

    async def delete(self) -> None:
        self.__class__._storage = [d for d in self.__class__._storage if d.id != self.id]


@pytest.fixture
def patch_user_document(monkeypatch: pytest.MonkeyPatch) -> type[FakeUserDocument]:
    FakeUserDocument._storage = []
    monkeypatch.setattr(user_repository_module, "UserDocument", FakeUserDocument)
    return FakeUserDocument


@pytest.fixture
def user_repo(patch_user_document: type[FakeUserDocument]) -> UserRepository:
    return UserRepository()


@pytest.fixture
def sample_user() -> User:
    return User(
        _id=ObjectId(),
        username="test_user",
        email="test@example.com",
        password="hashed_password",
        folder=UserFolder(_id=ObjectId(), entries=[]),
    )


def test_init_success(user_repo: UserRepository) -> None:
    assert user_repo.collection is None


@pytest.mark.asyncio
async def test_get_user_by_id_success(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    sample_user: User,
) -> None:
    await FakeUserDocument(
        id=sample_user.id,
        username=sample_user.username,
        email=str(sample_user.email),
        password=sample_user.password,
        folder=sample_user.folder,
        otp=sample_user.otp,
        exp=sample_user.exp,
        user_credit=sample_user.user_credit,
    ).insert()

    result = await user_repo.get_user_by_field("_id", str(sample_user.id))

    assert result is not None
    assert result.id == sample_user.id
    assert result.username == sample_user.username


@pytest.mark.asyncio
async def test_get_user_by_field_not_found(user_repo: UserRepository) -> None:
    result = await user_repo.get_user_by_field("email", "missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_field_invalid_id(user_repo: UserRepository) -> None:
    with pytest.raises(HTTPException) as exc:
        await user_repo.get_user_by_field("_id", "invalid_object_id")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid ID format"


@pytest.mark.asyncio
async def test_get_user_by_field_database_error(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_user_document,
        "find_one",
        AsyncMock(side_effect=PyMongoError("Simulated database error")),
    )

    with pytest.raises(HTTPException) as exc:
        await user_repo.get_user_by_field("email", "test@example.com")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Database error while fetching user"


@pytest.mark.asyncio
async def test_create_user_success(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    sample_user: User,
) -> None:
    created = await user_repo.create_user(sample_user)

    assert created.id == sample_user.id
    assert created.email == sample_user.email
    assert len(patch_user_document._storage) == 1


@pytest.mark.asyncio
async def test_create_user_database_error(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    sample_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_user_document,
        "insert",
        AsyncMock(side_effect=PyMongoError("insert failure")),
    )

    with pytest.raises(HTTPException) as exc:
        await user_repo.create_user(sample_user)

    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_success(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    sample_user: User,
) -> None:
    doc = FakeUserDocument(
        id=sample_user.id,
        username=sample_user.username,
        email=str(sample_user.email),
        password=sample_user.password,
        folder=sample_user.folder,
        otp=sample_user.otp,
        exp=sample_user.exp,
        user_credit=sample_user.user_credit,
    )
    await doc.insert()

    updated = await user_repo.update_user(sample_user.id, {"username": "updated_user"})

    assert updated is not None
    assert updated.username == "updated_user"


@pytest.mark.asyncio
async def test_update_user_with_nested_folder_entries(
    user_repo: UserRepository,
    sample_user: User,
) -> None:
    doc = FakeUserDocument(
        id=sample_user.id,
        username=sample_user.username,
        email=str(sample_user.email),
        password=sample_user.password,
        folder=sample_user.folder,
        otp=sample_user.otp,
        exp=sample_user.exp,
        user_credit=sample_user.user_credit,
    )
    await doc.insert()

    new_entries = [ObjectId(), ObjectId()]
    updated = await user_repo.update_user(sample_user.id, {"folder.entries": new_entries})

    assert updated is not None
    assert updated.folder is not None
    assert updated.folder.entries == new_entries


@pytest.mark.asyncio
async def test_update_user_not_found(user_repo: UserRepository) -> None:
    with pytest.raises(HTTPException) as exc:
        await user_repo.update_user(ObjectId(), {"username": "updated"})

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_update_user_invalid_object_id_field(
    user_repo: UserRepository,
    sample_user: User,
) -> None:
    doc = FakeUserDocument(
        id=sample_user.id,
        username=sample_user.username,
        email=str(sample_user.email),
        password=sample_user.password,
        folder=sample_user.folder,
        otp=sample_user.otp,
        exp=sample_user.exp,
        user_credit=sample_user.user_credit,
    )
    await doc.insert()

    with pytest.raises(HTTPException) as exc:
        await user_repo.update_user(sample_user.id, {"folder_id": "not_an_object_id"})

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid ID format"


@pytest.mark.asyncio
async def test_update_user_database_error(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_user_document,
        "find_one",
        AsyncMock(side_effect=PyMongoError("find failure")),
    )

    with pytest.raises(HTTPException) as exc:
        await user_repo.update_user(ObjectId(), {"username": "updated"})

    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_user_success(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    sample_user: User,
) -> None:
    doc = FakeUserDocument(
        id=sample_user.id,
        username=sample_user.username,
        email=str(sample_user.email),
        password=sample_user.password,
        folder=sample_user.folder,
        otp=sample_user.otp,
        exp=sample_user.exp,
        user_credit=sample_user.user_credit,
    )
    await doc.insert()

    result = await user_repo.delete_user(sample_user.id)

    assert result == {"message": "User deleted successfully"}
    assert len(patch_user_document._storage) == 0


@pytest.mark.asyncio
async def test_delete_user_not_found(user_repo: UserRepository) -> None:
    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user(ObjectId())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_invalid_id(user_repo: UserRepository) -> None:
    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user("invalid_object_id")
    assert exc.value.status_code == 400
    assert "Invalid user ID" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_user_database_error(
    user_repo: UserRepository,
    patch_user_document: type[FakeUserDocument],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch_user_document,
        "find_one",
        AsyncMock(side_effect=PyMongoError("delete failure")),
    )

    with pytest.raises(HTTPException) as exc:
        await user_repo.delete_user(ObjectId())

    assert exc.value.status_code == 500
    assert "Database error" in exc.value.detail
