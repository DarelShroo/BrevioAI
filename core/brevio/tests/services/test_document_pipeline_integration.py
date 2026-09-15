"""Integration tests for the real document MAP → REDUCE → FORMAT → commit path.

LLM provider calls are faked. Pipeline functions under test are not replaced:
_process_single_document, run_map_phase, run_reduce_phase, _reduce_batch,
SummaryArtifactManager, commit_final.
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.summary_pipeline import PipelinePhase, SummaryArtifactManager
from core.brevio.services.summary_service import ReduceConvergenceError, SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKENS", "1000000")
    monkeypatch.setenv("MAX_TOKEN_PER_MINUTE", "1000000")
    monkeypatch.setenv("TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_api_key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_api_key")
    monkeypatch.setenv("MAX_TOKEN_WAIT", "1")
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")


@pytest.fixture
def service() -> SummaryService:
    svc = SummaryService()
    svc.token_bucket = 1000000
    svc.tokens_per_minute = 1000000
    svc.history_token_model.user_id = "user"
    svc.history_token_model.folder_id = "fold"
    return svc


def _prompt_config() -> PromptConfig:
    return PromptConfig(
        model=ModelType.DEEPSEEK_V4_PRO,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=SummaryLevel.MODERATE,
    )


def _file_config(tmp_path) -> FileConfig:
    return FileConfig(
        document_path=str(tmp_path / "doc.pdf"),
        summary_path=str(tmp_path / "summary.md"),
        transcription_path=str(tmp_path / "t.txt"),
    )


def _document_pages(n: int = 6, repeats: int = 400) -> list[str]:
    return [
        f"CHAPTER_{i} UNIQUE_SOURCE_{i} begins. "
        + ("empirical science methodology and experimental evidence. " * repeats)
        for i in range(n)
    ]


async def _forbidden_llm(*_args, **_kwargs):
    raise AssertionError("Real LLM client was invoked")


class _WhitespaceEncoder:
    """Local tokenizer stand-in so tests never download HuggingFace weights."""

    def encode(self, text: str):
        return text.split() if text else []

    def decode(self, tokens):
        return " ".join(str(token) for token in tokens)


def _install_llm_tripwire(service: SummaryService) -> MagicMock:
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_forbidden_llm)
    service.client = mock_client
    service.api_service._initialize_client = AsyncMock(return_value=mock_client)
    return mock_client


def _wrap_phase(service: SummaryService, order: list[str]) -> None:
    orig_map = service.run_map_phase
    orig_reduce = service.run_reduce_phase
    orig_format = service.run_formatting_phase

    async def map_wrap(*args, **kwargs):
        order.append("MAP")
        return await orig_map(*args, **kwargs)

    async def reduce_wrap(*args, **kwargs):
        order.append("REDUCE")
        return await orig_reduce(*args, **kwargs)

    async def format_wrap(*args, **kwargs):
        order.append("FORMAT")
        return await orig_format(*args, **kwargs)

    service.run_map_phase = map_wrap  # type: ignore[method-assign]
    service.run_reduce_phase = reduce_wrap  # type: ignore[method-assign]
    service.run_formatting_phase = format_wrap  # type: ignore[method-assign]


def _document_stack(
    service: SummaryService,
    *,
    pages: list[str],
    map_impl,
    reduce_impl,
    format_impl,
    extra=(),
) -> ExitStack:
    stack = ExitStack()
    decision = MagicMock()
    decision.route = "hierarchical"
    decision.output_target_tokens = 2000
    decision.output_min_tokens = 800
    decision.output_hard_limit = 8192
    decision.requires_section_assembly = False
    decision.section_keep_ratio = 0.55
    pol = stack.enter_context(
        patch("core.brevio.services.summary_service.AdaptiveSaliencePolicy")
    )
    pol.return_value.budget.return_value = decision
    stack.enter_context(
        patch(
            "core.brevio.services.summary_service.get_encoder",
            return_value=_WhitespaceEncoder(),
        )
    )
    stack.enter_context(
        patch.object(service.directory_manager, "validate_paths", new=AsyncMock())
    )
    stack.enter_context(
        patch.object(
            service.directory_manager, "read_pdf", new=AsyncMock(return_value=pages)
        )
    )
    stack.enter_context(
        patch.object(
            service, "detect_language_with_retry_safe", new=AsyncMock(return_value="en")
        )
    )
    stack.enter_context(
        patch.object(service, "generate_summary_chunk", side_effect=map_impl)
    )
    stack.enter_context(
        patch.object(service, "_execute_reduce_call", side_effect=reduce_impl)
    )
    stack.enter_context(
        patch.object(service, "_execute_formatting_call", side_effect=format_impl)
    )
    stack.enter_context(patch.object(service, "_check_token_limit", return_value=True))
    for item in extra:
        stack.enter_context(item)
    return stack


async def _run_document(service: SummaryService, tmp_path):
    return await service._process_single_document(
        "formatting prompt",
        _file_config(tmp_path),
        ModelType.DEEPSEEK_V4_PRO,
        _prompt_config(),
        folder_id="fold",
        user_id="user",
    )


@pytest.mark.asyncio
async def test_success_length_split_converges_then_format_commit(service, tmp_path):
    phase_order: list[str] = []
    reduce_calls: list[str] = []
    format_calls: list[str] = []
    commits: list[str] = []
    length_emitted = False
    _wrap_phase(service, phase_order)
    _install_llm_tripwire(service)

    orig_commit = SummaryArtifactManager.commit_final

    async def commit_wrap(self, content: str | None = None) -> None:
        commits.append(content if content is not None else "<from-partial>")
        phase_order.append("COMMIT")
        await orig_commit(self, content)

    def _dense_mock(prefix: str, repeats: int = 90) -> str:
        return prefix + " " + ("named method evidence example finding. " * repeats)

    async def map_impl(index, chunk, *args, **kwargs):
        return (
            index,
            _dense_mock(
                f"MAP_SUMMARY_{index} recovered UniqueToken{index} from source."
            ),
            20,
        )

    async def reduce_impl(batch_text, *args, **kwargs):
        nonlocal length_emitted
        reduce_calls.append(batch_text)
        is_multi = (
            batch_text.count("--- [Bloque") >= 2 or batch_text.count("--- [Block") >= 2
        )
        if is_multi and not length_emitted:
            length_emitted = True
            return "Truncated synthesis that cuts off mid", 40, "length"
        return (
            _dense_mock("Reduced synthesis covering every block in this batch."),
            80,
            "stop",
        )

    async def format_impl(text_block, *args, **kwargs):
        format_calls.append(text_block)
        out = (
            text_block
            if text_block.rstrip().endswith(".")
            else text_block.rstrip() + "."
        )
        return out, 12, "stop"

    with _document_stack(
        service,
        pages=_document_pages(),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
        extra=(patch.object(SummaryArtifactManager, "commit_final", commit_wrap),),
    ):
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    partial_path = tmp_path / "summary.md.partial"

    assert resp.success is True
    assert resp.phase == PipelinePhase.SUCCESS.value
    assert summary_path.exists()
    assert summary_path.read_text().strip()
    assert not partial_path.exists()
    assert resp.partial_available is False
    assert phase_order[:3] == ["MAP", "REDUCE", "FORMAT"]
    assert "COMMIT" in phase_order
    assert (
        phase_order.index("MAP")
        < phase_order.index("REDUCE")
        < phase_order.index("FORMAT")
    )
    assert length_emitted is True
    assert len(reduce_calls) >= 3
    assert format_calls
    assert commits
    assert "Reduced synthesis" in summary_path.read_text()


@pytest.mark.asyncio
async def test_reduce_impossible_fails_and_cleans_partials(service, tmp_path):
    phase_order: list[str] = []
    _wrap_phase(service, phase_order)
    _install_llm_tripwire(service)

    async def map_impl(index, chunk, *args, **kwargs):
        return index, f"MAP_PROGRESS_{index} recoverable distinctive facts.", 15

    async def reduce_impl(batch_text, *args, **kwargs):
        return "cut off without ending", 5, "length"

    async def format_impl(*args, **kwargs):
        raise AssertionError("FORMAT must not run after REDUCE failure")

    with _document_stack(
        service,
        pages=_document_pages(n=2, repeats=400),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
    ):
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    partial_path = tmp_path / "summary.md.partial"
    diag = resp.diagnostics or {}

    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "REDUCE"
    assert resp.phase == PipelinePhase.REDUCE_FAILED.value
    assert resp.error_type == "ReduceConvergenceError"
    assert not summary_path.exists()
    assert not partial_path.exists()
    assert resp.partial_available is False
    assert "FORMAT" not in phase_order
    assert diag.get("batch_index") is not None
    assert diag.get("reduce_level") is not None or diag.get("level") is not None
    assert diag.get("split_depth") is not None or diag.get("depth") is not None
    assert diag.get("finish_reason") == "length"


@pytest.mark.asyncio
async def test_failure_before_progress_leaves_no_empty_partial(service, tmp_path):
    _install_llm_tripwire(service)

    async def map_impl(*args, **kwargs):
        raise RuntimeError("provider exploded before any SUCCESS chunk")

    async def reduce_impl(*args, **kwargs):
        raise AssertionError("REDUCE must not run after fatal MAP")

    async def format_impl(*args, **kwargs):
        raise AssertionError("FORMAT must not run after fatal MAP")

    with _document_stack(
        service,
        pages=_document_pages(n=2, repeats=200),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
    ):
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    partial_path = tmp_path / "summary.md.partial"

    assert resp.success is False
    assert resp.partial_available is False
    assert not summary_path.exists()
    assert not partial_path.exists()


@pytest.mark.asyncio
async def test_concurrent_reduce_failure_cancels_and_drains_siblings(service, tmp_path):
    phase_order: list[str] = []
    cancelled = 0
    _wrap_phase(service, phase_order)
    _install_llm_tripwire(service)

    long_piece = "tokencontent " * 2500

    async def map_impl(index, chunk, *args, **kwargs):
        marker = "BoomBatch" if index == 0 else f"SlowBatch_{index}"
        return index, f"MAP_SUMMARY_{index} {marker} {long_piece}", 400

    async def reduce_impl(batch_text, *args, **kwargs):
        nonlocal cancelled
        if "BoomBatch" in batch_text:
            await asyncio.sleep(0.02)
            raise ReduceConvergenceError(
                "root boom",
                phase=PipelinePhase.REDUCE_FAILED.value,
                batch_index=1,
                reduce_level=1,
                split_depth=0,
                finish_reason="length",
            )
        try:
            await asyncio.sleep(20)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        return "should not finish.", 1, "stop"

    async def format_impl(*args, **kwargs):
        raise AssertionError("FORMAT must not run after REDUCE failure")

    before = {task for task in asyncio.all_tasks() if not task.done()}
    with _document_stack(
        service,
        pages=_document_pages(n=6, repeats=500),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
    ):
        resp = await _run_document(service, tmp_path)
    after = {task for task in asyncio.all_tasks() if not task.done()}
    leftover = after - before - {asyncio.current_task()}

    summary_path = tmp_path / "summary.md"
    diag = resp.diagnostics or {}

    assert resp.success is False
    assert resp.phase == PipelinePhase.REDUCE_FAILED.value
    assert resp.error_type == "ReduceConvergenceError"
    assert "root boom" in (resp.message or "") + (resp.error_message or "")
    assert not summary_path.exists()
    assert cancelled >= 1
    assert leftover == set()
    assert "FORMAT" not in phase_order
    assert diag.get("batch_index") is not None
    assert diag.get("finish_reason") == "length"


def _dense_mock(prefix: str, repeats: int = 90) -> str:
    return prefix + " " + ("named method evidence example finding. " * repeats)


@pytest.mark.asyncio
@pytest.mark.parametrize("n_pages", [1, 2, 3, 10, 25])
async def test_scaling_page_counts_commit_a_real_summary(service, tmp_path, n_pages):
    _install_llm_tripwire(service)
    repeats = 80 if n_pages >= 25 else 200

    async def map_impl(index, chunk, *args, **kwargs):
        return index, _dense_mock(f"MAP_SUMMARY_{index} UniqueToken{index}."), 20

    async def reduce_impl(batch_text, *args, **kwargs):
        return _dense_mock("Reduced synthesis covering every block."), 80, "stop"

    async def format_impl(text_block, *args, **kwargs):
        out = (
            text_block
            if text_block.rstrip().endswith(".")
            else text_block.rstrip() + "."
        )
        return out, 12, "stop"

    with _document_stack(
        service,
        pages=_document_pages(n=n_pages, repeats=repeats),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
    ):
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    assert resp.success is True, resp.message
    assert summary_path.exists()
    body = summary_path.read_text()
    assert "Reduced synthesis" in body or "MAP_SUMMARY_" in body
    assert "¿Qué necesitas?" not in body
    assert len(body.split()) >= 80


@pytest.mark.asyncio
async def test_chatbot_reduce_is_salvaged_to_map_extracts(service, tmp_path):
    chatbot = (
        Path(__file__).resolve().parents[1] / "fixtures" / "asyncio_chatbot_summary.md"
    ).read_text(encoding="utf-8")
    _install_llm_tripwire(service)

    async def map_impl(index, chunk, *args, **kwargs):
        return (
            index,
            _dense_mock(f"MAP_SUMMARY_{index} UniqueToken{index} asyncio event loop."),
            20,
        )

    async def reduce_impl(batch_text, *args, **kwargs):
        return chatbot, 40, "stop"

    async def format_impl(text_block, *args, **kwargs):
        out = (
            text_block
            if text_block.rstrip().endswith(".")
            else text_block.rstrip() + "."
        )
        return out, 12, "stop"

    with _document_stack(
        service,
        pages=_document_pages(n=4, repeats=200),
        map_impl=map_impl,
        reduce_impl=reduce_impl,
        format_impl=format_impl,
    ):
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    assert resp.success is True, resp.message
    body = summary_path.read_text()
    assert "¿Qué necesitas?" not in body
    assert "Opciones para ayudarte" not in body
    assert "MAP_SUMMARY_" in body
    assert len(body.split()) >= 180
    assert service.history_token_model.quality_verdict in {
        "VALID",
        "DEGRADED",
        "SALVAGED",
    }
