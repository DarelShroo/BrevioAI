import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.billing_estimator_dependency import get_billing_estimator
from core.brevio_api.dependencies.advanced_prompt_generator_dependency import get_advanced_prompt_generator
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel

client = TestClient(app)

@pytest.fixture
def override_dependencies():
    app.dependency_overrides[verify_api_key] = lambda: "test-api-key"
    mock_billing = AsyncMock()
    mock_billing.summary_tokens_predict.return_value = {"total": 100, "prompt": 50, "completion": 50}
    app.dependency_overrides[get_billing_estimator] = lambda: mock_billing
    
    mock_acg = AsyncMock()
    app.dependency_overrides[get_advanced_prompt_generator] = lambda: mock_acg
    
    yield
    app.dependency_overrides.clear()

def test_estimate_media(override_dependencies):
    response = client.get("/billing/estimate-media", params={"minutes": 10.5})
    # Since the endpoint currently has "pass", it returns null/empty
    assert response.status_code == 200

def test_estimate_documents(override_dependencies):
    params = {
        "file_tokens": 1000,
        "model": "gpt-4o-mini",
        "language_output": "spanish",
        "language_input": "english",
        "category": "journalism",
        "style": "chronicle",
        "output_format": "markdown",
        "summary_level": "detailed"
    }
    response = client.get("/billing/estimate-documents", params=params)
    assert response.status_code == 200
    assert response.json() == {"total": 100, "prompt": 50, "completion": 50}
