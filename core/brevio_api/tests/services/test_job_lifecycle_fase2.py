"""FASE 2 adversarial tests: claim, idempotency, recovery, no Celery bytes."""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from core.brevio_api.services.job_lifecycle import (
    JobHeartbeat,
    heartbeat_key,
    stale_processing_grace_seconds,
)
from core.brevio_api.tasks import process_summary_task
from core.shared.enums.job_status import JobStatus, can_transition_status


def test_can_transition_includes_queued():
    assert can_transition_status(None, JobStatus.QUEUED.value) is True
    assert (
        can_transition_status(JobStatus.QUEUED.value, JobStatus.PROCESSING.value)
        is True
    )
    assert (
        can_transition_status(JobStatus.QUEUED.value, JobStatus.FAILED.value) is True
    )
    assert (
        can_transition_status(JobStatus.QUEUED.value, JobStatus.COMPLETED.value)
        is False
    )
    # FASE 6: PROCESSING → QUEUED allowed for capacity yield safety path.
    assert (
        can_transition_status(JobStatus.PROCESSING.value, JobStatus.QUEUED.value)
        is True
    )
    assert (
        can_transition_status(JobStatus.COMPLETED.value, JobStatus.FAILED.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.FAILED.value, JobStatus.COMPLETED.value)
        is False
    )
    assert (
        can_transition_status(JobStatus.COMPLETED.value, JobStatus.COMPLETED.value)
        is True
    )


def test_process_summary_task_signature_is_job_id_only():
    sig = inspect.signature(process_summary_task.run)
    params = list(sig.parameters)
    assert "job_id" in params
    assert "files" not in params


def test_process_summary_task_rejects_bytes_payload():
    with pytest.raises(ValueError, match="no longer accepts file bytes"):
        process_summary_task.run(job_id="abc", files=[("a.pdf", b"%PDF")])


def test_celery_app_acks_late_configured():
    from core.brevio_api.celery import celery_app

    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert "reconcile-stale-jobs" in celery_app.conf.beat_schedule


@pytest.mark.asyncio
async def test_claim_queued_job_is_atomic_single_winner():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    job_id = str(ObjectId())
    claimed_doc = {
        "_id": ObjectId(job_id),
        "user_id": ObjectId(),
        "name": "doc",
        "results": [{"_id": ObjectId(), "index": 0, "status": "PROCESSING"}],
        "status": JobStatus.PROCESSING.value,
        "file_manifest": [],
    }
    collection = MagicMock()
    collection.find_one_and_update = AsyncMock(side_effect=[claimed_doc, None])
    repo = FolderEntryRepository(collection)

    first = await repo.claim_queued_job(job_id)
    second = await repo.claim_queued_job(job_id)
    assert first is not None
    assert first.status == JobStatus.PROCESSING.value
    assert second is None
    assert collection.find_one_and_update.await_count == 2
    filt = collection.find_one_and_update.await_args_list[0].args[0]
    assert filt["status"] == JobStatus.QUEUED.value


@pytest.mark.asyncio
async def test_upsert_data_result_by_index_does_not_duplicate():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )
    from core.shared.models.user.data_result import DataResult

    job_id = str(ObjectId())
    existing_id = ObjectId()
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(job_id),
            "results": [
                {
                    "_id": existing_id,
                    "index": 0,
                    "status": JobStatus.QUEUED.value,
                    "name": "a.pdf",
                }
            ],
        }
    )
    collection.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    repo = FolderEntryRepository(collection)

    r1 = DataResult(
        index=0,
        name="a.pdf",
        status=JobStatus.PROCESSING.value,
        success=False,
    )
    out1 = await repo.upsert_data_result_by_index(job_id, r1)
    r2 = DataResult(
        index=0,
        name="a.pdf",
        status=JobStatus.PROCESSING.value,
        success=False,
    )
    out2 = await repo.upsert_data_result_by_index(job_id, r2)
    assert str(out1.id) == str(existing_id)
    assert str(out2.id) == str(existing_id)
    # No $push on second path when index exists
    for call in collection.update_one.await_args_list:
        assert "$push" not in (call.args[1] if len(call.args) > 1 else {})


@pytest.mark.asyncio
async def test_fail_processing_results_respects_completed_noop():
    from core.brevio_api.services.user_service import UserService
    from core.shared.models.user.data_result import DataResult

    completed = DataResult(
        id=ObjectId(),
        index=0,
        status=JobStatus.COMPLETED.value,
        success=True,
        name="ok.pdf",
    )
    entry = SimpleNamespace(
        user_id=ObjectId(),
        name="job",
        status=JobStatus.COMPLETED.value,
        results=[completed],
    )
    repo = MagicMock()
    repo.get_folder_entry_by_id = AsyncMock(return_value=entry)
    repo.transition_job_status = AsyncMock(return_value=None)
    service = UserService(MagicMock(), repo)
    service.update_data_result_status = AsyncMock()

    await service.fail_processing_results(str(ObjectId()), Exception("late fail"))
    service.update_data_result_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_double_delivery_second_claim_is_noop():
    service = MagicMock()
    service.claim_summary_job = AsyncMock(side_effect=[MagicMock(status="PROCESSING"), None])
    service.execute_stored_summary_job = AsyncMock(return_value={"ok": True})
    service.release_capacity_for_job = AsyncMock()

    with patch("core.brevio_api.tasks.BrevioService", return_value=service), patch(
        "core.brevio_api.tasks.JobHeartbeat"
    ) as hb_cls:
        hb = MagicMock()
        hb_cls.return_value = hb
        from core.brevio_api.tasks import _run_claimed_job

        first = await _run_claimed_job("job-1")
        second = await _run_claimed_job("job-1")
    assert first["status"] == "ok"
    assert second["status"] == "ignored"
    assert service.execute_stored_summary_job.await_count == 1
    hb.start.assert_called_once()
    hb.stop.assert_called_once()


@pytest.mark.asyncio
async def test_reconciler_marks_stale_processing_failed():
    from core.brevio_api.services.brevio_service import BrevioService

    old = datetime.now(timezone.utc) - timedelta(
        seconds=stale_processing_grace_seconds() + 10
    )
    job = SimpleNamespace(
        id=ObjectId(),
        status=JobStatus.PROCESSING.value,
        queued_at=old,
        created_at=old,
        claimed_at=old,
        enqueued_at=old,
        enqueue_attempts=1,
    )
    user_service = MagicMock()
    user_service.fail_processing_results = AsyncMock()
    repo = MagicMock()
    repo.list_jobs_by_status = AsyncMock(return_value=[job])
    user_service._folder_entry_repo = repo

    service = BrevioService()
    service._get_user_service = AsyncMock(return_value=user_service)
    service.release_capacity_for_job = AsyncMock()
    service.settle_job_credits = AsyncMock()
    service.dispatch_waiting_jobs = AsyncMock(return_value={"dispatched": 0})
    service._get_credit_service = AsyncMock(side_effect=Exception("skip"))

    with patch(
        "core.brevio_api.services.job_lifecycle.heartbeat_alive", return_value=False
    ), patch("core.brevio_api.services.capacity.CapacityStore") as store_cls:
        store = MagicMock()
        store.reclaim_expired_holders.return_value = 0
        store_cls.return_value = store
        stats = await service.reconcile_stale_jobs()

    assert stats["failed_stale_processing"] == 1
    user_service.fail_processing_results.assert_awaited()
    service.release_capacity_for_job.assert_awaited()


@pytest.mark.asyncio
async def test_reconciler_reenqueues_orphan_queued():
    from core.brevio_api.services.brevio_service import BrevioService

    old = datetime.now(timezone.utc) - timedelta(seconds=400)
    job = SimpleNamespace(
        id=ObjectId(),
        status=JobStatus.QUEUED.value,
        queued_at=old,
        created_at=old,
        claimed_at=None,
        enqueued_at=None,
        enqueue_attempts=0,
    )
    user_service = MagicMock()
    user_service.fail_processing_results = AsyncMock()
    repo = MagicMock()
    repo.list_jobs_by_status = AsyncMock(return_value=[job])
    repo.mark_job_enqueued = AsyncMock()
    user_service._folder_entry_repo = repo

    service = BrevioService()
    service._get_user_service = AsyncMock(return_value=user_service)
    service.schedule_or_dispatch = AsyncMock()
    service.dispatch_waiting_jobs = AsyncMock(return_value={"dispatched": 0})
    service._get_credit_service = AsyncMock(side_effect=Exception("skip credits"))

    with patch("core.brevio_api.services.capacity.CapacityStore") as store_cls:
        store = MagicMock()
        store.reclaim_expired_holders.return_value = 0
        store_cls.return_value = store
        stats = await service.reconcile_stale_jobs()

    assert stats["reenqueued"] == 1
    service.schedule_or_dispatch.assert_awaited()
    repo.mark_job_enqueued.assert_awaited_once_with(str(job.id))


@pytest.mark.asyncio
async def test_reconciler_exhausted_enqueue_attempts_marks_failed():
    from core.brevio_api.services.brevio_service import BrevioService

    old = datetime.now(timezone.utc) - timedelta(seconds=400)
    job = SimpleNamespace(
        id=ObjectId(),
        status=JobStatus.QUEUED.value,
        queued_at=old,
        created_at=old,
        claimed_at=None,
        enqueued_at=None,
        enqueue_attempts=3,
    )
    user_service = MagicMock()
    user_service.fail_processing_results = AsyncMock()
    repo = MagicMock()
    repo.list_jobs_by_status = AsyncMock(return_value=[job])
    repo.mark_job_enqueued = AsyncMock()
    user_service._folder_entry_repo = repo

    service = BrevioService()
    service._get_user_service = AsyncMock(return_value=user_service)
    service.schedule_or_dispatch = AsyncMock()
    service.release_capacity_for_job = AsyncMock()
    service.settle_job_credits = AsyncMock()
    service.dispatch_waiting_jobs = AsyncMock(return_value={"dispatched": 0})
    service._get_credit_service = AsyncMock(side_effect=Exception("skip credits"))

    with patch("core.brevio_api.services.capacity.CapacityStore") as store_cls:
        store = MagicMock()
        store.reclaim_expired_holders.return_value = 0
        store_cls.return_value = store
        stats = await service.reconcile_stale_jobs()

    assert stats["failed_orphan_queued"] == 1
    assert stats["reenqueued"] == 0
    repo.mark_job_enqueued.assert_not_awaited()
    user_service.fail_processing_results.assert_awaited_once()
    service.release_capacity_for_job.assert_awaited_once_with(str(job.id))
    service.settle_job_credits.assert_awaited_once_with(str(job.id), success=False)


@pytest.mark.asyncio
async def test_claim_queued_job_atomic_concurrency_real_mongo():
    import os
    from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository

    mongo_uri = os.environ.get("FASE3_MONGO_URI", "mongodb://127.0.0.1:27017")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Test connection
        await client.admin.command("ping")
    except Exception:
        pytest.skip("MongoDB server is not reachable for real concurrency test")

    db = client.get_database("test_lifecycle_db")
    coll = db.folder_entries
    repo = FolderEntryRepository(coll)

    job_id = ObjectId()
    user_id = ObjectId()
    await coll.insert_one({
        "_id": job_id,
        "user_id": user_id,
        "name": "concurrent_test_job",
        "status": JobStatus.QUEUED.value,
        "queued_at": datetime.now(timezone.utc),
        "results": [{"_id": ObjectId(), "index": 0, "status": JobStatus.QUEUED.value}],
        "file_manifest": [],
    })

    try:
        # Two concurrent workers attempting to claim the exact same queued job
        results = await asyncio.gather(
            repo.claim_queued_job(str(job_id)),
            repo.claim_queued_job(str(job_id)),
        )

        claimed = [r for r in results if r is not None]
        unclaimed = [r for r in results if r is None]

        assert len(claimed) == 1
        assert len(unclaimed) == 1
        assert claimed[0].status == JobStatus.PROCESSING.value

        # Verify state in DB
        doc = await coll.find_one({"_id": job_id})
        assert doc["status"] == JobStatus.PROCESSING.value
        assert doc["claimed_at"] is not None
        assert doc["results"][0]["status"] == JobStatus.PROCESSING.value
    finally:
        await coll.delete_one({"_id": job_id})
        client.close()


@pytest.mark.asyncio
async def test_celery_app_includes_capacity_dispatcher():
    from core.brevio_api.celery import celery_app

    assert "dispatch-capacity-jobs" in celery_app.conf.beat_schedule
    assert celery_app.conf.worker_prefetch_multiplier == 1


@pytest.mark.asyncio
async def test_idempotency_find_returns_same_job():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    user_id = str(ObjectId())
    job_id = ObjectId()
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": job_id,
            "user_id": ObjectId(user_id),
            "name": "x",
            "results": [],
            "idempotency_key": "abc",
            "status": JobStatus.QUEUED.value,
            "file_manifest": [],
        }
    )
    repo = FolderEntryRepository(collection)
    found = await repo.find_by_idempotency_key(user_id, "abc")
    assert found is not None
    assert str(found.id) == str(job_id)


@pytest.mark.asyncio
async def test_idempotency_index_uses_partial_filter_not_sparse_nulls():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    collection = MagicMock()
    collection.update_many = AsyncMock()
    collection.index_information = AsyncMock(
        return_value={
            "entries_user_idempotency": {
                "key": [("user_id", 1), ("idempotency_key", 1)],
                "unique": True,
                "sparse": True,
            }
        }
    )
    collection.drop_index = AsyncMock()
    collection.create_index = AsyncMock()
    repo = FolderEntryRepository(collection)
    await repo.ensure_indexes()

    collection.update_many.assert_awaited()
    unset_call = collection.update_many.await_args_list[0]
    assert unset_call.args[0] == {"idempotency_key": None}
    collection.drop_index.assert_awaited_with("entries_user_idempotency")
    idempotency_calls = [
        call
        for call in collection.create_index.await_args_list
        if call.kwargs.get("name") == "entries_user_idempotency"
        or (
            call.args
            and call.args[0] == [("user_id", 1), ("idempotency_key", 1)]
        )
    ]
    assert idempotency_calls
    kwargs = idempotency_calls[0].kwargs
    assert kwargs["unique"] is True
    assert kwargs["partialFilterExpression"] == {
        "idempotency_key": {"$type": "string"}
    }
    assert "sparse" not in kwargs


@pytest.mark.asyncio
async def test_idempotency_index_skips_rebuild_when_partial_exists():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    collection = MagicMock()
    collection.update_many = AsyncMock()
    collection.index_information = AsyncMock(
        return_value={
            "entries_user_idempotency": {
                "key": [("user_id", 1), ("idempotency_key", 1)],
                "unique": True,
                "partialFilterExpression": {
                    "idempotency_key": {"$type": "string"},
                },
            }
        }
    )
    collection.drop_index = AsyncMock()
    collection.create_index = AsyncMock()
    repo = FolderEntryRepository(collection)
    await repo.ensure_indexes()
    collection.drop_index.assert_not_awaited()
    assert not any(
        call.kwargs.get("name") == "entries_user_idempotency"
        for call in collection.create_index.await_args_list
    )


def test_heartbeat_key_format():
    assert heartbeat_key("abc123") == "brevio:job:abc123:hb"


@pytest.mark.asyncio
async def test_concurrent_idempotency_creates_single_logical_job():
    """100 parallel lookups with unique key resolve to one job id."""
    import asyncio

    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    user_id = str(ObjectId())
    job_id = ObjectId()
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": job_id,
            "user_id": ObjectId(user_id),
            "name": "x",
            "results": [],
            "idempotency_key": "same-key",
            "status": JobStatus.QUEUED.value,
            "file_manifest": [],
        }
    )
    repo = FolderEntryRepository(collection)

    async def lookup():
        found = await repo.find_by_idempotency_key(user_id, "same-key")
        assert found is not None
        return str(found.id)

    ids = await asyncio.gather(*[lookup() for _ in range(100)])
    assert set(ids) == {str(job_id)}
    assert collection.find_one.await_count == 100


@pytest.mark.asyncio
async def test_transition_rejects_completed_to_failed():
    from core.brevio_api.repositories.folder_entry_repository import (
        FolderEntryRepository,
    )

    job_id = str(ObjectId())
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(job_id),
            "user_id": ObjectId(),
            "name": "x",
            "results": [],
            "status": JobStatus.COMPLETED.value,
            "file_manifest": [],
        }
    )
    collection.find_one_and_update = AsyncMock()
    repo = FolderEntryRepository(collection)
    # get_folder_entry_by_id path
    repo.get_folder_entry_by_id = AsyncMock(
        return_value=SimpleNamespace(status=JobStatus.COMPLETED.value, results=[])
    )
    out = await repo.transition_job_status(
        job_id, new_status=JobStatus.FAILED.value
    )
    assert out is None
    collection.find_one_and_update.assert_not_awaited()
