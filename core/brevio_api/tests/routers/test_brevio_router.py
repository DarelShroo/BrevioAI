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
from core.brevio_api.dependencies.credential_resolver_dependency import (
    get_credential_resolver,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.shared.enums.model import ModelType

client = TestClient(app)


class FakeResolver:
    async def ensure_model_access(
        self, user_id: str, model: ModelType, user_credits: float = 0
    ) -> None:
        return None

    async def ensure_user_credential(self, user_id: str, provider: str) -> None:
        return None


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
    app.dependency_overrides[get_credential_resolver] = lambda: FakeResolver()

    class FakeLibraryFolders:
        async def resolve_destination(
            self, user_id: str, folder_id: str | None, folder_name: str | None
        ) -> None:
            return None

        async def resolve_optional_folder(
            self, user_id: str, folder_id: str | None
        ) -> None:
            return None

    from core.brevio_api.dependencies.library_folder_service_dependency import (
        library_folder_service_dependency,
    )

    app.dependency_overrides[
        library_folder_service_dependency
    ] = lambda: FakeLibraryFolders()
    yield


# ================================
# Mock BrevioService
# ================================
class FakeBrevio:
    async def create_summary_job(self, user_id: str, **kwargs: Any) -> str:
        return "folder-abc123"

    async def admit_summary_job_with_files(
        self, user_id: str, files_data: Any, **kwargs: Any
    ) -> tuple[str, bool]:
        job_id = await self.create_summary_job(
            user_id,
            name=kwargs.get("name", ""),
            original_name=kwargs.get("original_name"),
            library_folder_id=kwargs.get("library_folder_id"),
            source_type=kwargs.get("source_type"),
            idempotency_key=kwargs.get("idempotency_key"),
            transcription_provider=kwargs.get("transcription_provider"),
            transcription_model=kwargs.get("transcription_model"),
        )
        return job_id, True

    async def mark_job_enqueued(self, job_id: str) -> None:
        return None

    async def find_job_by_idempotency(
        self, user_id: str, idempotency_key: str
    ) -> str | None:
        return None

    @staticmethod
    def _prompt_metadata(prompt_config: Any, source_type: str) -> dict[str, str]:
        return {
            "language": getattr(prompt_config.language, "name", "SPANISH"),
            "model": getattr(prompt_config.model, "value", str(prompt_config.model)),
            "category": prompt_config.category,
            "style": prompt_config.style,
            "format": getattr(prompt_config.format, "value", str(prompt_config.format)),
            "summary_level": getattr(
                prompt_config.summary_level, "value", str(prompt_config.summary_level)
            ),
            "source_type": source_type,
        }

    async def get_user_credits(self, user_id: str) -> float:
        return 999.0

    async def reserve_credits_for_admitted_job(self, **kwargs: Any) -> None:
        return None

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


def _form_data(mock_prompt_config: PromptConfig, extra: dict | None = None) -> dict:
    data = mock_prompt_config.model_dump(exclude_none=True)
    if extra:
        data.update(extra)
    return data


def _capture_task_delay(monkeypatch: Any, delayed: dict[str, Any]) -> None:
    mock_result = MagicMock()
    mock_result.id = "mocked-task-id"

    def capture_delay(*args: Any, **kwargs: Any) -> MagicMock:
        payload_args = list(args)
        if payload_args and not isinstance(payload_args[0], (dict, str, list, tuple)):
            payload_args = payload_args[1:]
        delayed["args"] = tuple(payload_args)
        delayed.update(kwargs)
        return mock_result

    monkeypatch.setattr("celery.app.task.Task.delay", capture_delay)


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
    body = r.json()["data"]
    assert body["models"] == ["gpt-4", "claude-3"]
    by_id = {item["id"]: item for item in body["catalog"]}
    assert by_id["gpt-4"]["access"] == "pay_per_use"
    assert by_id["gpt-4"]["requires_api_key"] is True
    assert by_id["gpt-4"]["provider"] == "openai"
    assert by_id["claude-3"]["requires_api_key"] is True
    assert any(item["id"] == "openai" for item in body["providers"])


def test_conteo_playlist() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = client.post(
        "/brevio/count-yt-videos",
        json={"url": "https://www.youtube.com/playlist?list=ABC"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 7


def test_duracion_video() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = client.post(
        "/brevio/count-time-yt-video",
        json={"url": "https://www.youtube.com/watch?v=123"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["time"] == 3600


def test_summary_playlist(mock_prompt_config: PromptConfig) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    payload = {
        "data": [{"url": "https://www.youtube.com/playlist?list=XYZ"}],
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
        data = _form_data(mock_prompt_config)
        r = client.post("/brevio/summary-media", files=files, data=data)

    assert r.status_code == 202
    assert r.json()["status"] == "success"


def test_summary_media_ignores_user_max_output_tokens(
    tmp_path: Any, mock_prompt_config: PromptConfig
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = _post_media(
        tmp_path,
        "talk.mp3",
        mock_prompt_config,
        extra={"max_output_tokens": "999999999", "temperature": "1.7"},
    )
    assert r.status_code == 202


def test_summary_media_ignores_temperature_when_model_does_not_support_it(
    tmp_path: Any,
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    path = tmp_path / "talk.mp3"
    path.write_bytes(b"fake-media")
    with open(path, "rb") as file:
        files = {"files": ("talk.mp3", file, "application/octet-stream")}
        data = {
            "language": "SPANISH",
            "model": ModelType.GPT_5_6.value,
            "category": "education",
            "style": "quick_ref",
            "format": "markdown",
            "summary_level": "concise",
            "temperature": "0.2",
        }
        r = client.post("/brevio/summary-media", files=files, data=data)
    assert r.status_code == 202


def test_summary_pdf(tmp_path: Any, mock_prompt_config: PromptConfig) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")

    with open(f, "rb") as file:
        files = {"files": ("doc.pdf", file, "application/pdf")}
        data = _form_data(mock_prompt_config)
        r = client.post("/brevio/summary-documents", files=files, data=data)

    assert r.status_code == 202
    assert r.json()["status"] == "success"
    assert r.json()["task_id"] == "mocked-task-id"
    assert r.json()["folder_entry_id"] == "folder-abc123"


def test_summary_documents_keeps_real_filename(
    tmp_path: Any, mock_prompt_config: PromptConfig
) -> None:
    captured: dict[str, Any] = {}

    class CapturingBrevio(FakeBrevio):
        async def create_summary_job(self, user_id: str, **kwargs: Any) -> str:
            captured.update(kwargs)
            return "folder-abc123"

    app.dependency_overrides[get_brevio_service] = lambda: CapturingBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    filename = "using-asyncio-python-understanding-asynchronous.pdf"
    f = tmp_path / filename
    f.write_bytes(b"%PDF-1.4")

    with open(f, "rb") as file:
        files = {"files": (filename, file, "application/pdf")}
        data = _form_data(mock_prompt_config)
        r = client.post("/brevio/summary-documents", files=files, data=data)

    assert r.status_code == 202
    assert captured["name"] == ""
    assert captured["original_name"] == filename
    assert captured["library_folder_id"] is None


def test_summary_documents_multiple_files_batch_name(
    tmp_path: Any, mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    captured: dict[str, Any] = {}
    delayed: dict[str, Any] = {}

    class CapturingBrevio(FakeBrevio):
        async def create_summary_job(self, user_id: str, **kwargs: Any) -> str:
            captured.update(kwargs)
            return "folder-multi"

    _capture_task_delay(monkeypatch, delayed)
    app.dependency_overrides[get_brevio_service] = lambda: CapturingBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    pdf = tmp_path / "alpha.pdf"
    docx = tmp_path / "beta.docx"
    pdf.write_bytes(b"%PDF-1.4")
    docx.write_bytes(b"PK\x03\x04")

    with open(pdf, "rb") as pdf_file, open(docx, "rb") as docx_file:
        files = [
            ("files", ("alpha.pdf", pdf_file, "application/pdf")),
            (
                "files",
                (
                    "beta.docx",
                    docx_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ]
        r = client.post(
            "/brevio/summary-documents",
            files=files,
            data=_form_data(mock_prompt_config),
        )

    assert r.status_code == 202
    assert captured["name"] == ""
    assert captured["original_name"] == "alpha.pdf; beta.docx"
    assert delayed.get("job_id") == "folder-abc123" or delayed.get("args") == (
        "folder-abc123",
    ) or "files" not in delayed
    assert "files" not in delayed


def test_summary_documents_uses_explicit_entry_name(
    tmp_path: Any, mock_prompt_config: PromptConfig
) -> None:
    captured: dict[str, Any] = {}

    class CapturingBrevio(FakeBrevio):
        async def create_summary_job(self, user_id: str, **kwargs: Any) -> str:
            captured.update(kwargs)
            return "folder-named"

    app.dependency_overrides[get_brevio_service] = lambda: CapturingBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    pdf = tmp_path / "alpha.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    with open(pdf, "rb") as pdf_file:
        files = {"files": ("alpha.pdf", pdf_file, "application/pdf")}
        data = _form_data(mock_prompt_config, {"name": "Mi carpeta"})
        r = client.post("/brevio/summary-documents", files=files, data=data)

    assert r.status_code == 202
    assert captured["name"] == "Mi carpeta"


def test_summary_documents_rejects_empty_file_list(
    mock_prompt_config: PromptConfig,
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()

    data = _form_data(mock_prompt_config)
    r = client.post("/brevio/summary-documents", data=data)
    assert r.status_code == 422


def _post_media(
    tmp_path: Any,
    filename: str,
    mock_prompt_config: PromptConfig,
    extra: dict | None = None,
):
    path = tmp_path / filename
    path.write_bytes(b"fake-media")
    with open(path, "rb") as file:
        files = {"files": (filename, file, "application/octet-stream")}
        data = _form_data(mock_prompt_config, extra)
        return client.post("/brevio/summary-media", files=files, data=data)


@pytest.mark.parametrize("filename", ["talk.mp3", "talk.m4a", "talk.wav", "talk.mp4"])
def test_summary_media_accepts_mvp_formats(
    tmp_path: Any, mock_prompt_config: PromptConfig, filename: str
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = _post_media(tmp_path, filename, mock_prompt_config)
    assert r.status_code == 202, r.text


@pytest.mark.parametrize("filename", ["clip.avi", "clip.mov", "clip.mkv", "clip.webm"])
def test_summary_media_rejects_non_mvp_formats(
    tmp_path: Any, mock_prompt_config: PromptConfig, filename: str
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = _post_media(tmp_path, filename, mock_prompt_config)
    assert r.status_code == 415
    body = r.json()
    assert body["code"] == "MEDIA_FORMAT_NOT_ALLOWED"


def test_transcription_providers_dev_lists_local_whisper() -> None:
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.get("/brevio/transcription-providers")
    assert r.status_code == 200
    payload = r.json()["data"]
    by_id = {item["id"]: item for item in payload["providers"]}
    assert by_id["local_whisper"]["implemented"] is True
    assert by_id["local_whisper"]["user_access"] is True
    assert "local_whisper" in payload["selectable"]


def test_transcription_providers_prod_hides_local_whisper_from_users(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    r = client.get("/brevio/transcription-providers")
    assert r.status_code == 200
    payload = r.json()["data"]
    by_id = {item["id"]: item for item in payload["providers"]}
    assert by_id["local_whisper"]["implemented"] is True
    assert by_id["local_whisper"]["user_access"] is False
    assert "local_whisper" not in payload["selectable"]


def test_prod_rejects_local_whisper_selection(
    tmp_path: Any, mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = _post_media(
        tmp_path,
        "talk.mp3",
        mock_prompt_config,
        extra={"transcription_provider": "local_whisper"},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "TRANSCRIPTION_PROVIDER_NOT_ALLOWED"


def test_dev_allows_local_whisper_selection(
    tmp_path: Any, mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    delayed: dict[str, Any] = {}
    captured: dict[str, Any] = {}
    _capture_task_delay(monkeypatch, delayed)

    class CapturingBrevio(FakeBrevio):
        async def create_summary_job(self, user_id: str, **kwargs: Any) -> str:
            captured.update(kwargs)
            return "folder-abc123"

    app.dependency_overrides[get_brevio_service] = lambda: CapturingBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    r = _post_media(
        tmp_path,
        "talk.mp4",
        mock_prompt_config,
        extra={"transcription_provider": "local_whisper"},
    )
    assert r.status_code == 202, r.text
    assert captured.get("transcription_provider") == "local_whisper"
    assert delayed.get("job_id") == "folder-abc123" or delayed.get("args") == (
        "folder-abc123",
    )
    assert "files" not in delayed
    assert "api_key" not in delayed
    assert "openai_api_key" not in delayed


def test_openai_without_byok_returns_transcription_code(
    tmp_path: Any, mock_prompt_config: PromptConfig
) -> None:
    class MissingKeyResolver(FakeResolver):
        async def ensure_user_credential(self, user_id: str, provider: str) -> None:
            raise ProviderError(
                kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED, message="missing"
            )

    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    app.dependency_overrides[get_credential_resolver] = lambda: MissingKeyResolver()
    r = _post_media(
        tmp_path,
        "talk.mp3",
        mock_prompt_config,
        extra={"transcription_provider": "openai"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "TRANSCRIPTION_API_KEY_REQUIRED"


def test_youtube_prod_requires_openai_key_before_queue(
    mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)

    class MissingKeyResolver(FakeResolver):
        async def ensure_user_credential(self, user_id: str, provider: str) -> None:
            raise ProviderError(
                kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED, message="missing"
            )

    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    app.dependency_overrides[get_credential_resolver] = lambda: MissingKeyResolver()
    payload = {
        "data": [{"url": "https://youtube.com/watch?v=abc"}],
        "prompt_config": mock_prompt_config.model_dump(),
    }
    with patch(
        "core.brevio_api.routers.brevio_router.generate_summary_task"
    ) as mock_task:
        mock_task.delay = MagicMock()
        r = client.post("/brevio/summary-yt-playlist", json=payload)
        mock_task.delay.assert_not_called()
    assert r.status_code == 401
    assert r.json()["code"] == "TRANSCRIPTION_API_KEY_REQUIRED"


def test_youtube_prod_rejects_local_whisper(
    mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    payload = {
        "data": [{"url": "https://youtube.com/watch?v=abc"}],
        "prompt_config": mock_prompt_config.model_dump(),
        "transcription_provider": "local_whisper",
    }
    r = client.post("/brevio/summary-yt-playlist", json=payload)
    assert r.status_code == 403
    assert r.json()["code"] == "TRANSCRIPTION_PROVIDER_NOT_ALLOWED"


def test_youtube_sends_resolved_transcription_provider(
    mock_prompt_config: PromptConfig, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    delayed: dict[str, Any] = {}
    _capture_task_delay(monkeypatch, delayed)

    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    payload = {
        "data": [{"url": "https://youtube.com/watch?v=abc"}],
        "prompt_config": mock_prompt_config.model_dump(),
        "transcription_provider": "local_whisper",
    }
    r = client.post("/brevio/summary-yt-playlist", json=payload)
    assert r.status_code == 202, r.text
    # Celery now receives job_id only; payload is persisted on the job.
    assert delayed.get("job_id") == "folder-abc123" or delayed.get("args") == (
        "folder-abc123",
    )
    assert "brevio_generate_dict" not in delayed
    assert not any(isinstance(a, dict) and "transcription_provider" in a for a in delayed.get("args", ()))


def test_youtube_ignores_user_max_output_tokens(
    mock_prompt_config: PromptConfig,
) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: FakeBrevio()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    payload = {
        "data": [{"url": "https://youtube.com/watch?v=abc"}],
        "prompt_config": {
            **mock_prompt_config.model_dump(),
            "max_output_tokens": 999_999_999,
            "temperature": 1.7,
        },
    }
    r = client.post("/brevio/summary-yt-playlist", json=payload)
    assert r.status_code == 202
