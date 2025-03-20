import os
import time
import asyncio
import pytest
import logging
from unittest.mock import patch
from backend.brevio.services.summary_service import SummaryService

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Configura variables de entorno necesarias para SummaryService."""
    monkeypatch.setenv("MAX_TOKENS", "1000")
    monkeypatch.setenv("MAX_TOKENS_PER_CHUNK", "250")
    monkeypatch.setenv("TOKENS_PER_MINUTE", "500")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")

@pytest.fixture
def summary_service():
    """Proporciona una instancia de SummaryService para las pruebas."""
    return SummaryService()

def test_chunk_text(summary_service):
    """Prueba la división de texto en chunks."""
    text = "0123456789" * 10  # 100 caracteres
    chunk_size = 30
    overlap = 5
    chunks = summary_service.chunk_text(text, chunk_size, overlap)
    
    assert len(chunks) == 5 
    for chunk in chunks[:-1]:
        assert len(chunk) <= chunk_size 
    assert len(chunks[-1]) <= chunk_size 
    
    reconstructed = chunks[0]
    for chunk in chunks[1:]:
        reconstructed += chunk[overlap:]
    assert text.startswith(reconstructed[:len(text)])

@pytest.mark.asyncio
async def test_check_token_limit_true(summary_service):
    """Prueba que _check_token_limit devuelva True cuando hay suficientes tokens."""
    summary_service.token_bucket = 1000
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is True

@pytest.mark.asyncio
async def test_check_token_limit_false(summary_service):
    """Prueba que _check_token_limit devuelva False cuando no hay suficientes tokens."""
    summary_service.token_bucket = 50
    summary_service.last_token_reset = time.time()
    result = await summary_service._check_token_limit(200)
    assert result is False

@pytest.mark.asyncio
async def test_generate_summary_chunk_success(summary_service, caplog):
    """Prueba el éxito de generate_summary_chunk con una respuesta mockeada."""
    logger = logging.getLogger('backend.brevio.services.summary_service')
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]
            self.usage = MockUsage()

    class MockChoice:
        def __init__(self):
            self.message = MockMessage()

    class MockMessage:
        content = "Resumen de prueba"

    class MockUsage:
        total_tokens = 150

    mock_response = MockResponse()

    async def mock_create(*args, **kwargs):
        return mock_response

    with patch.object(summary_service.client.chat.completions, "create", new=mock_create):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            0, "Texto de prueba", "Prompt de prueba", "Resumen acumulado"
        )
        assert index == 0
        assert summary == "Resumen de prueba"
        assert tokens_used == 150
        assert summary_service.token_bucket == summary_service.tokens_per_minute - 150

        # Check if the expected log message is captured
        #assert any("Chunk 0 processed" in record.getMessage() for record in caplog.records if record.levelname == "INFO")



@pytest.mark.asyncio
async def test_generate_summary_chunk_failure(summary_service):
    """Prueba el manejo de errores en generate_summary_chunk."""
    with patch.object(summary_service.client.chat.completions, "create", side_effect=Exception("Error API")):
        index, summary, tokens_used = await summary_service.generate_summary_chunk(
            1, "Otro texto", "Prompt", "Acumulado"
        )
        assert index == 1
        assert "Error procesando chunk" in summary
        assert tokens_used == 0

@pytest.mark.asyncio
async def test_process_chunks_in_groups(summary_service):
    """Prueba process_chunks_in_groups con chunks simulados."""
    chunks = ["Chunk 1", "Chunk 2"]
    prompt = "Prompt de prueba"
    
    async def fake_generate_summary_chunk(index, chunk, prompt, acc):
        return index, f"Resumen: {chunk}", len(chunk)
    
    with patch.object(summary_service, "generate_summary_chunk", side_effect=fake_generate_summary_chunk), \
         patch.object(summary_service, "_check_token_limit", return_value=True):
        full_summary, total_tokens_used = await summary_service.process_chunks_in_groups(chunks, prompt)
        
        assert "Resumen: Chunk 1" in full_summary
        assert "Resumen: Chunk 2" in full_summary
        assert total_tokens_used == len("Chunk 1") + len("Chunk 2")

if __name__ == "__main__":
    pytest.main([__file__])
