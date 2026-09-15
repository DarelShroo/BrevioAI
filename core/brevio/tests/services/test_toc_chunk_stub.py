"""TOC-heavy chunks must become compact MAP stubs, not invented lessons."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.chunking_utils import (
    extract_toc_entry_labels,
    is_table_of_contents_chunk,
)

TOC_SAMPLE = """
Tabla de Contenido
UNIDAD 1 - INTRODUCCIÓN ................................................................ 9
  1.1 - ¿QUÉ ES JAVASCRIPT? ............................................................. 9
  1.2 - EDITAR JAVASCRIPT ............................................................... 10
UNIDAD 2 - ELEMENTOS BÁSICOS ....................................................... 25
  2.1 - ELEMENTOS DEL LENGUAJE ......................................................... 25
UNIDAD 3 - ESTRUCTURAS DE CONTROL .............................................. 41
UNIDAD 4 - FUNCIONES ................................................................... 55
UNIDAD 5 - OBJETOS ........................................................................ 65
UNIDAD 6 - EVENTOS ....................................................................... 85
UNIDAD 7 - DHTML ......................................................................... 95
Tabla de Ejemplos
Ejemplo 1 – Código JavaScript embebido ............................................. 11
Ejemplo 2 – Código JavaScript en fichero externo ................................. 13
Ejemplo 6 – Conversor pesetas a euros ............................................. 21
Ejemplo 40 – Eventos de ratón ........................................................... 143
"""


BODY_SAMPLE = """
UNIDAD 1 - INTRODUCCIÓN
Javascript es un lenguaje de programación interpretado que se utiliza
principalmente para crear páginas Web capaces de interactuar con el usuario.
Las páginas estáticas solo muestran contenido; con JavaScript aportan dinamismo
en el cliente (navegador), sin intercambio de datos con el servidor.
"""


def test_strip_document_front_matter_toc_keeps_unidad_1_body():
    from core.shared.utils.chunking_utils import strip_document_front_matter_toc

    hybrid = (
        TOC_SAMPLE
        + "\n\nUNIDAD 1 - INTRODUCCIÓN\n"
        + "1.1 - ¿QUÉ ES JAVASCRIPT?\n"
        + "Javascript es un lenguaje de programación interpretado que se utiliza "
        + "principalmente para crear páginas Web capaces de interactuar con el usuario. "
        + "Las páginas Web se consideran estáticas cuando se limitan a mostrar un contenido "
        + "y los procesos se ejecutan en el cliente sin intercambio de datos con el servidor.\n"
    )
    cleaned = strip_document_front_matter_toc(hybrid)
    assert "Tabla de Contenido" not in cleaned
    assert "UNIDAD 2" not in cleaned
    assert "interpretado" in cleaned
    assert "estáticas" in cleaned
    assert "servidor" in cleaned


def test_strip_interior_book_index_keeps_prologue_and_chapter_body():
    from core.shared.utils.chunking_utils import strip_document_front_matter_toc

    hybrid = (
        "Daron Acemoglu es catedrático en el MIT y ha escrito Why Nations Fail.\n"
        "Índice general\n"
        "PARTE I Introducción a la economía     2\n"
        "Capítulo   1    Principios y práctica de la economía     2\n"
        "Capítulo   2    Métodos económicos     20\n"
        "Capítulo  13   Teoría de juegos y Nash     300\n"
        "Capítulo  20   Modelo de Solow     454\n"
        "Capítulo  21   Crecimiento     480\n"
        "Capítulo  22   Inflación     500\n"
        "Capítulo  23   Desempleo     520\n"
        "Capítulo  24   Economía abierta     540\n"
        "Índice detallado\n"
        "Prólogo\n"
        "Nos encanta la economía. Nos maravilla cómo funcionan los sistemas económicos.\n"
        "La economía es el estudio de las decisiones de la gente. El primer principio "
        "es que la gente intenta optimizar: procuran elegir la mejor opción disponible.\n"
    )
    cleaned = strip_document_front_matter_toc(hybrid)
    assert "Teoría de juegos y Nash" not in cleaned
    assert "Modelo de Solow" not in cleaned
    assert "Nos encanta la economía" in cleaned
    assert "intenta optimizar" in cleaned
    assert "catedrático" in cleaned


def test_strip_wrapped_indice_detallado_without_leader_dots():
    from core.shared.utils.chunking_utils import strip_document_front_matter_toc

    hybrid = (
        "Daron Acemoglu es catedrático en el Departamento de Economía del MIT.\n"
        "Índice detallado \n"
        "Economía basada en la evidencia:     \n"
        "¿Cuánto aumenta el sueldo medio si la ley obliga \n"
        "a un año más de educación?     29     \n"
        "2.3   Preguntas y respuestas de economía     30  \n"
        "   Resumen     32   \n"
        "Términos clave        32   \n"
        "   Preguntas     32   \n"
        "   Problemas     33    \n"
        "Capítulo 13   Teoría de juegos y Nash     300\n"
        "Capítulo 20   Modelo de Solow     454\n"
        "Capítulo 21   Crecimiento     480\n"
        "Capítulo 22   Inflación     500\n"
        "Prólogo\n"
        "Nos encanta la economía. Nos maravilla cómo funcionan los sistemas económicos. "
        "La economía es el estudio de las decisiones de la gente y el primer principio "
        "es que la gente intenta optimizar.\n"
    )
    cleaned = strip_document_front_matter_toc(hybrid)
    assert "Teoría de juegos y Nash" not in cleaned
    assert "Modelo de Solow" not in cleaned
    assert "Nos encanta la economía" in cleaned
    assert "catedrático" in cleaned


def test_strip_leading_toc_keeps_body_prose():
    from core.shared.utils.chunking_utils import strip_leading_toc

    hybrid = (
        TOC_SAMPLE
        + "\n\nUNIDAD 1 - INTRODUCCIÓN\n"
        + "Javascript es un lenguaje de programación interpretado que se utiliza "
        + "principalmente para crear páginas Web capaces de interactuar con el usuario.\n"
    )
    cleaned = strip_leading_toc(hybrid)
    assert "Tabla de Contenido" not in cleaned
    assert "interpretado" in cleaned
    assert "UNIDAD 2" not in cleaned


def test_is_table_of_contents_chunk_detects_leader_dots():
    assert is_table_of_contents_chunk(TOC_SAMPLE)
    assert not is_table_of_contents_chunk(BODY_SAMPLE)


def test_extract_toc_entry_labels_finds_units():
    labels = extract_toc_entry_labels(TOC_SAMPLE)
    joined = " ".join(labels).upper()
    assert "UNIDAD 1" in joined
    assert "UNIDAD 2" in joined


@pytest.mark.asyncio
async def test_generate_summary_chunk_skips_llm_for_toc():
    service = SummaryService()
    service.history_token_model = HistoryTokenModel(
        summary_level=SummaryLevel.VERY_DETAILED.value
    )
    service.client = MagicMock()
    service.provider_executor = MagicMock()
    service.provider_executor.execute = AsyncMock(
        side_effect=AssertionError("TOC chunk must not call the LLM")
    )

    with patch("core.brevio.services.summary_service.dump_audit"):
        index, summary, tokens = await service.generate_summary_chunk(
            0,
            TOC_SAMPLE,
            "MAP PROMPT",
            ModelType.GPT_4O_MINI,
            LanguageType.SPANISH,
            total_document_tokens=4000,
        )

    assert index == 0
    assert tokens == 0
    assert summary is not None
    assert "ÍNDICE ÚNICAMENTE" in summary
    assert "UNIDAD 1" in summary.upper()
    service.provider_executor.execute.assert_not_called()


def test_is_toc_map_stub_detects_language_prefixes():
    from core.shared.utils.chunking_utils import is_toc_map_stub

    assert is_toc_map_stub(
        "ÍNDICE ÚNICAMENTE — este fragmento es una tabla de contenidos"
    )
    assert is_toc_map_stub("INDEX ONLY — this fragment is a table of contents")
    assert not is_toc_map_stub(
        "La economía es el estudio de cómo los agentes asignan recursos."
    )


def test_reduce_drops_toc_stubs_and_keeps_body():
    from core.brevio.services.summary_service import ReduceChunk, SummaryService

    stubs = [
        ReduceChunk(
            text="ÍNDICE ÚNICAMENTE — Lista: Capítulo 20 Solow; Nash.",
            source_chunk_indices=[0],
            tokens=20,
        ),
        ReduceChunk(
            text="La economía estudia cómo los agentes asignan recursos escasos.",
            source_chunk_indices=[1],
            tokens=18,
        ),
    ]
    kept = SummaryService._reduce_chunks_without_toc_stubs(stubs)
    assert len(kept) == 1
    assert "escasos" in kept[0].text
    assert "Solow" not in kept[0].text
