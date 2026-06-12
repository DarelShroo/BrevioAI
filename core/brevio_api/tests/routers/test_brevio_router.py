from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

# === IMPORTS ORIGINALES ===
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.__main__ import app
from core.brevio_api.config.dotenv import API_KEY
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.shared.enums.model import ModelType

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar() -> Generator:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def usuario_falso() -> User:
    return User(
        _id=ObjectId(),
        username="testuser",
        email="test@example.com",
        password="fakehash",
        user_credit=999,
        folder=UserFolder(entries=[]),
    )


@pytest.fixture(autouse=True)
def mock_todo(monkeypatch: Any, usuario_falso: User) -> Generator:
    async def fake_get_user(field: str, value: Any) -> User | None:
        if field == "_id" and str(value) == str(usuario_falso.id):
            return usuario_falso
        return None

    monkeypatch.setattr(
        "core.brevio_api.repositories.user_repository.UserRepository.get_user_by_field",
        fake_get_user,
    )

    async def fake_folder_entry(self: Any, user_id: str) -> str:
        return "folder-abc123"

    monkeypatch.setattr(
        "core.brevio_api.services.user_service.UserService.create_folder_entry",
        fake_folder_entry,
    )
    yield


# ================================
# Mock BrevioService
# ================================
class FakeBrevio:
    def get_languages(self) -> List[str]:
        return ["ENGLISH", "SPANISH"]

    def get_models(self) -> List[str]:
        return ["gpt-4", "claude-3"]

    async def get_all_category_style_combinations(
        self,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return {"news": [{"style": "wire", "source_types": ["text"]}]}

    async def count_media_in_yt_playlist(self, url: str) -> int:
        return 7

    async def get_total_duration(self, url: str) -> int:
        return 3600


# ================================
# FIXTURE PROMPT CONFIG
# ================================
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


# ================================
# DESHABILITAR CELERY POR COMPLETO EN TESTS
# ================================
@pytest.fixture(autouse=True)
def disable_celery_connections(monkeypatch: Any) -> None:
    """
    Mockea TODAS las instancias de Celery Task para que .delay() devuelva un mock
    sin intentar conectar a RabbitMQ.
    """
    mock_result = MagicMock()
    mock_result.id = "mocked-task-id"

    def fake_delay(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_result

    # Mockea .delay en cualquier Task de Celery
    monkeypatch.setattr("celery.app.task.Task.delay", fake_delay)

    # También mockea .apply_async por si acaso
    monkeypatch.setattr("celery.app.task.Task.apply_async", lambda *a, **k: mock_result)


# ================================
# TESTS
# ================================
def test_languajes() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.get("/brevio/languages")
    assert r.status_code == 200


def test_modelos() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.get("/brevio/models")
    assert r.status_code == 200


def test_conteo_playlist() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.post(
        "/brevio/count-yt-videos", json={"url": "https://youtube.com/playlist?list=ABC"}
    )
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 7


def test_duracion_video() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.post(
        "/brevio/count-time-yt-video", json={"url": "https://youtube.com/watch?v=123"}
    )
    assert r.status_code == 200
    assert r.json()["data"]["time"] == 3600


def test_summary_playlist(mock_prompt_config: PromptConfig) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    payload = {
        "data": [{"url": "https://youtube.com/playlist?list=XYZ"}],
        "prompt_config": mock_prompt_config.model_dump(),
    }
    r = client.post("/brevio/summary-yt-playlist", json=payload)

    assert r.status_code == 202
    assert r.json()["status"] == "success"


def test_summary_audio(tmp_path: Any, mock_prompt_config: PromptConfig) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    f = tmp_path / "test.mp3"
    f.write_bytes(b"fake audio")

    with open(f, "rb") as file:
        files = {"files": ("test.mp3", file, "audio/mpeg")}
        data = {**mock_prompt_config.model_dump()}
        r = client.post("/brevio/summary-media", files=files, data=data)

    assert r.status_code == 202
    assert r.json()["status"] == "success"


def test_summary_pdf(tmp_path: Any, mock_prompt_config: PromptConfig) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")

    with open(f, "rb") as file:
        files = {"files": ("doc.pdf", file, "application/pdf")}
        data = {**mock_prompt_config.model_dump()}
        r = client.post("/brevio/summary-documents", files=files, data=data)

    assert r.status_code == 202
    assert r.json()["status"] == "success"
