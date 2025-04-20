from typing import Any, Dict, List, Optional

import pytest
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from core.brevio.enums.language import LanguageType
from core.brevio.enums.model import ModelType
from core.brevio.enums.source_type import SourceType
from core.brevio_api.__main__ import app
from core.brevio_api.config.config import API_KEY
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.services.brevio_service import BrevioService

# Cliente de prueba
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Any:
    # Limpiar el override después de cada test
    yield
    app.dependency_overrides.clear()


# Clase mock para BrevioService
class MockBrevioService:
    def get_languages(self) -> List[str]:
        return [LanguageType.ENGLISH.name, LanguageType.SPANISH.name]

    def get_models(self) -> List[str]:
        return ["MODEL_A", "MODEL_B"]

    def get_all_category_style_combinations(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "Category1": [{"style": "Style1", "source_types": ["TypeA"]}],
            "Category2": [{"style": "Style2", "source_types": ["TypeB"]}],
        }

    async def count_media_in_yt_playlist(self, url: str) -> int:
        # Actualizar para coincidir con cualquier URL que pase la validación
        return 5

    async def get_total_duration(self, url: str) -> int:
        # Actualizar para devolver un valor para cualquier URL válida
        return 3600

    async def generate(self, data: Any, user_id: ObjectId) -> Dict[str, str]:
        return {"status": "processing"}

    async def generate_summary_media_upload(
        self, files_data: Any, user_id: ObjectId, prompt_config: Dict[str, Any]
    ) -> Dict[str, str]:
        return {"status": "processing"}

    async def generate_summary_documents(
        self, files_data: Any, user_id: ObjectId, prompt_config: Dict[str, Any]
    ) -> Dict[str, str]:
        return {"status": "processing"}


# Helper para simular acceso no autorizado
def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no proporcionado o nulo"
    )


# Tests para /languages
def test_get_languages_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    response = client.get("/brevio/languages")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["languages"] == ["ENGLISH", "SPANISH"]
    app.dependency_overrides.clear()


def test_get_languages_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    response = client.get("/brevio/languages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /models
def test_get_models_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    response = client.get("/brevio/models")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["models"] == ["MODEL_A", "MODEL_B"]
    app.dependency_overrides.clear()


def test_get_models_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    response = client.get("/brevio/models")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /categories-styles
def test_get_categories_styles_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    response = client.get("/brevio/categories-styles")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["advanced_content_combinations"] == {
        "Category1": [{"style": "Style1", "source_types": ["TypeA"]}],
        "Category2": [{"style": "Style2", "source_types": ["TypeB"]}],
    }
    app.dependency_overrides.clear()


def test_get_categories_styles_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    response = client.get("/brevio/categories-styles")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /count-yt-videos
def test_count_yt_videos_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    payload = {"url": "https://www.youtube.com/playlist?list=PL123456"}
    response = client.post("/brevio/count-yt-videos", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["count"] == 5
    app.dependency_overrides.clear()


def test_count_yt_videos_invalid_url() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    payload = {"url": "invalid_url"}
    response = client.post("/brevio/count-yt-videos", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    app.dependency_overrides.clear()


def test_count_yt_videos_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    payload = {"url": "https://www.youtube.com/playlist?list=PL123456"}
    response = client.post("/brevio/count-yt-videos", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /count-time-yt-video
def test_get_total_duration_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY

    payload = {
        "url": "https://www.youtube.com/watch?v=oTf0KxK1QNo&list=PLqRCtm0kbeHA5M_E_Anwu-vh4NWlgrOY_"
    }

    response = client.post("/brevio/count-time-yt-video", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["time"] == 3600

    app.dependency_overrides.clear()


def test_get_total_duration_non_youtube_url() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY

    payload = {"url": "https://www.google.com"}

    response = client.post("/brevio/count-time-yt-video", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    app.dependency_overrides.clear()


def test_get_total_duration_invalid_url() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY

    payload = {"url": "invalid-url"}

    response = client.post("/brevio/count-time-yt-video", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    app.dependency_overrides.clear()


def test_get_total_duration_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    payload = {"url": "https://www.youtube.com/watch?v=123456"}
    response = client.post("/brevio/count-time-yt-video", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /summary-yt-playlist
def test_summary_yt_playlist_success() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    payload = {
        "data": [{"url": "https://www.youtube.com/playlist?list=PL123456"}],
        "prompt_config": {
            "language": LanguageType.SPANISH.name.lower(),
            "model": ModelType.GPT_4.value,
            "category": "journalism",
            "style": "news_wire",
            "format": "markdown",
            "source_types": SourceType.TEXT.value,
        },
    }
    response = client.post("/brevio/summary-yt-playlist", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    app.dependency_overrides.clear()


def test_summary_yt_playlist_invalid_url() -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    payload = {
        "data": [{"url": "invalid_url"}],
        "prompt_config": {
            "language": LanguageType.SPANISH.name.lower(),
            "model": ModelType.GPT_4.value,
            "category": "journalism",
            "style": "news_wire",
            "format": "markdown",
            "source_types": SourceType.TEXT.value,
        },
    }
    response = client.post("/brevio/summary-yt-playlist", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    app.dependency_overrides.clear()


def test_summary_yt_playlist_unauthorized() -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    payload = {
        "data": [{"url": "https://www.youtube.com/playlist?list=PL123456"}],
        "prompt_config": {
            "language": LanguageType.SPANISH.name.lower(),
            "model": ModelType.GPT_4.value,
            "category": "journalism",
            "style": "news_wire",
            "format": "markdown",
            "source_types": SourceType.TEXT.value,
        },
    }
    response = client.post("/brevio/summary-yt-playlist", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    app.dependency_overrides.clear()


# Tests para /summary-media
def test_summary_media_success(tmp_path: Any) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    file_path = tmp_path / "test.mp3"
    file_path.write_bytes(b"fake mp3 content")
    with open(file_path, "rb") as f:
        response = client.post(
            "/brevio/summary-media",
            files={"files": ("test.mp3", f, "audio/mpeg")},
            data={
                "language": LanguageType.SPANISH.name.lower(),
                "model": ModelType.GPT_4.value,
                "category": "journalism",
                "style": "news_wire",
                "format": "markdown",
                "source_types": SourceType.TEXT.value,
            },
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    app.dependency_overrides.clear()


def test_summary_media_unsupported_file(tmp_path: Any) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"fake text content")
    with open(file_path, "rb") as f:
        response = client.post(
            "/brevio/summary-media",
            files={"files": ("test.txt", f, "text/plain")},
            data={
                "language": LanguageType.SPANISH.name.lower(),
                "model": ModelType.GPT_4.value,
                "category": "journalism",
                "style": "news_wire",
                "format": "markdown",
                "source_types": SourceType.TEXT.value,
            },
        )
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    app.dependency_overrides.clear()


def test_summary_media_unauthorized(tmp_path: Any) -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    file_path = tmp_path / "test.mp3"
    file_path.write_bytes(b"fake audio content")
    with open(file_path, "rb") as file:
        response = client.post(
            "/brevio/summary-media",
            files={"files": ("test.mp3", file, "audio/mpeg")},
            data={
                "language": LanguageType.SPANISH.name.lower(),
                "model": ModelType.GPT_4.value,
                "category": "journalism",
                "style": "news_wire",
                "format": "markdown",
                "source_types": SourceType.TEXT.value,
            },
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "status": "error",
        "message": "Token no proporcionado o nulo",
        "signature": {
            "brand": "Brevio",
            "version": "v1.0",
            "contact": "support@brevio.com",
        },
    }
    app.dependency_overrides.clear()


# Tests para /summary-documents
def test_summary_documents_success(tmp_path: Any) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    try:
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"fake pdf content")
        with open(file_path, "rb") as f:
            response = client.post(
                "/brevio/summary-documents",
                files={"files": ("test.pdf", f, "application/pdf")},
                data={
                    "language": LanguageType.SPANISH.name.lower(),
                    "model": ModelType.GPT_4.value,
                    "category": "journalism",
                    "style": "news_wire",
                    "format": "markdown",
                    "source_types": SourceType.TEXT.value,
                },
            )
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "data" in data
        assert data["status"] == "success"
    finally:
        app.dependency_overrides.clear()


def test_summary_documents_unsupported_file(tmp_path: Any) -> None:
    app.dependency_overrides[get_brevio_service] = lambda: MockBrevioService()
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: ObjectId()
    try:
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"fake text content")
        with open(file_path, "rb") as f:
            response = client.post(
                "/brevio/summary-documents",
                files={"files": ("test.txt", f, "text/plain")},
                data={
                    "language": LanguageType.ENGLISH.name.lower(),
                    "model": ModelType.GPT_4.value,
                    "category": "journalism",
                    "style": "news_wire",
                    "format": "markdown",
                    "source_types": SourceType.PDF.value,
                },
            )
        assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    finally:
        app.dependency_overrides.clear()


def test_summary_documents_unauthorized(tmp_path: Any) -> None:
    app.dependency_overrides[verify_api_key] = raise_unauthorized
    try:
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"dummy_content")
        with open(file_path, "rb") as f:
            data = {
                "language": LanguageType.SPANISH.name.lower(),
                "model": ModelType.GPT_4.value,
                "category": "journalism",
                "style": "news_wire",
                "format": "markdown",
                "source_types": SourceType.TEXT.value,
            }
            response = client.post(
                "/brevio/summary-documents",
                files={"files": ("test.pdf", f, "application/pdf")},
                data=data,
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        expected_response = {
            "status": "error",
            "message": "Token no proporcionado o nulo",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        }
        assert response.json() == expected_response
    finally:
        app.dependency_overrides.clear()
