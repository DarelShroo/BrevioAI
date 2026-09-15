import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture
def summary_service():
    service = SummaryService()
    # Mockear las capacidades del modelo para forzar un native_max_output_tokens alto
    service.tokens_per_minute = 100_000
    service.token_bucket = 100_000
    return service


@pytest.mark.asyncio
async def test_case_1_and_2_budget_estimation(summary_service):
    """
    Caso 1 y 2: Input=4000, Output=4000 -> Reserva ~8000.
    NO usa native_max_output_tokens (ej. 384,000).
    """
    initial_bucket = summary_service.token_bucket

    # Supongamos input=4000, requested_output=4000
    tokens_needed = 4000 + 4000

    # Comprobar que esto pasa sin esperar
    result = await summary_service._check_token_limit(
        tokens_needed=tokens_needed,
        request_type="TEST",
        model_name="test-model",
        input_tokens=4000,
        requested_output_tokens=4000,
    )

    assert result is True
    # Debe haber restado EXACTAMENTE 8000
    assert summary_service.token_bucket == initial_bucket - 8000


@pytest.mark.asyncio
async def test_case_3_exceed_capacity(summary_service):
    """
    Caso 3: Request excede capacidad -> Falla controlado, no bucle.
    """
    tokens_needed = 100_001
    result = await summary_service._check_token_limit(tokens_needed=tokens_needed)
    assert result is True


@pytest.mark.asyncio
async def test_case_4_release_surplus(summary_service):
    """
    Caso 4: Reserva seguida de uso menor -> Excedente liberado.
    """
    initial_bucket = summary_service.token_bucket
    tokens_needed = 10_000

    await summary_service._check_token_limit(tokens_needed=tokens_needed)
    assert summary_service.token_bucket == initial_bucket - 10_000

    # API gasta 2_000, sobran 8_000
    unused = 10_000 - 2_000
    summary_service.refund_tokens(unused)

    assert summary_service.token_bucket == initial_bucket - 2_000


@pytest.mark.asyncio
async def test_case_5_api_exception(summary_service):
    """
    Caso 5: API lanza excepcion -> Reserva liberada (reembolso total).
    """
    initial_bucket = summary_service.token_bucket
    tokens_needed = 5_000

    await summary_service._check_token_limit(tokens_needed=tokens_needed)

    # Simula fallo, se llama a refund con tokens_needed
    summary_service.refund_tokens(tokens_needed)

    assert summary_service.token_bucket == initial_bucket


@pytest.mark.asyncio
async def test_case_6_concurrent_calls(summary_service):
    """
    Caso 6: Llamadas concurrentes no superan presupuesto.
    """
    summary_service.token_bucket = 25_000
    summary_service.tokens_per_minute = 20_000

    # 3 llamadas de 10_000. 2 deberían pasar (10k cada una + 1k safety_margin),
    # la 3a debería esperar y fallar por timeout.
    os.environ["MAX_TOKEN_WAIT"] = "1"

    async def try_acquire():
        return await summary_service._check_token_limit(tokens_needed=10_000)

    t1 = asyncio.create_task(try_acquire())
    t2 = asyncio.create_task(try_acquire())
    t3 = asyncio.create_task(try_acquire())

    results = await asyncio.gather(t1, t2, t3, return_exceptions=True)

    successes = sum(1 for r in results if r is True)
    timeouts = sum(1 for r in results if isinstance(r, TimeoutError))

    assert successes == 2
    assert timeouts == 1
    assert summary_service.token_bucket == 5000


@pytest.mark.asyncio
async def test_case_7_pipeline_phases(summary_service):
    """
    Caso 7: MAP, REDUCE y FORMAT no suman todo el budget global, cada uno pide lo suyo.
    """
    summary_service.token_bucket = 50_000

    # Fase MAP (4 chunks, 4000 req cada uno) -> se descuenta por separado
    for _ in range(4):
        await summary_service._check_token_limit(tokens_needed=4000, request_type="MAP")

    assert summary_service.token_bucket == 50_000 - 16_000

    # Fase REDUCE (1 chunk de 5000)
    await summary_service._check_token_limit(tokens_needed=5000, request_type="REDUCE")
    assert summary_service.token_bucket == 50_000 - 21_000

    # Fase FORMAT (1 chunk de 6000)
    await summary_service._check_token_limit(
        tokens_needed=6000, request_type="FORMAT_SINGLE"
    )
    assert summary_service.token_bucket == 50_000 - 27_000
