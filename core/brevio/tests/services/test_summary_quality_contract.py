"""Artifact quality contract: COMPLETED requires a real summary, not plumbing success."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.summary_pipeline import (
    ArtifactQualityError,
    SummaryArtifactManager,
)
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.utils.adaptive_salience_policy import AdaptiveSaliencePolicy
from core.shared.utils.chunking_utils import (
    extract_document_outline,
    last_toc_strip_stats,
    strip_document_front_matter_toc,
)
from core.shared.utils.summary_quality import (
    QualitySignals,
    choose_deliverable_text,
    count_words,
    evaluate_artifact,
    looks_like_assistant_chat,
    looks_truncated,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CHATBOT = (FIXTURES / "asyncio_chatbot_summary.md").read_text(encoding="utf-8")
VALID = (FIXTURES / "asyncio_valid_summary.md").read_text(encoding="utf-8")

ASYNCIO_SOURCE_WORDS = 46_348
ASYNCIO_MAP_WORDS = 7_298
ASYNCIO_SOURCE_TOKENS = 70_617
ASYNCIO_MAP_TOKENS = 23_157
ASYNCIO_MIN_TOKENS = 4_505


def _asyncio_signals(**overrides) -> QualitySignals:
    payload = dict(
        source_tokens=ASYNCIO_SOURCE_TOKENS,
        source_words=ASYNCIO_SOURCE_WORDS,
        map_tokens=ASYNCIO_MAP_TOKENS,
        map_words=ASYNCIO_MAP_WORDS,
        output_min_tokens=ASYNCIO_MIN_TOKENS,
        output_target_tokens=8_192,
        output_hard_limit=8_192,
        summary_level=SummaryLevel.MODERATE,
        route="hierarchical",
    )
    payload.update(overrides)
    return QualitySignals(**payload)


def test_a_normal_summary_is_deliverable():
    report = evaluate_artifact(
        VALID,
        _asyncio_signals(
            final_words=count_words(VALID),
            final_tokens=max(1, len(VALID) // 4),
        ),
    )
    assert report.deliverable
    assert "assistant_chat" not in report.reasons


def test_b_and_k_long_document_keeps_reasonable_map_ratio():
    report = evaluate_artifact(
        VALID,
        _asyncio_signals(
            final_words=count_words(VALID),
            final_tokens=max(1, len(VALID) // 4),
        ),
    )
    assert report.map_ratio > 0.22
    assert report.source_ratio > 0.03


def test_c_extremely_short_output_fails():
    report = evaluate_artifact(
        "Too short.", _asyncio_signals(final_words=2, final_tokens=8)
    )
    assert not report.deliverable
    assert any(
        "map_collapse" in reason or "source_collapse" in reason or "below_" in reason
        for reason in report.reasons
    )


def test_short_clip_changelog_artifact_passes_capped_output_min():
    """Regression for folder_id 6aa98ec597a3c29b27d8921c (below_output_min:1071<1316)."""
    policy = AdaptiveSaliencePolicy()
    decision = policy.budget(
        ModelType.QWEN3_14B, SummaryLevel.MODERATE, 7834, LanguageType.ENGLISH
    )
    # Synthetic body sized like the failed REDUCE (~1071 tokens / ~647 words).
    body = ("Computer science covers algorithms, systems, and applications. " * 110).strip()
    report = evaluate_artifact(
        body,
        QualitySignals(
            source_tokens=7834,
            source_words=5200,
            map_tokens=1301,
            map_words=780,
            final_tokens=1071,
            final_words=count_words(body),
            output_min_tokens=decision.output_min_tokens,
            output_target_tokens=decision.output_target_tokens,
            output_hard_limit=decision.output_hard_limit,
            summary_level=SummaryLevel.MODERATE,
            route="hierarchical",
        ),
    )
    assert decision.output_min_tokens <= 2200
    assert int(decision.output_min_tokens * 0.40) <= 1071
    assert report.deliverable
    assert not any(reason.startswith("below_output_min:") for reason in report.reasons)


def test_d_chatbot_output_fails_and_can_be_salvaged():
    assert looks_like_assistant_chat(CHATBOT)
    report = evaluate_artifact(
        CHATBOT,
        _asyncio_signals(final_words=count_words(CHATBOT), final_tokens=812),
    )
    assert not report.deliverable
    assert "assistant_chat" in report.reasons

    chosen, salvage = choose_deliverable_text(
        [("proposed", CHATBOT), ("map_extracts", VALID)],
        _asyncio_signals(),
    )
    assert salvage.deliverable
    assert salvage.verdict.value == "SALVAGED"
    assert chosen == VALID
    assert looks_like_assistant_chat(chosen) is False


def test_e_truncated_tail_is_detected():
    text = "Asyncio usa un event loop para programar tareas, " * 20
    text = text.rstrip() + ","
    assert looks_truncated(text)


def test_f_length_placeholder_is_detected():
    assert looks_truncated("El resumen continúa [texto truncado]")


@pytest.mark.asyncio
async def test_g_ocr_failed_pages_are_recorded():
    from core.brevio.managers.directory_manager import ExtractionReport

    report = ExtractionReport(
        extractor="generation",
        pages_total=10,
        pages_extracted=10,
        pages_empty=2,
        pages_ocr=1,
        pages_ocr_failed=1,
        pages_dropped=1,
        characters_extracted=100,
        tokens_extracted=40,
        notes=["page 3: OCR failed (tesseract missing)"],
    )
    assert report.pages_ocr_failed == 1
    assert report.pages_dropped == 1
    assert any("OCR" in note for note in report.notes)


def test_h_excessive_toc_strip_without_index_is_rejected():
    body = (
        "Este capitulo desarrolla la teoria economica con ejemplos y casos. " * 80
    ) + "\n"
    fake_front = ("Titulo accidental 12\n" * 80) + body
    cleaned = strip_document_front_matter_toc(fake_front)
    stats = last_toc_strip_stats()
    assert stats["drop_ratio"] < 0.35 or stats["applied"] is False
    assert "teoria economica" in cleaned or stats["applied"] is False


def test_i_requested_model_budget_follows_configuration():
    qwen = AdaptiveSaliencePolicy().budget(
        ModelType.QWEN3_14B, SummaryLevel.MODERATE, 70_617, LanguageType.SPANISH
    )
    flash = AdaptiveSaliencePolicy().budget(
        ModelType.DEEPSEEK_FLASH, SummaryLevel.MODERATE, 70_617, LanguageType.SPANISH
    )
    assert qwen.output_hard_limit == 8192
    assert flash.output_hard_limit == 16_384
    assert qwen.requires_section_assembly is True


def test_j_spanish_intermediate_reduce_emits_min_words_like_english():
    from core.shared.utils.adaptive_salience_policy import (
        intermediate_reduce_instruction,
    )

    es = intermediate_reduce_instruction(6000, 0.55, language=LanguageType.SPANISH)
    en = intermediate_reduce_instruction(6000, 0.55, language=LanguageType.ENGLISH)
    assert "al menos" in es.lower()
    assert "write at least" in en.lower()
    assert "no rellenes repetiendo párrafos para alcanzar un mínimo" not in es.lower()


@pytest.mark.asyncio
async def test_l_quality_gate_reads_partial_not_an_empty_variable(tmp_path):
    """The gate inspects the file that would become summary.md."""
    summary_path = tmp_path / "summary.md"
    manager = SummaryArtifactManager(str(summary_path))
    await manager.replace_partial(CHATBOT)
    on_disk = await manager.read_partial_text()
    assert on_disk.strip() == CHATBOT.strip()
    report = evaluate_artifact(
        on_disk,
        _asyncio_signals(final_words=count_words(on_disk), final_tokens=812),
    )
    assert not report.deliverable
    assert "assistant_chat" in report.reasons


@pytest.mark.asyncio
async def test_asyncio_chatbot_cannot_be_committed(tmp_path):
    summary_path = tmp_path / "summary.md"
    manager = SummaryArtifactManager(str(summary_path))
    await manager.replace_partial(CHATBOT)
    service = SummaryService()
    encoder = MagicMock()
    encoder.encode.side_effect = lambda text: list(range(max(1, len(text) // 4)))
    decision = AdaptiveSaliencePolicy().budget(
        ModelType.QWEN3_14B,
        SummaryLevel.MODERATE,
        ASYNCIO_SOURCE_TOKENS,
        LanguageType.SPANISH,
    )
    with pytest.raises(ArtifactQualityError):
        await service._enforce_artifact_quality_gate(
            manager,
            encoder=encoder,
            file_tokens=ASYNCIO_SOURCE_TOKENS,
            source_words=ASYNCIO_SOURCE_WORDS,
            map_words=ASYNCIO_MAP_WORDS,
            map_tokens=ASYNCIO_MAP_TOKENS,
            map_salvage_text="",
            decision=decision,
            summary_level=SummaryLevel.MODERATE,
        )
    assert not summary_path.exists()
    assert Path(str(summary_path) + ".partial").exists()


@pytest.mark.asyncio
async def test_asyncio_chatbot_is_salvaged_to_valid_map_extracts(tmp_path):
    summary_path = tmp_path / "summary.md"
    manager = SummaryArtifactManager(str(summary_path))
    await manager.replace_partial(CHATBOT)
    service = SummaryService()
    encoder = MagicMock()
    encoder.encode.side_effect = lambda text: list(range(max(1, len(text or "") // 4)))
    decision = AdaptiveSaliencePolicy().budget(
        ModelType.QWEN3_14B,
        SummaryLevel.MODERATE,
        ASYNCIO_SOURCE_TOKENS,
        LanguageType.SPANISH,
    )
    await service._enforce_artifact_quality_gate(
        manager,
        encoder=encoder,
        file_tokens=ASYNCIO_SOURCE_TOKENS,
        source_words=ASYNCIO_SOURCE_WORDS,
        map_words=ASYNCIO_MAP_WORDS,
        map_tokens=ASYNCIO_MAP_TOKENS,
        map_salvage_text=VALID,
        decision=decision,
        summary_level=SummaryLevel.MODERATE,
    )
    salvaged = await manager.read_partial_text()
    assert looks_like_assistant_chat(salvaged) is False
    assert count_words(salvaged) == count_words(VALID)
    assert service.history_token_model.quality_verdict == "SALVAGED"
    await manager.commit_final()
    committed = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "¿Qué necesitas?" not in committed
    assert count_words(committed) >= 3000


def test_code_filenames_are_not_a_document_outline():
    text = "# threadmem.py\n\nprint(1)\n\n# quickstart.py\n\nprint(2)\n"
    assert extract_document_outline(text) == []


def test_real_markdown_headings_remain_an_outline():
    text = "# Main Title\n\n## Alpha Section\n\nbody\n\n## Beta Section\n\nmore\n"
    outline = extract_document_outline(text)
    assert "# Main Title" in outline
    assert "## Alpha Section" in outline


def test_looks_like_assistant_chat_on_service_delegates():
    service = SummaryService()
    assert service._looks_like_assistant_chat(CHATBOT)
    assert not service._looks_like_assistant_chat(VALID[:800])


def _asyncio_audit_dir() -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / "benchmark" / "full_corpus" / "audit" / "6aa8359c7fdf55f93dee04c0"


def test_asyncio_real_map_extracts_salvage_the_chatbot_job():
    audit = _asyncio_audit_dir()
    maps = sorted(audit.glob("*_02_MAP_OUTPUT_summary_*.txt"))
    if len(maps) < 26:
        pytest.skip("benchmark audit artifacts are not present")
    assert len(maps) == 26
    map_join = "\n\n".join(path.read_text(encoding="utf-8") for path in maps)
    chosen, salvage = choose_deliverable_text(
        [("proposed", CHATBOT), ("map_extracts", map_join)],
        _asyncio_signals(),
    )
    assert looks_like_assistant_chat(CHATBOT)
    assert salvage.deliverable
    assert salvage.verdict.value == "SALVAGED"
    assert chosen == map_join
    assert count_words(chosen) >= 7000
    assert looks_like_assistant_chat(chosen) is False


def test_h3_l1_reduce_payload_gets_packing_slack_not_silent_overflow():
    import tiktoken

    from core.brevio.services.summary_pipeline import ContextOverflowError

    audit = _asyncio_audit_dir()
    l1_path = next(audit.glob("*_03_REDUCE_L1_IN_batch1_depth0_.txt"), None)
    l2_path = next(audit.glob("*_03_REDUCE_L2_IN_batch1_depth0_.txt"), None)
    if l1_path is None or l2_path is None:
        pytest.skip("benchmark audit artifacts are not present")
    assert l1_path is not None
    assert l2_path is not None
    l1 = l1_path.read_text(encoding="utf-8")
    l2 = l2_path.read_text(encoding="utf-8")
    encoder = tiktoken.get_encoding("cl100k_base")
    service = SummaryService()
    system_tokens = 795
    l1_tokens = len(encoder.encode(l1))
    l2_tokens = len(encoder.encode(l2))
    l1_limit = service._safe_completion_token_limit(
        ModelType.QWEN3_14B, system_tokens, l1_tokens, 8192
    )
    l2_limit = service._safe_completion_token_limit(
        ModelType.QWEN3_14B, system_tokens, l2_tokens, 8192
    )
    assert l1_tokens > 5000
    assert l1_limit < 8192
    assert l2_limit == 8192
    with pytest.raises(ContextOverflowError):
        service._safe_completion_token_limit(
            ModelType.QWEN3_14B,
            system_tokens=2000,
            user_tokens=14_000,
            requested_output_tokens=8192,
        )


def test_ablation_map_prompt_no_longer_says_stop_early():
    from core.brevio.constants.prompts import ENGLISH, SPANISH

    es = SPANISH.get_map_closing_instruction().lower()
    en = ENGLISH.get_map_closing_instruction().lower()
    assert "detente" not in es
    assert "no te detengas pronto" in es or "no te detengas" in es
    assert "do not stop early" in en
    assert "and stop" not in en


def test_ablation_packing_changes_qwen_output_budget():
    service = SummaryService()
    packed = service._safe_completion_token_limit(ModelType.QWEN3_14B, 800, 6000, 8192)
    unpacked = service._safe_completion_token_limit(
        ModelType.DEEPSEEK_V4_PRO, 800, 6000, 8192
    )
    assert packed < unpacked


def test_ablation_section_assembly_vs_clipped_native_max():
    policy = AdaptiveSaliencePolicy()
    assembled = policy.budget(
        ModelType.QWEN3_14B, SummaryLevel.MODERATE, 70_617, LanguageType.SPANISH
    )
    clipped_would_be = 8192
    assert assembled.output_target_tokens > clipped_would_be
    assert assembled.requires_section_assembly is True
    assert assembled.output_hard_limit == clipped_would_be


def test_estimation_extractor_is_not_generation():
    from core.brevio.managers.directory_manager import ExtractionReport
    from core.brevio_api.services.estimation.document_extraction_service import (
        ExtractedDocument,
    )

    estimate = ExtractedDocument(
        filename="book.pdf",
        extension="pdf",
        text="hello",
        extraction_status="partial",
        pages_total=166,
        pages_with_text=158,
        pages_without_text=8,
    )
    generation = ExtractionReport(
        extractor="generation",
        pages_total=166,
        pages_extracted=166,
        pages_empty=8,
        pages_ocr=0,
        pages_ocr_failed=8,
        pages_dropped=8,
    )
    assert estimate.extractor == "estimation"
    assert generation.extractor == "generation"
    assert estimate.pages_total == generation.pages_total
    assert (
        estimate.pages_with_text != generation.pages_extracted
        or generation.pages_ocr_failed
    )


def test_asyncio_gold_topics_survive_valid_not_chatbot():
    from benchmarks.summary_pipeline.gold import gold_for_document, match_topics

    gold = gold_for_document("using-asyncio.pdf")
    assert gold is not None
    chatbot_present, _ = match_topics(gold["important_topics"], CHATBOT)
    valid_present, _ = match_topics(gold["important_topics"], VALID)
    assert len(valid_present) >= len(chatbot_present)
    assert len(valid_present) >= 3
