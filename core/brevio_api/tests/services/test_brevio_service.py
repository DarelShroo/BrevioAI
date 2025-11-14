import tempfile
from pathlib import Path as FilePath
from typing import Generator, Tuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import HttpUrl

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker
from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.services.user_service import UserService
from core.brevio_api.utils.password_utils import hash_password
from core.shared.enums.model import ModelType
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry

usage_cost_tracker = UsageCostTracker()


@pytest.fixture
def mock_prompt_config() -> PromptConfig:
    return PromptConfig(
        model=ModelType.GPT_4,
        category="education",
        style="quick_ref",
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.SPANISH,
        summary_level=SummaryLevel.CONCISE,
    )


@pytest.fixture
def mock_user() -> User:
    """Fixture para crear un usuario simulado."""
    user_id = ObjectId()
    folder_id = ObjectId()
    return User(
        _id=user_id,
        username="testuser",
        email="test@example.com",
        password=hash_password("password"),
        user_credit=999,
        folder=UserFolder(_id=folder_id, entries=[]),
    )


@pytest.fixture
def brevio_service(mock_user: User) -> Generator[BrevioService, None, None]:
    with patch("core.brevio_api.core.database.AsyncDB") as mock_async_db_class:
        mock_db_instance = MagicMock()
        mock_db_instance.database.return_value = AsyncMock(spec=AsyncIOMotorDatabase)
        mock_db_instance.verify_connection = AsyncMock(
            return_value=None
        )  # Mock verify_connection
        mock_async_db_class.return_value = mock_db_instance

        # Crear la instancia real de BrevioService
        service = BrevioService()

        # Asignar el mock_db_instance al _db del servicio
        service._db = mock_db_instance

        # Crear el mock del UserService
        mock_user_service_instance = MagicMock(spec=UserService)
        mock_user_service_instance.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_user_service_instance.create_folder_entry = AsyncMock(
            return_value=str(ObjectId())
        )
        mock_user_service_instance.create_data_result = AsyncMock(return_value=None)

        # Reemplazar el _user_service de la instancia de BrevioService con nuestro mock
        service._user_service = mock_user_service_instance

        # Mock _main
        mock_main = MagicMock()
        mock_main.generate = AsyncMock(return_value={"result": "success"})
        mock_main.generate_summary_documents = AsyncMock(
            return_value={"summary": "done"}
        )
        service._main = mock_main

        # Mock init_services para que no intente conectar a MongoDB
        with patch.object(service, "init_services", new=AsyncMock(return_value=None)):
            yield service


@pytest.mark.asyncio
async def test_generate_success(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        data = BrevioGenerate(
            data=[
                MediaEntry(
                    url=HttpUrl("http://example.com/test.mp3"), path=test_file_path
                )
            ],
            prompt_config=mock_prompt_config,
        )

        with patch("pathlib.Path.is_file", return_value=True), patch.object(
            brevio_service, "get_total_duration", AsyncMock(return_value=60.0)
        ):
            user_id = str(mock_user.id)
            result = await brevio_service.generate(data, user_id, usage_cost_tracker)

            assert result == {"result": "success"}
            mock_generate: AsyncMock = cast(AsyncMock, brevio_service._main.generate)
            mock_generate.assert_awaited_once()

            # Verificar que se llamó a create_folder_entry
            mock_user_service = cast(MagicMock, brevio_service._user_service)
            mock_user_service.create_folder_entry.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_generate_brevio_error(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    """Test para verificar que generate maneja errores de _main correctamente."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
        test_file_path = FilePath(temp_file.name)
        data = BrevioGenerate(
            data=[
                MediaEntry(
                    url=HttpUrl("http://example.com/test.mp3"), path=test_file_path
                )
            ],
            prompt_config=mock_prompt_config,
        )

        # Forzar error en _main.generate
        mock_generate: AsyncMock = cast(AsyncMock, brevio_service._main.generate)
        mock_generate.side_effect = Exception("boom from main.generate")

        with patch("pathlib.Path.is_file", return_value=True), patch.object(
            brevio_service, "get_total_duration", AsyncMock(return_value=60.0)
        ):
            with pytest.raises(HTTPException) as exc_info:
                user_id = str(mock_user.id)
                await brevio_service.generate(data, user_id, usage_cost_tracker)

            assert exc_info.value.status_code == 500
            assert "boom from main.generate" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_generate_summary_media_upload_success(
    brevio_service: BrevioService, mock_user: User, mock_prompt_config: PromptConfig
) -> None:
    files_data: list[Tuple[str, bytes]] = [
        ("video1.mp4", b"content1"),
        ("audio1.mp3", b"content2"),
    ]

    with patch("core.brevio.constants.constants.Constants") as mock_constants, patch(
        "pathlib.Path.is_file", return_value=True
    ), patch("pathlib.Path.mkdir"), patch(
        "core.brevio_api.services.brevio_service.BrevioService._write_file"
    ) as mock_write_file, patch(
        "core.brevio_api.services.brevio_service.wait_for_file",
        AsyncMock(return_value=True),
    ), patch.object(
        brevio_service, "count_minutes_media", AsyncMock(return_value=1.0)
    ), patch(
        "os.chmod", return_value=None
    ):
        mock_constants.DESTINATION_FOLDER = FilePath("/mock/dir")
        mock_write_file.return_value = None

        user_id = str(mock_user.id)
        result = await brevio_service.generate_summary_media_upload(
            files_data, user_id, mock_prompt_config, usage_cost_tracker
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
        "core.brevio_api.services.brevio_service.wait_for_file",
        AsyncMock(return_value=True),
    ), patch(
        "os.chmod", return_value=None
    ):
        mock_constants.DESTINATION_FOLDER = FilePath("/mock/dir")
        mock_write_file.return_value = None

        user_id = str(mock_user.id)
        result = await brevio_service.generate_summary_documents(
            files_data, user_id, mock_prompt_config, usage_cost_tracker
        )

        assert result == {"summary": "done"}
        assert mock_write_file.call_count == len(files_data)
        mock_generate_summary: AsyncMock = cast(
            AsyncMock, brevio_service._main.generate_summary_documents
        )
        mock_generate_summary.assert_awaited_once()
