"""Contract and chaos tests for the real document summary pipeline."""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.summary_pipeline import (
    PipelineOutcome,
    PipelinePhase,
    SummaryArtifactManager,
    gather_or_cancel,
)
from core.brevio.services.summary_service import (
    MapChunkResult,
    MapPhaseFailedError,
    ReduceConvergenceError,
    SummaryService,
)
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )
    monkeypatch.setenv("BREVIO_KEEP_PARTIALS", "false")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")


@pytest.fixture
def service():
    return SummaryService()


def _prompt_config() -> PromptConfig:
    return PromptConfig(
        model=ModelType.DEEPSEEK_V4_PRO,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=SummaryLevel.MODERATE,
    )


def _file_config(tmp_path, name: str = "doc.pdf") -> FileConfig:
    return FileConfig(
        document_path=str(tmp_path / name),
        summary_path=str(tmp_path / "summary.md"),
        transcription_path=str(tmp_path / "t.txt"),
    )


def _maps(*texts: str) -> list[MapChunkResult]:
    return [
        MapChunkResult(i, f"original-{i} recoverable {text}", "SUCCESS", text)
        for i, text in enumerate(texts)
    ]


def _document_patches(service, *, chunks, map_impl, reduce_impl, format_impl):
    decision = MagicMock()
    decision.route = "hierarchical"
    decision.output_target_tokens = 80
    policy_patch = patch("core.brevio.services.summary_service.AdaptiveSaliencePolicy")
    patches = [
        patch.object(service, "chunk_text", new=AsyncMock(return_value=chunks)),
        patch.object(service, "run_map_phase", side_effect=map_impl),
        patch.object(service, "run_reduce_phase", side_effect=reduce_impl),
        patch.object(service, "run_formatting_phase", side_effect=format_impl),
        patch.object(service.directory_manager, "validate_paths", new=AsyncMock()),
        patch.object(
            service.directory_manager,
            "read_pdf",
            new=AsyncMock(return_value=["hello world " * 40]),
        ),
        patch.object(
            service, "detect_language_with_retry_safe", new=AsyncMock(return_value="en")
        ),
        patch.object(
            service.advanced_prompt_generator,
            "get_map_prompt",
            new=AsyncMock(return_value="m"),
        ),
        patch.object(
            service.advanced_prompt_generator,
            "get_reduce_prompt",
            new=AsyncMock(return_value="r"),
        ),
        patch.object(
            service.advanced_prompt_generator,
            "get_format_prompt",
            new=AsyncMock(return_value="format only"),
        ),
        policy_patch,
    ]
    return patches, policy_patch, decision


async def _run_document(service, tmp_path):
    file_config = _file_config(tmp_path)
    return await service._process_single_document(
        "formatting prompt",
        file_config,
        ModelType.DEEPSEEK_V4_PRO,
        _prompt_config(),
        folder_id="fold",
        user_id="user",
    )


@pytest.mark.asyncio
async def test_1_map_success_reduce_format_success(service, tmp_path):
    chunks = ["alpha chunk text here", "beta chunk text here"]
    map_results = _maps("SUMMARY ALPHA enough", "SUMMARY BETA enough")

    async def fake_map(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            await callback("\n".join(item.summary_text for item in map_results))
        return map_results, 20

    async def fake_reduce(mapped, *args, **kwargs):
        assert all(isinstance(item, MapChunkResult) for item in mapped)
        return "REDUCED BODY FROM MAP", 8

    async def fake_format(text, *args, **kwargs):
        assert text == "REDUCED BODY FROM MAP"
        return "FORMATTED FINAL SUMMARY", 4

    patches, policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=fake_format,
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    partial_path = tmp_path / "summary.md.partial"
    assert resp.success is True
    assert resp.status == "COMPLETED"
    assert resp.job_phase == "COMPLETED"
    assert resp.phase == PipelinePhase.SUCCESS.value
    assert summary_path.exists()
    assert "FORMATTED FINAL SUMMARY" in summary_path.read_text()
    assert not partial_path.exists()
    assert not (tmp_path / "summary.md.map.partial").exists()
    assert resp.partial_available is False


@pytest.mark.asyncio
async def test_format_skipped_when_below_min_tokens(service, tmp_path, monkeypatch):
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "10000")
    chunks = ["alpha chunk text here"]
    map_results = _maps("SUMMARY ALPHA enough")
    format_called = {"n": 0}

    async def fake_map(*args, **kwargs):
        return map_results, 10

    async def fake_reduce(*args, **kwargs):
        return "REDUCED BODY FROM MAP", 8

    async def fake_format(*args, **kwargs):
        format_called["n"] += 1
        raise AssertionError("FORMAT must be skipped")

    patches, policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=fake_format,
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is True
    assert format_called["n"] == 0
    assert "REDUCED BODY FROM MAP" in (tmp_path / "summary.md").read_text()


@pytest.mark.asyncio
async def test_2_map_mixed_success_failed_does_not_enter_reduce(service):
    mapped = [
        MapChunkResult(0, "ORIG0 long enough text", "SUCCESS", "SUMMARY0 enough"),
        MapChunkResult(
            1, "ORIG1 must survive into reduce", "FAILED", None, "provider 429"
        ),
    ]

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", new=AsyncMock()
    ) as mock_reduce, patch.object(
        service, "_check_token_limit", return_value=True
    ):
        service.history_token_model.summary_level = SummaryLevel.MODERATE.value
        service.history_token_model.num_tokens_file = 100
        with pytest.raises(MapPhaseFailedError):
            await service.run_reduce_phase(
                mapped,
                "reduce prompt",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )
        mock_reduce.assert_not_called()


@pytest.mark.asyncio
async def test_3_wrong_type_between_phases_is_invariant(service, tmp_path):
    chunks = ["a chunk", "b chunk"]

    async def fake_map(*args, **kwargs):
        return ["legacy-string-not-dto", "another"], 10

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=AsyncMock(return_value=("should-not-run", 1)),
        format_impl=AsyncMock(return_value=("should-not-run", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is False
    assert resp.error_type == "InvariantViolationError"
    assert resp.phase == PipelinePhase.INVARIANT_FAILED.value
    assert not (tmp_path / "summary.md").exists()


@pytest.mark.asyncio
async def test_4_reduce_failure_cleans_partials(service, tmp_path):
    chunks = ["alpha chunk text here", "beta chunk text here"]
    map_results = _maps("MAP PROGRESS ALPHA", "MAP PROGRESS BETA")

    async def fake_map(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            await callback("MAP PROGRESS ALPHA\nMAP PROGRESS BETA")
        return map_results, 20

    async def fake_reduce(*args, **kwargs):
        raise ReduceConvergenceError(
            "Intermediate REDUCE failed to compress batch 7 at level 1. Max split depth reached.",
            phase=PipelinePhase.REDUCE_FAILED.value,
            batch_index=7,
            reduce_level=1,
            split_depth=16,
            finish_reason="length",
        )

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=AsyncMock(return_value=("nope", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    partial = tmp_path / "summary.md.partial"
    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "REDUCE"
    assert resp.phase == PipelinePhase.REDUCE_FAILED.value
    assert resp.error_type == "ReduceConvergenceError"
    assert resp.partial_available is False
    assert not (tmp_path / "summary.md").exists()
    assert not partial.exists()
    assert resp.diagnostics["batch_index"] == 7
    assert resp.diagnostics["reduce_level"] == 1


@pytest.mark.asyncio
async def test_5_reduce_fails_without_recoverable_progress(service, tmp_path):
    chunks = ["alpha chunk text here"]

    async def fake_map(*args, **kwargs):
        return [
            MapChunkResult(0, "original failed chunk text", "FAILED", None, "provider"),
        ], 0

    async def fake_reduce(*args, **kwargs):
        raise ReduceConvergenceError(
            "no progress",
            phase=PipelinePhase.REDUCE_FAILED.value,
            batch_index=1,
            reduce_level=1,
        )

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=AsyncMock(return_value=("nope", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "MAP"
    assert resp.phase == PipelinePhase.MAP_FAILED.value
    assert resp.partial_available is False
    assert not (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()


@pytest.mark.asyncio
async def test_6_format_failure_cleans_partials(service, tmp_path):
    chunks = ["alpha chunk text here"]
    map_results = _maps("MAP TEXT")

    async def fake_map(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            await callback("MAP TEXT")
        return map_results, 10

    async def fake_reduce(*args, **kwargs):
        return "REDUCED RECOVERABLE TEXT", 6

    async def fake_format(*args, **kwargs):
        raise RuntimeError("formatter exploded")

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=fake_format,
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    partial = tmp_path / "summary.md.partial"
    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "FORMAT"
    assert resp.phase == PipelinePhase.FORMAT_FAILED.value
    assert not (tmp_path / "summary.md").exists()
    assert not partial.exists()
    assert resp.partial_available is False


@pytest.mark.asyncio
async def test_7_cleanup_exception_does_not_destroy_final(service, tmp_path):
    chunks = ["alpha chunk text here"]
    map_results = _maps("MAP TEXT")

    async def fake_map(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            await callback("MAP TEXT")
        return map_results, 10

    original_remove = SummaryArtifactManager._remove_file

    async def exploding_remove(self, path: str):
        if str(path).endswith(".partial"):
            raise OSError("cleanup boom")
        return await original_remove(self, path)

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=chunks,
        map_impl=fake_map,
        reduce_impl=AsyncMock(return_value=("REDUCED", 4)),
        format_impl=AsyncMock(return_value=("FINAL SUMMARY BODY", 3)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        stack.enter_context(
            patch.object(SummaryArtifactManager, "_remove_file", exploding_remove)
        )
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    summary_path = tmp_path / "summary.md"
    assert resp.success is True
    assert summary_path.exists()
    assert "FINAL SUMMARY BODY" in summary_path.read_text()


@pytest.mark.asyncio
async def test_8_reduce_batch_failure_cancels_siblings_and_keeps_root(service):
    mapped = _maps(
        "BoomBatch distinctive text here",
        "SlowBatch distinctive text here",
        "OtherBatch distinctive",
    )
    cancelled_slow = asyncio.Event()

    async def fake_execute(batch_text, *args, **kwargs):
        if "BoomBatch" in batch_text:
            await asyncio.sleep(0.02)
            raise ReduceConvergenceError(
                "root boom",
                phase=PipelinePhase.REDUCE_FAILED.value,
                batch_index=1,
                reduce_level=1,
            )
        try:
            await asyncio.sleep(20)
        except asyncio.CancelledError:
            cancelled_slow.set()
            raise
        return "ok", 1, "stop"

    service._reduce_batch_token_limit = lambda *args, **kwargs: 8
    service.history_token_model.summary_level = SummaryLevel.MODERATE.value
    service.history_token_model.user_id = "user"
    service.history_token_model.num_tokens_file = 50

    start = time.time()
    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", side_effect=fake_execute
    ), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        with pytest.raises(ReduceConvergenceError) as exc:
            await service.run_reduce_phase(
                mapped,
                "reduce prompt",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )
    elapsed = time.time() - start
    assert elapsed < 5
    assert "root boom" in str(exc.value)
    assert type(exc.value).__name__ == "ReduceConvergenceError"


@pytest.mark.asyncio
async def test_9_max_split_depth_has_full_diagnostics(service):
    mapped = [MapChunkResult(0, "x" * 400, "SUCCESS", "Y" * 400)]

    async def always_length(*args, **kwargs):
        return "truncated-output", 3, "length"

    def always_split(text, max_tokens, encoder, depth=0):
        if len(text) <= 4:
            return [text]
        mid = max(1, len(text) // 2)
        return [text[:mid], text[mid:]]

    service.history_token_model.summary_level = SummaryLevel.MODERATE.value
    service.history_token_model.user_id = "user"
    service.history_token_model.num_tokens_file = 400

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(
        service, "_split_markdown_structurally", side_effect=always_split
    ), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        try:
            result = await service.run_reduce_phase(
                mapped,
                "reduce prompt",
                ModelType.DEEPSEEK_V4_PRO,
                LanguageType.ENGLISH,
                force_reduce=True,
            )
        except ReduceConvergenceError as err:
            assert err.diagnostics["reason"] in {
                "max_split_depth",
                "indivisible_input",
                "non_progress_split",
                "final_join_cap",
                "final_join_unmergeable",
            }
            assert err.diagnostics["batch_index"] == 1
            assert err.diagnostics.get("reduce_level", 1) >= 1
            assert err.diagnostics["finish_reason"] in {"length", "stop"}
            return

    assert "Y" in result.text
    assert result.text.strip() != "truncated-output"


@pytest.mark.asyncio
async def test_10_indivisible_input_fails_explicitly(service):
    dense = "Distinctive market-equilibrium claim with numbers and names. " * 80
    mapped = [MapChunkResult(0, dense, "SUCCESS", dense)]

    async def always_length(*args, **kwargs):
        return "cut", 2, "length"

    def no_split(text, *args, **kwargs):
        return [text]

    service.history_token_model.summary_level = SummaryLevel.MODERATE.value
    service.history_token_model.user_id = "user"
    service.history_token_model.num_tokens_file = 2000

    with patch.object(
        service.api_service, "_initialize_client", new=AsyncMock()
    ), patch.object(
        service, "_execute_reduce_call", side_effect=always_length
    ), patch.object(
        service, "_split_markdown_structurally", side_effect=no_split
    ), patch.object(
        service, "_check_token_limit", return_value=True
    ):
        result = await service.run_reduce_phase(
            mapped,
            "reduce prompt",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
            force_reduce=True,
        )

    assert result.finish_reason == "stop"
    assert "market-equilibrium" in result.text
    assert result.text.strip() != "cut"


@pytest.mark.asyncio
async def test_11_empty_partial_is_never_recoverable(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    assert await manager.write_partial("   \n") is False
    assert not os.path.exists(manager.partial_path)
    empty = tmp_path / "summary.md.partial"
    empty.write_text("")
    assert await manager.has_recoverable_partial() is False
    assert not empty.exists()


@pytest.mark.asyncio
async def test_12_full_success_removes_partial(service, tmp_path):
    await test_1_map_success_reduce_format_success(service, tmp_path)


@pytest.mark.asyncio
async def test_gather_or_cancel_preserves_root_and_drains_siblings():
    slow_cancelled = asyncio.Event()

    async def boom():
        await asyncio.sleep(0.01)
        raise ReduceConvergenceError("root", batch_index=2)

    async def slow():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            slow_cancelled.set()
            raise
        return "nope"

    with pytest.raises(ReduceConvergenceError) as exc:
        await gather_or_cancel(boom(), slow())
    assert "root" in str(exc.value)
    assert slow_cancelled.is_set()
    assert getattr(exc.value, "secondary_exceptions", []) == []


@pytest.mark.asyncio
async def test_budget_exceeded_during_map_fails_job(service, tmp_path):
    from core.brevio.services.provider_quota.errors import JobRequestBudgetExceededError

    async def fake_map(*args, **kwargs):
        raise JobRequestBudgetExceededError(
            "Job exceeded max provider requests (3/3) during MAP"
        )

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=["alpha chunk text here"],
        map_impl=fake_map,
        reduce_impl=AsyncMock(return_value=("nope", 1)),
        format_impl=AsyncMock(return_value=("nope", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "MAP"
    assert resp.error_type == "JobRequestBudgetExceededError"
    assert resp.phase != PipelinePhase.SUCCESS.value
    assert not (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()


@pytest.mark.asyncio
async def test_unexpected_exception_cleans_temporaries(service, tmp_path):
    async def fake_map(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            await callback("MAP PARTIAL TEXT")
        raise RuntimeError("provider exploded")

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=["alpha chunk text here"],
        map_impl=fake_map,
        reduce_impl=AsyncMock(return_value=("nope", 1)),
        format_impl=AsyncMock(return_value=("nope", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is False
    assert resp.status == "FAILED"
    assert not (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()
    assert not (tmp_path / "summary.md.map.partial").exists()


@pytest.mark.asyncio
async def test_finalize_twice_is_idempotent(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    (tmp_path / "summary.md.partial").write_text("partial", encoding="utf-8")
    (tmp_path / "summary.md.map.partial").write_text("map", encoding="utf-8")
    await manager.finalize(PipelineOutcome.FAILED_MAP, False)
    await manager.finalize(PipelineOutcome.FAILED_MAP, False)
    assert not (tmp_path / "summary.md.partial").exists()
    assert not (tmp_path / "summary.md.map.partial").exists()
    assert not (tmp_path / "summary.md").exists()


@pytest.mark.asyncio
async def test_budget_exceeded_during_reduce_fails_job(service, tmp_path):
    from core.brevio.services.provider_quota.errors import JobRequestBudgetExceededError

    async def fake_map(*args, **kwargs):
        return _maps("MAP TEXT ENOUGH"), 10

    async def fake_reduce(*args, **kwargs):
        raise JobRequestBudgetExceededError(
            "Job exceeded max provider requests (3/3) during REDUCE"
        )

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=["alpha chunk text here"],
        map_impl=fake_map,
        reduce_impl=fake_reduce,
        format_impl=AsyncMock(return_value=("nope", 1)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert resp.success is False
    assert resp.status == "FAILED"
    assert resp.job_phase == "REDUCE"
    assert resp.error_type == "JobRequestBudgetExceededError"
    assert resp.phase != PipelinePhase.SUCCESS.value
    assert not (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()


@pytest.mark.asyncio
async def test_map_recovers_from_internal_retry_then_completes(service, tmp_path):
    attempts = {"n": 0}
    map_results = _maps("SUMMARY ALPHA enough")

    async def fake_map(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            # Recoverable failure is swallowed inside MAP; the phase is not terminal yet.
            return map_results, 10
        return map_results, 10

    patches, _policy_patch, decision = _document_patches(
        service,
        chunks=["alpha chunk text here"],
        map_impl=fake_map,
        reduce_impl=AsyncMock(return_value=("REDUCED BODY FROM MAP", 8)),
        format_impl=AsyncMock(return_value=("FORMATTED FINAL SUMMARY", 4)),
    )
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patches]
        policy = entered[-1]
        policy.return_value.budget.return_value = decision
        resp = await _run_document(service, tmp_path)

    assert attempts["n"] == 1
    assert resp.success is True
    assert resp.status == "COMPLETED"
    assert resp.job_phase == "COMPLETED"
    assert (tmp_path / "summary.md").exists()
    assert not (tmp_path / "summary.md.partial").exists()


@pytest.mark.asyncio
async def test_commit_twice_does_not_duplicate_summary(tmp_path):
    manager = SummaryArtifactManager(str(tmp_path / "summary.md"))
    await manager.commit_final("first version")
    await manager.commit_final("second version")
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert text.count("second version") == 1
    assert "first version" not in text
    assert not (tmp_path / "summary.md.partial").exists()
