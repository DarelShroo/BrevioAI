import tempfile
from pathlib import Path as FilePath
from typing import Any, Generator, Tuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import mongomock
import pytest
from bson import ObjectId
from fastapi import HTTPException

from core.brevio.enums.language import LanguageType
from core.brevio.enums.model import ModelType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.utils.password_utils import hash_password


@pytest.fixture(autouse=True)
def mock_mongodb_autouse() -> Generator[MagicMock, None, None]:
    """Fixture para simular la conexión a MongoDB usando mongomock."""
    mock_db = MagicMock()
    mock_db.client = mongomock.MongoClient()
    mock_db.db = mock_db.client.db
    mock_db.database.return_value = mock_db.db

    with patch(
        "core.brevio_api.core.database.MongoClient", new=mongomock.MongoClient
    ), patch(
        "core.brevio_api.core.database.DB._verify_connection", return_value=None
    ), patch(
        "core.brevio_api.core.database.DB.__new__", return_value=mock_db
    ):
        yield mock_db


@pytest.fixture
def mock_prompt_config() -> PromptConfig:
    """Fixture para proporcionar una configuración de prompt de prueba."""
    return PromptConfig(
        model=ModelType.GPT_4,
        category="education",
        style="quick_ref",
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.SPANISH,
        source_types=SourceType.TEXT,
    )


@pytest.fixture
def mock_user() -> User:
    """Fixture para crear un usuario simulado."""
    return User(
        _id=ObjectId(),
        username="testuser",
        email="test@example.com",
        password=hash_password("password"),
        folder=UserFolder(_id=ObjectId()),
    )


@pytest.fixture
def brevio_service(mock_user: User) -> Generator[BrevioService, None, None]:
    """Fixture para proporcionar una instancia de BrevioService con dependencias simuladas."""
    with patch("core.brevio_api.core.database.DB") as mock_db_class:
        mock_db_instance = MagicMock()
        mock_db_instance.database.return_value = mongomock.MongoClient().db
        mock_db_class.return_value = mock_db_instance

        service = BrevioService()

        # Mock Main instance methods
        mock_main = MagicMock()
        mock_main.generate = AsyncMock(return_value={"result": "success"})
        mock_main.generate_summary_documents = AsyncMock(
            return_value={"summary": "done"}
        )
        setattr(service, "_main", mock_main)

        # Mock user service methods
        service._user_service = MagicMock()
        service._user_service.create_folder_entry = MagicMock(return_value=ObjectId())
        service._user_service.get_user_by_id = MagicMock(return_value=mock_user)
        service._user_service.create_data_result = AsyncMock()

        yield service


@pytest.mark.asyncio
async def test_generate_success(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    """Test para verificar que generate devuelve el resultado esperado."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        data = BrevioGenerate(
            data=[MediaEntry(path=test_file_path)],
            prompt_config=mock_prompt_config,
        )

        with patch("pathlib.Path.is_file", return_value=True), patch(
            "os.makedirs", return_value=None
        ), patch("os.listdir", return_value=["test.mp3"]):
            result = await brevio_service.generate(data, mock_user.id)
            assert result == {"result": "success"}
            mock_generate: AsyncMock = cast(AsyncMock, brevio_service._main.generate)
            mock_generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_brevio_error(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    """Test para verificar que generate maneja errores de _main correctamente."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        data = BrevioGenerate(
            data=[MediaEntry(path=test_file_path)],
            prompt_config=mock_prompt_config,
        )

        mock_generate: AsyncMock = cast(AsyncMock, brevio_service._main.generate)
        mock_generate.side_effect = Exception("Generation failed")

        with patch("pathlib.Path.is_file", return_value=True), patch(
            "os.makedirs", return_value=None
        ), patch("os.listdir", return_value=["test.mp3"]):
            with pytest.raises(HTTPException) as exc_info:
                await brevio_service.generate(data, mock_user.id)
            assert exc_info.value.status_code == 500
            assert "Unexpected error during generation: Generation failed" in str(
                exc_info.value.detail
            )


@pytest.mark.asyncio
async def test_generate_summary_media_upload_success(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    """Test para verificar que generate_summary_media_upload funciona correctamente."""
    files_data: list[Tuple[str, bytes]] = [
        ("video1.mp4", b"content1"),
        ("audio1.mp3", b"content2"),
    ]

    with patch("core.brevio.constants.constants.Constants") as mock_constants, patch(
        "pathlib.Path.is_file", return_value=True
    ), patch("pathlib.Path.mkdir"), patch(
        "core.brevio_api.services.brevio_service.BrevioService._write_file"
    ) as mock_write_file, patch(
        "os.makedirs", return_value=None
    ), patch(
        "os.listdir", return_value=["video1.mp4", "audio1.mp3"]
    ):
        mock_constants.DESTINATION_FOLDER = FilePath("/mock/dir")
        mock_write_file.return_value = None

        result = await brevio_service.generate_summary_media_upload(
            files_data, mock_user.id, mock_prompt_config
        )
        assert result == {"result": "success"}
        assert mock_write_file.call_count == len(files_data)
        mock_generate: AsyncMock = cast(AsyncMock, brevio_service._main.generate)
        mock_generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_summary_documents_success(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    """Test para verificar que generate_summary_documents funciona correctamente."""
    files_data: list[Tuple[str, bytes]] = [
        ("doc1.pdf", b"content1"),
        ("doc2.pdf", b"content2"),
    ]

    with patch("core.brevio.constants.constants.Constants") as mock_constants, patch(
        "pathlib.Path.is_file", return_value=True
    ), patch("pathlib.Path.mkdir"), patch(
        "core.brevio_api.services.brevio_service.BrevioService._write_file"
    ) as mock_write_file, patch(
        "os.makedirs", return_value=None
    ), patch(
        "os.listdir", return_value=["doc1.pdf", "doc2.pdf"]
    ), patch(
        "builtins.open", create=True
    ):
        mock_constants.DESTINATION_FOLDER = FilePath("/mock/dir")
        mock_write_file.return_value = None

        result = await brevio_service.generate_summary_documents(
            files_data, mock_user.id, mock_prompt_config
        )
        assert result == {"summary": "done"}
        assert mock_write_file.call_count == len(files_data)
        mock_generate_summary: AsyncMock = cast(
            AsyncMock, brevio_service._main.generate_summary_documents
        )
        mock_generate_summary.assert_awaited_once()
