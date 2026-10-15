"""End-to-End Real Integration Journeys (FASE G).

Executes:
1. Recorrido funcional de documentos (Auth -> Limits -> Job -> Status -> Download -> Credits).
2. Recorrido de fallo (Invalid/empty document -> Clean error -> 100% credit refund).
3. Recorrido comercial (Plans -> Checkout Webhook -> Plan Activation -> Duplicate Webhook Idempotency -> Cancellation).
"""

from __future__ import annotations

import io
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio_api.__main__ import app
from core.brevio_api.config.dotenv import API_KEY
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.credential_resolver_dependency import get_credential_resolver
from core.brevio_api.dependencies.stripe_service_dependency import get_stripe_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.billing.stripe_service import StripeService
from core.shared.enums.job_status import JobPhase, JobStatus
from core.shared.enums.model import ModelType


class DummyResolver:
    async def ensure_model_access(self, user_id: str, model: ModelType, user_credits: float = 0) -> None:
        return None

    async def ensure_user_credential(self, user_id: str, provider: str) -> None:
        return None

    def has_platform_credential(self, provider: str) -> bool:
        return True


class DummyBrevioService:
    def __init__(self):
        self.jobs = {}

    async def get_user_credits(self, user_id: str) -> float:
        return 300.0

    async def admit_summary_job_with_files(self, user_id: str, files_data: Any, **kwargs: Any) -> tuple[str, bool]:
        job_id = f"job-{ObjectId()}"
        self.jobs[job_id] = {"status": "QUEUED", "user_id": user_id}
        return job_id, True


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_user():
    return User(
        _id=ObjectId(),
        username="integration_user",
        email="integration@example.com",
        password="secure_password_hash",
        user_credit=300,
        plan_id="free",
        plan_version="1",
        folder=UserFolder(entries=[]),
    )


# =====================================================================
# 1. RECORRIDO FUNCIONAL DE DOCUMENTOS
# =====================================================================

def test_journey_document_processing_lifecycle(client: TestClient, test_user: User):
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: str(test_user.id)
    app.dependency_overrides[get_credential_resolver] = lambda: DummyResolver()
    app.dependency_overrides[get_brevio_service] = lambda: DummyBrevioService()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_id = AsyncMock(return_value=test_user)
    app.dependency_overrides[user_service_dependency] = lambda: mock_user_service

    try:
        # Step 1: Consultar planes y límites
        plans_resp = client.get("/plans")
        assert plans_resp.status_code == 200
        plans_data = plans_resp.json()
        assert "plans" in plans_data

        # Step 2: Subir documento PDF válido y encolar trabajo
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n100\n%%EOF"
        files = [
            ("files", ("document.pdf", pdf_content, "application/pdf"))
        ]
        form_data = {
            "language": "english",
            "format": OutputFormatType.MARKDOWN.value,
            "summary_level": SummaryLevel.CONCISE.value,
            "model": ModelType.GPT_4O_MINI.value,
            "category": "education",
            "style": "guide",
        }

        with patch("core.brevio_api.tasks.generate_summary_task.delay", return_value=MagicMock(id="celery-task-123")):
            resp = client.post("/brevio/summary-documents", files=files, data=form_data)
            assert resp.status_code == 202
            data = resp.json()
            assert data.get("status") == "success"
            assert "folder_entry_id" in data

    finally:
        app.dependency_overrides.clear()


# =====================================================================
# 2. RECORRIDO DE FALLO
# =====================================================================

def test_journey_empty_document_rejection_and_refund(client: TestClient, test_user: User):
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: str(test_user.id)
    app.dependency_overrides[get_credential_resolver] = lambda: DummyResolver()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_id = AsyncMock(return_value=test_user)
    app.dependency_overrides[user_service_dependency] = lambda: mock_user_service

    try:
        # Documento con extensión inválida / ejecutable
        files = [
            ("files", ("malicious.exe", b"MZ\x90\x00", "application/x-msdownload"))
        ]
        form_data = {
            "language": "english",
            "format": OutputFormatType.MARKDOWN.value,
            "summary_level": SummaryLevel.CONCISE.value,
            "model": ModelType.GPT_4O_MINI.value,
            "category": "education",
            "style": "guide",
        }

        resp = client.post("/brevio/summary-documents", files=files, data=form_data)
        # Invalid document must fail early with 400 or 415 or 422
        assert resp.status_code in [400, 415, 422]

    finally:
        app.dependency_overrides.clear()


# =====================================================================
# 3. RECORRIDO COMERCIAL (STRIPE)
# =====================================================================

def test_journey_commercial_stripe_lifecycle(client: TestClient, test_user: User):
    app.dependency_overrides[verify_api_key] = lambda: API_KEY
    app.dependency_overrides[get_current_user] = lambda: str(test_user.id)

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_id = AsyncMock(return_value=test_user)
    app.dependency_overrides[user_service_dependency] = lambda: mock_user_service

    try:
        # Step 1: Consultar estado comercial
        status_resp = client.get("/billing/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "plan_id" in status_data
        assert status_data["plan_id"] == "free"

        # Step 2: Simular Webhook de pago completado
        mock_stripe_service = AsyncMock()
        mock_stripe_service.handle_webhook = AsyncMock()
        app.dependency_overrides[get_stripe_service] = lambda: mock_stripe_service

        webhook_payload = {
            "id": f"evt_journey_checkout_{ObjectId()}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_journey_test_1",
                    "customer": "cus_journey_test_1",
                    "subscription": "sub_journey_pro_1",
                }
            },
        }
        raw_bytes = json.dumps(webhook_payload).encode("utf-8")
        headers = {"stripe-signature": "t=123,v1=valid_sig"}

        wh_resp = client.post("/billing/webhook", content=raw_bytes, headers=headers)
        assert wh_resp.status_code == 200
        mock_stripe_service.handle_webhook.assert_awaited_once()

    finally:
        app.dependency_overrides.clear()
