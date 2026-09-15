"""Connectivity check must not consume a provider completion."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.services.api_service import ApiService
from core.shared.enums.model import ModelType


@pytest.mark.asyncio
async def test_check_api_connectivity_does_not_create_completion():
    svc = ApiService(
        running=True,
        task_queue=MagicMock(),
        queue_lock=MagicMock(),
        client_lock=MagicMock(),
        tasks_put=0,
        task_done_calls=0,
        running_tasks=[],
        credential_resolver=MagicMock(),
    )
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=AssertionError("completion probe must not run")
    )
    svc._initialize_client = AsyncMock(return_value=fake_client)
    ok = await svc.check_api_connectivity(ModelType.GPT_4O_MINI, user_id="u1")
    assert ok is True
    fake_client.chat.completions.create.assert_not_called()
    svc._initialize_client.assert_awaited()


@pytest.mark.asyncio
async def test_check_api_connectivity_false_on_init_error():
    svc = ApiService(
        running=True,
        task_queue=MagicMock(),
        queue_lock=MagicMock(),
        client_lock=MagicMock(),
        tasks_put=0,
        task_done_calls=0,
        running_tasks=[],
        credential_resolver=MagicMock(),
    )
    svc._initialize_client = AsyncMock(side_effect=RuntimeError("no creds"))
    ok = await svc.check_api_connectivity(ModelType.GPT_4O_MINI, user_id="u1")
    assert ok is False
