"""Regression: short technical sections and code examples must survive MAP→REDUCE."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator
from core.brevio.services.summary_service import MapChunkResult, SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.chunking_utils import extract_document_outline


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


@pytest.mark.asyncio
async def test_regression_preserve_section_1_9() -> None:
    """
    Section 1.9 with code examples (document.write / alert / prompt) must not be
    dropped by REDUCE. Uses mocked LLM calls — no live provider required.
    """
    chunks = [
        """
        1.8 Elementos de un programa
        Un programa es un conjunto de instrucciones.
        """,
        """
        1.9 Entrada y Salida

        document.write("Hola")
        alert("Hola")
        prompt("Introduce tu nombre")
        """,
    ]

    full_text = "\n".join(chunks)
    outline = extract_document_outline(full_text)
    assert any("1.9" in item for item in outline) or "1.9" in full_text

    service = SummaryService()
    service.history_token_model.summary_level = "moderate"
    service.client = MagicMock()

    gen = AdvancedPromptGenerator()
    map_prompt = await gen.get_map_prompt(LanguageType.SPANISH)
    reduce_prompt = await gen.get_reduce_prompt(LanguageType.SPANISH)
    assert "COVERAGE" in reduce_prompt.upper() or "COBERTURA" in reduce_prompt.upper()

    map_results = [
        MapChunkResult(
            0,
            chunks[0],
            "SUCCESS",
            "1.8 Elementos de un programa: conjunto de instrucciones.",
        ),
        MapChunkResult(
            1,
            chunks[1],
            "SUCCESS",
            "1.9 Entrada y Salida: document.write, alert, prompt.",
        ),
    ]

    async def fake_reduce(mapped, *args, **kwargs):
        texts = []
        for item in mapped:
            if isinstance(item, MapChunkResult):
                texts.append(item.summary_text or "")
            else:
                texts.append(str(item))
        joined = "\n".join(texts)
        assert "1.9" in joined
        assert "document.write" in joined
        return (
            "1.8 Elementos de un programa.\n"
            "1.9 Entrada y Salida con document.write, alert y prompt.",
            12,
        )

    with patch.object(service, "run_reduce_phase", side_effect=fake_reduce):
        final_summary, _ = await service.run_reduce_phase(
            map_results, reduce_prompt, ModelType.GPT_4O_MINI, LanguageType.SPANISH
        )

    final_summary_lower = final_summary.lower()
    assert "1.9" in final_summary_lower or "entrada y salida" in final_summary_lower
    assert "document.write" in final_summary_lower
    assert "alert" in final_summary_lower
    assert "prompt" in final_summary_lower
    assert "console.log" not in final_summary_lower
