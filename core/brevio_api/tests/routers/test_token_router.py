"""
End-to-end tests for Token routes in FastAPI application.
"""

from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app

client = TestClient(app)


def test_token_router_not_found() -> None:
    response = client.get("/token")
    assert response.status_code == 404
