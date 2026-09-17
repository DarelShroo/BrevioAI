from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import status

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.models.user.library_folder import LibraryFolder
from core.brevio_api.services.library_folder_service import LibraryFolderService
from core.shared.utils.source_names import (
    NameValidationError,
    names_for_batch,
    names_for_source,
    require_editable_name,
)


def test_names_for_source_keeps_real_pdf_filename() -> None:
    display, original = names_for_source(
        "uploads/0/using-asyncio-python-understanding-asynchronous.pdf",
        0,
        kind="document",
    )
    assert display == "using-asyncio-python-understanding-asynchronous.pdf"
    assert original == "using-asyncio-python-understanding-asynchronous.pdf"
    assert display != "Document 0"
    assert display != "Documento 0"


def test_names_for_source_generic_fallback() -> None:
    display, original = names_for_source("", 2, kind="document")
    assert display == "Document 2"
    assert original == "Document 2"


def test_names_for_batch_single_file() -> None:
    display, original = names_for_batch(["notes.pdf"], kind="document")
    assert display == ""
    assert original == "notes.pdf"


def test_names_for_batch_multiple_files() -> None:
    display, original = names_for_batch(
        ["alpha.pdf", "beta.docx", "gamma.pdf"],
        kind="document",
    )
    assert display == ""
    assert original == "alpha.pdf; beta.docx; gamma.pdf"


def test_names_for_batch_respects_explicit_entry_name() -> None:
    display, original = names_for_batch(
        ["alpha.pdf", "beta.pdf"],
        kind="document",
        entry_name="Mi carpeta",
    )
    assert display == "Mi carpeta"
    assert original == "alpha.pdf; beta.pdf"


def test_names_for_batch_empty_falls_back() -> None:
    display, original = names_for_batch([], kind="document")
    assert display == ""
    assert original == ""


def test_resolve_entry_display_name_prefers_custom_name() -> None:
    from core.shared.utils.source_names import resolve_entry_display_name

    assert (
        resolve_entry_display_name(
            entry_id="abcdef123456",
            name="Mi carpeta",
            results=[{"name": "a.pdf"}, {"name": "b.pdf"}],
        )
        == "Mi carpeta"
    )


def test_resolve_entry_display_name_ignores_first_file() -> None:
    from core.shared.utils.source_names import (
        resolve_entry_display_name,
        stable_entry_name,
    )

    assert resolve_entry_display_name(
        entry_id="abcdef123456",
        name="a.pdf (+1)",
        original_name="a.pdf; b.pdf",
        results=[{"name": "a.pdf"}, {"name": "b.pdf"}],
    ) == stable_entry_name("abcdef123456")


def test_require_editable_name_rejects_too_long() -> None:
    with pytest.raises(NameValidationError) as exc:
        require_editable_name("n" * 256, code_empty="EMPTY", code_too_long="LONG")
    assert exc.value.code == "LONG"


@pytest.fixture
def folder_service() -> tuple[LibraryFolderService, AsyncMock, AsyncMock]:
    folders = AsyncMock()
    entries = AsyncMock()
    folders.ensure_indexes = AsyncMock()
    entries.ensure_indexes = AsyncMock()
    return LibraryFolderService(folders, entries), folders, entries


@pytest.mark.asyncio
async def test_create_and_list_folders(
    folder_service: tuple[LibraryFolderService, AsyncMock, AsyncMock],
) -> None:
    service, folders, entries = folder_service
    user_id = str(ObjectId())
    created = LibraryFolder(
        user_id=ObjectId(user_id), name="Mis apuntes", name_key="mis apuntes"
    )
    folders.create = AsyncMock(return_value=created)
    folders.list_for_user = AsyncMock(return_value=[created])
    entries.count_by_library_folders = AsyncMock(
        return_value={"unfiled": 2, str(created.id): 1}
    )

    result = await service.create_folder(user_id, "Mis apuntes")
    listed = await service.list_folders(user_id)
    unfiled = await service.unfiled_count(user_id)

    assert result.name == "Mis apuntes"
    assert listed[0]["entry_count"] == 1
    assert unfiled == 2


@pytest.mark.asyncio
async def test_rename_and_delete_unfiles_entries(
    folder_service: tuple[LibraryFolderService, AsyncMock, AsyncMock],
) -> None:
    service, folders, entries = folder_service
    user_id = str(ObjectId())
    folder = LibraryFolder(user_id=ObjectId(user_id), name="A", name_key="a")
    folders.get_by_id = AsyncMock(return_value=folder)
    folders.rename = AsyncMock(
        return_value=LibraryFolder(
            id=folder.id, user_id=folder.user_id, name="B", name_key="b"
        )
    )
    folders.delete = AsyncMock(return_value=True)
    entries.clear_library_folder = AsyncMock(return_value=3)

    renamed = await service.rename_folder(user_id, str(folder.id), "B")
    await service.delete_folder(user_id, str(folder.id))

    assert renamed.name == "B"
    entries.clear_library_folder.assert_awaited_once_with(user_id, str(folder.id))
    folders.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_folder_isolation_and_missing(
    folder_service: tuple[LibraryFolderService, AsyncMock, AsyncMock],
) -> None:
    service, folders, _entries = folder_service
    owner = ObjectId()
    other = ObjectId()
    folder = LibraryFolder(user_id=owner, name="Privada", name_key="privada")
    folders.get_by_id = AsyncMock(return_value=folder)

    with pytest.raises(CodedHTTPException) as forbidden:
        await service.require_owned_folder(str(other), str(folder.id))
    assert forbidden.value.status_code == status.HTTP_404_NOT_FOUND
    assert forbidden.value.code == ApiErrorCode.FOLDER_NOT_FOUND.value

    folders.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(CodedHTTPException) as missing:
        await service.require_owned_folder(str(owner), str(ObjectId()))
    assert missing.value.status_code == status.HTTP_404_NOT_FOUND
    assert missing.value.code == ApiErrorCode.FOLDER_NOT_FOUND.value


@pytest.mark.asyncio
async def test_duplicate_folder_name(
    folder_service: tuple[LibraryFolderService, AsyncMock, AsyncMock],
) -> None:
    service, folders, _entries = folder_service
    folders.create = AsyncMock(side_effect=ValueError("duplicate"))
    with pytest.raises(CodedHTTPException) as exc:
        await service.create_folder(str(ObjectId()), "Notes")
    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.code == ApiErrorCode.FOLDER_NAME_DUPLICATE.value
