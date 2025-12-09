import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.brevio.constants.constants import Constants
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.routers.brevio_router import brevio_router
from core.brevio_api.services.brevio_service import BrevioService

app = FastAPI()
app.include_router(brevio_router)

from bson import ObjectId

from core.brevio_api.dependencies.user_dependency import get_current_user

# Mock dependencies
mock_brevio_service = MagicMock(spec=BrevioService)


def override_get_brevio_service() -> MagicMock:
    return mock_brevio_service


def override_verify_api_key() -> str:
    return "valid_key"


def override_get_current_user() -> ObjectId:
    return ObjectId("507f1f77bcf86cd799439011")


app.dependency_overrides[get_brevio_service] = override_get_brevio_service
app.dependency_overrides[verify_api_key] = override_verify_api_key
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.mark.asyncio
async def test_download_folder_success() -> None:
    # Setup
    user_id = "507f1f77bcf86cd799439011"
    folder_id = "test_folder_id"

    # Mock the service method to return a Response
    from fastapi.responses import Response

    mock_brevio_service.download_folder_content.return_value = Response(
        content=b"fake_zip_content",
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=download_{folder_id}.zip"
        },
    )

    # Execute
    response = client.get(f"/brevio/download/{folder_id}")

    # Verify
    assert response.status_code == 200
    assert response.content == b"fake_zip_content"
    assert response.headers["content-type"] == "application/zip"
    assert (
        "attachment; filename=download_test_folder_id.zip"
        in response.headers["content-disposition"]
    )
    mock_brevio_service.download_folder_content.assert_called_once_with(
        user_id, folder_id
    )


@pytest.mark.asyncio
async def test_download_folder_not_found() -> None:
    # Setup
    user_id = "507f1f77bcf86cd799439011"
    folder_id = "non_existent_folder"

    from fastapi import HTTPException

    mock_brevio_service.download_folder_content.side_effect = HTTPException(
        status_code=404, detail="Folder not found"
    )

    # Execute
    response = client.get(f"/brevio/download/{folder_id}")

    # Verify
    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"
