import asyncio
import tempfile
from concurrent.futures import Future
from pathlib import Path as FilePath
from typing import List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import mongomock
import pytest
from bson import ObjectId

from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType
from backend.brevio.enums.output_format_type import OutputFormatType
from backend.brevio.enums.source_type import SourceType
from backend.brevio.models import PromptConfig
from backend.core.database import DB
from backend.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from backend.models.user import User
from backend.models.user.user_folder import UserFolder
from backend.services.brevio_service import BrevioService
from backend.utils.password_utils import hash_password

# Marcamos todos los tests como asyncio


# Fixture para evitar conexiones reales a MongoDB
@pytest.fixture(autouse=True)
def mock_mongodb():
    """
    Mock MongoDB connections for tests by patching MongoClient and DB class
    """
    with patch(
        "backend.core.database.MongoClient", new=mongomock.MongoClient
    ) as mock_client, patch(
        "backend.core.database.DB._verify_connection"
    ) as mock_verify:
        mock_verify.return_value = None
        mock_db = MagicMock()
        mock_db.client = mongomock.MongoClient()
        mock_db.db = mock_db.client.db
        mock_db.database.return_value = mock_db.db
        with patch("backend.core.database.DB.__new__", return_value=mock_db), patch(
            "backend.services.brevio_service.DB", return_value=mock_db
        ):
            yield mock_db


@pytest.fixture
def mock_prompt_config():
    return PromptConfig(
        model=ModelType.GPT_4.value,
        category="education",
        style="quick_ref",
        format=OutputFormatType.MARKDOWN.value,
        language=LanguageType.SPANISH.value,
        source_types=SourceType.TEXT.value,
    )


@pytest.fixture(scope="function")
def mock_user():
    return User(
        id=ObjectId(),
        email="test@example.com",
        username="testuser",
        password=hash_password("password"),
        folder=UserFolder(id=ObjectId()),
    )


@pytest.fixture
def brevio_service(mock_user):
    with patch("backend.core.database.DB") as mock_db_class, patch(
        "pathlib.Path.is_file", return_value=True  # Simulate file existence
    ):
        mock_db_instance = MagicMock()
        mock_db_instance.database.return_value = mongomock.MongoClient().db
        mock_db_class.return_value = mock_db_instance

        service = BrevioService()

        service._user_service = MagicMock()
        service._user_service.create_folder_entry = MagicMock(
            return_value=MagicMock(id=ObjectId(), user_id=mock_user.id)
        )
        service._user_service.get_user_by_id = MagicMock(return_value=mock_user)
        service._user_service.create_data_result = AsyncMock(return_value=None)

        service._brevio = MagicMock()
        service._brevio.generate = AsyncMock(return_value={"result": "success"})
        service._brevio.generate_summary_documents = AsyncMock(
            return_value={"summary": "done"}
        )

        # Mock executor to return a Future object
        def create_future(result):
            future = Future()
            future.set_result(result)
            return future

        service.executor = MagicMock()
        service.executor.run_in_executor = AsyncMock(
            side_effect=lambda _, func, *args: create_future(func(*args))
        )

        service.save_media = MagicMock(
            return_value=MediaEntry(path="/mock/path/file.mp3")
        )

        return service


@pytest.mark.asyncio
async def test_generate_success(brevio_service, mock_user, mock_prompt_config):
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        data = BrevioGenerate(
            id=ObjectId(),
            data=[MediaEntry(path=str(test_file_path))],
            prompt_config=mock_prompt_config.model_dump(),
            model=ModelType.GPT_4,
        )
        result = await brevio_service.generate(data, mock_user.id)
        assert result == {"result": "success"}
        brevio_service._brevio.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_brevio_error(brevio_service, mock_user, mock_prompt_config):
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        brevio_service._brevio.generate = AsyncMock(
            side_effect=Exception("Generation failed")
        )
        data = BrevioGenerate(
            id=ObjectId(),
            data=[MediaEntry(path=str(test_file_path))],
            prompt_config=mock_prompt_config.model_dump(),
            model=ModelType.GPT_4,
        )
        with pytest.raises(Exception) as exc:
            await brevio_service.generate(data, mock_user.id)
        assert str(exc.value) == "Generation failed"
        brevio_service._brevio.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_summary_media_upload_success(
    brevio_service, mock_user, mock_prompt_config
):
    files_data = [("video1.mp4", b"content1"), ("audio1.mp3", b"content2")]
    with patch("backend.services.brevio_service.Constants") as mock_constants, patch(
        "pathlib.Path.mkdir", return_value=None
    ), patch("pathlib.Path.is_file", return_value=True):
        mock_constants.DESTINATION_FOLDER = "/mock/dir"
        brevio_service._user_service.create_folder_entry = MagicMock(
            return_value=MagicMock(id=ObjectId())
        )
        brevio_service._user_service.get_user_by_id = MagicMock(return_value=mock_user)
        brevio_service.save_media = MagicMock(
            side_effect=[
                MediaEntry(path="/mock/dir/video1.mp4"),
                MediaEntry(path="/mock/dir/audio1.mp3"),
            ]
        )
        result = await brevio_service.generate_summary_media_upload(
            files_data, mock_user.id, mock_prompt_config
        )
        assert result == {"result": "success"}
        brevio_service._brevio.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_summary_documents_success(
    brevio_service, mock_user, mock_prompt_config
):
    files_data = [("doc1.pdf", b"content1"), ("doc2.pdf", b"content2")]
    with patch("backend.services.brevio_service.Constants") as mock_constants, patch(
        "pathlib.Path.is_file", return_value=True
    ), patch(
        "backend.services.brevio_service.DirectoryManager.read_pdf"
    ) as mock_read_pdf:
        mock_constants.DESTINATION_FOLDER = "/mock/dir"
        mock_read_pdf.return_value = ["Sample text"]
        brevio_service.save_media = MagicMock(
            side_effect=[
                MediaEntry(path="/mock/dir/doc1.pdf"),
                MediaEntry(path="/mock/dir/doc2.pdf"),
            ]
        )
        result = await brevio_service.generate_summary_documents(
            files_data, mock_user.id, mock_prompt_config
        )
        assert result == {"summary": "done"}
        brevio_service._brevio.generate_summary_documents.assert_awaited_once()
