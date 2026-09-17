import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Any, Dict, List, Tuple

import aiofiles
from bson import ObjectId
from fastapi import HTTPException, status
from pydantic import HttpUrl, ValidationError

from core.brevio.__main__ import Main
from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.core.database import AsyncDB
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService
from core.brevio_api.utils.upload_security import (
    ensure_path_inside,
    sanitize_upload_filename,
)
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from core.shared.utils.source_names import names_for_batch, originals_for_batch

logger = logging.getLogger(__name__)


async def wait_for_file(
    file_path: FilePath, max_attempts: int = 10, delay: float = 0.1
) -> bool:
    loop = asyncio.get_running_loop()
    for attempt in range(max_attempts):
        exists = await loop.run_in_executor(None, os.path.exists, file_path)
        if exists:
            logger.debug(
                f"File confirmed to exist at {file_path} after {attempt + 1} attempts"
            )
            return True
        logger.debug(
            f"File not found at {file_path}, attempt {attempt + 1}/{max_attempts}"
        )
        await asyncio.sleep(delay)
    logger.error(f"File {file_path} not found after {max_attempts} attempts")
    return False


class BrevioService:
    def __init__(self) -> None:
        self._db = AsyncDB()
        self._user_service: UserService | None = None
        self.directory_manager = DirectoryManager()
        self._main = Main()

    async def init_services(self) -> None:
        await self._db.verify_connection()
        db = self._db.database()
        user_repository = UserRepository(db.get_collection("users"))
        entry_repository = FolderEntryRepository(db.get_collection("entries"))
        self._user_service = UserService(user_repository, entry_repository)

    async def _get_user_service(self) -> UserService:
        if self._user_service is None:
            await self.init_services()
        assert self._user_service is not None
        return self._user_service

    async def _get_credit_service(self):
        from core.brevio_api.services.billing.credit_service import CreditService

        await self._db.verify_connection()
        db = self._db.database()
        user_service = await self._get_user_service()
        return CreditService.from_db(db, user_repo=user_service.user_repo)

    async def get_user_credits(self, user_id: str) -> float:
        """Commercial balance from CreditAccount (legacy float API compat)."""
        try:
            credits = await self._get_credit_service()
            user_service = await self._get_user_service()
            user = await user_service.get_user_by_id(user_id)
            from core.brevio_api.services.billing.plan_registry import (
                default_plan,
                get_plan,
            )

            plan_id = getattr(user, "plan_id", None) if user else None
            try:
                plan = get_plan(str(plan_id or default_plan().plan_id))
            except KeyError:
                plan = default_plan()
            await credits.ensure_period_credits(user_id, plan, user=user)
            return float(await credits.get_balance(user_id))
        except Exception:
            logger.exception(
                "event=credit_balance_lookup_failed user_id=%s", user_id
            )
            return 0.0

    async def _user_has_byok(self, user_id: str, model) -> bool:
        from core.brevio_api.repositories.user_credential_repository import (
            UserCredentialRepository,
        )
        from core.brevio_api.services.encryption_service import EncryptionService
        from core.shared.utils.model_capabilities import get_model_capabilities
        from core.shared.utils.model_catalog import model_requires_api_key

        if not model_requires_api_key(model):
            return False
        provider = get_model_capabilities(model).provider.lower()
        db = self._db.database()
        repo = UserCredentialRepository(db, EncryptionService())
        creds = await repo.get_active_credentials_for_user(user_id, provider)
        return bool(creds)

    async def reserve_credits_for_admitted_job(
        self,
        *,
        user_id: str,
        job_id: str,
        prompt_config: PromptConfig,
        source_type: str,
        files_data: List[Tuple[str, bytes]] | None = None,
    ):
        """Calculate + atomically reserve credits for a QUEUED job before enqueue."""
        from core.brevio_api.models.errors.provider_errors import (
            ProviderError,
            ProviderErrorKind,
        )
        from core.brevio_api.services.billing.credit_service import CreditService

        credits: CreditService = await self._get_credit_service()
        try:
            user_service = await self._get_user_service()
            user = await user_service.get_user_by_id(user_id)
            from core.brevio_api.services.billing.plan_registry import (
                default_plan,
                get_plan,
            )

            plan_id = getattr(user, "plan_id", None) if user else None
            try:
                plan = get_plan(str(plan_id or default_plan().plan_id))
            except KeyError:
                plan = default_plan()
            await credits.ensure_period_credits(user_id, plan, user=user)
        except Exception:
            logger.warning(
                "event=period_credit_ensure_failed user_id=%s job_id=%s",
                user_id,
                job_id,
                exc_info=True,
            )
        has_byok = await self._user_has_byok(user_id, prompt_config.model)
        billing_mode = credits.resolve_billing_mode(
            model=prompt_config.model, has_byok=has_byok
        )

        maximum_credits = None
        expected_credits = None
        if source_type == "documents" and files_data:
            try:
                from core.brevio_api.models.brevio.document_processing_request import (
                    DocumentProcessingRequest,
                )
                from core.brevio_api.services.estimation.estimation_service import (
                    EstimationService,
                )

                request = DocumentProcessingRequest(
                    language=prompt_config.language,
                    model=prompt_config.model,
                    category=prompt_config.category,
                    style=prompt_config.style,
                    format=prompt_config.format,
                    summary_level=prompt_config.summary_level,
                )
                outcome = await EstimationService().estimate(request, files_data)
                maximum_credits = int(outcome.maximum_credits)
                expected_credits = int(outcome.expected_credits)
            except Exception:
                logger.warning(
                    "event=credit_estimation_fallback job_id=%s source_type=%s",
                    job_id,
                    source_type,
                    exc_info=True,
                )

        amount, expected = credits.compute_reservation_amount(
            billing_mode=billing_mode,
            maximum_credits=maximum_credits,
            expected_credits=expected_credits,
        )
        try:
            return await credits.reserve_for_job(
                user_id=user_id,
                job_id=job_id,
                amount=amount,
                expected_amount=expected,
                billing_mode=billing_mode,
            )
        except ProviderError:
            user_service = await self._get_user_service()
            try:
                await user_service.fail_processing_results(
                    job_id, Exception("Insufficient credits for reservation")
                )
            except Exception:
                pass
            raise

    async def _get_product_limit_service(self):
        from core.brevio_api.services.billing.product_limit_service import (
            ProductLimitService,
        )

        await self._db.verify_connection()
        return ProductLimitService.from_db(self._db.database())

    async def ensure_user_plan(self, user_id: str):
        """Migrate missing plan_id → default FREE without touching CreditAccount."""
        from core.brevio_api.services.billing.plan_registry import default_plan

        user_service = await self._get_user_service()
        user = await user_service.get_user_by_id(user_id)
        plan_id = getattr(user, "plan_id", None) or ""
        if not plan_id:
            plan = default_plan()
            # Avoid UserRepository.update_user converting *\_id keys to ObjectId.
            await user_service.user_repo.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"plan_id": plan.plan_id, "plan_version": plan.version}},
            )
            user.plan_id = plan.plan_id
            user.plan_version = plan.version
            logger.info(
                "event=user_plan_migrated user_id=%s plan_id=%s version=%s",
                user_id,
                plan.plan_id,
                plan.version,
            )
        return user

    async def settle_job_credits(
        self, job_id: str, *, success: bool, consumed_credits: int | None = None
    ) -> None:
        """Idempotent commercial settlement from real UsageRecord aggregation."""
        try:
            credits = await self._get_credit_service()
            if consumed_credits is not None:
                result = await credits.settle_job(
                    job_id=job_id, consumed_credits=int(consumed_credits)
                )
            else:
                from core.brevio_api.services.billing.usage_service import (
                    UsageBillingService,
                )

                usage = UsageBillingService.from_db(
                    self._db.database(), credit_service=credits
                )
                result = await usage.settle_job_from_usage(job_id)
            try:
                products = await self._get_product_limit_service()
                consumed = int(result.settlement.consumed_credits)
                snap = {}
                user_service = await self._get_user_service()
                try:
                    entry = await user_service._folder_entry_repo.get_folder_entry_by_id(
                        job_id
                    )
                    snap = entry.plan_snapshot or {}
                except Exception:
                    snap = {}
                raw_limit = snap.get("rollover_max")
                if raw_limit is None:
                    raw_limit = snap.get("credits_per_period")
                product_rec = None
                if raw_limit is None:
                    try:
                        product_rec = await products.records.get_by_job(job_id)
                        if product_rec and product_rec.snapshot is not None:
                            raw_limit = getattr(
                                product_rec.snapshot, "rollover_max", None
                            )
                            if raw_limit is None:
                                raw_limit = product_rec.snapshot.credits_per_period
                    except Exception:
                        raw_limit = None
                try:
                    credits_limit = int(raw_limit) if raw_limit is not None else 0
                except (TypeError, ValueError):
                    credits_limit = 0
                if credits_limit <= 0:
                    try:
                        from core.brevio_api.services.billing.plan_registry import (
                            get_plan,
                        )

                        plan_id = snap.get("plan_id")
                        if not plan_id and product_rec is not None:
                            plan_id = product_rec.plan_id
                        plan = get_plan(str(plan_id or "free"))
                        credits_limit = int(plan.rollover_max)
                    except Exception:
                        credits_limit = 0
                await products.record_settled_credits(
                    job_id,
                    consumed,
                    credits_limit=max(0, credits_limit),
                )
                record = await products.records.get_by_job(job_id)
                if record and record.status == "RESERVED":
                    if success:
                        await products.commit_admission(job_id)
                    else:
                        await products.release_admission(job_id)
            except Exception:
                logger.exception(
                    "event=product_usage_post_settle_failed job_id=%s", job_id
                )
        except Exception:
            logger.exception(
                "event=job_settlement_error job_id=%s success=%s", job_id, success
            )

    async def create_summary_job(
        self,
        user_id: str,
        *,
        name: str = "",
        original_name: str | None = None,
        library_folder_id: str | None = None,
        language: str | None = None,
        model: str | None = None,
        category: str | None = None,
        style: str | None = None,
        format: str | None = None,
        summary_level: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        queued_at=None,
        idempotency_key: str | None = None,
        file_manifest: list | None = None,
        job_payload: dict | None = None,
        transcription_provider: str | None = None,
        transcription_model: str | None = None,
        reasoning_effort: str | None = None,
        results: list | None = None,
        plan_snapshot: dict | None = None,
        job_id: str | None = None,
    ) -> str:
        user_service = await self._get_user_service()
        return await user_service.create_folder_entry(
            user_id,
            name=name,
            original_name=original_name,
            library_folder_id=library_folder_id,
            language=language,
            model=model,
            category=category,
            style=style,
            format=format,
            summary_level=summary_level,
            source_type=source_type,
            status=status,
            queued_at=queued_at,
            idempotency_key=idempotency_key,
            file_manifest=file_manifest,
            job_payload=job_payload,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
            reasoning_effort=reasoning_effort,
            results=results,
            plan_snapshot=plan_snapshot,
            job_id=job_id,
        )

    async def find_job_by_idempotency(
        self, user_id: str, idempotency_key: str
    ) -> str | None:
        user_service = await self._get_user_service()
        await user_service._folder_entry_repo.ensure_indexes()
        existing = await user_service._folder_entry_repo.find_by_idempotency_key(
            user_id, idempotency_key
        )
        return str(existing.id) if existing else None

    async def admit_summary_job_with_files(
        self,
        user_id: str,
        files_data: List[Tuple[str, bytes]],
        *,
        prompt_config: PromptConfig,
        source_type: str,
        name: str = "",
        original_name: str | None = None,
        library_folder_id: str | None = None,
        idempotency_key: str | None = None,
        transcription_provider: str | None = None,
        transcription_model: str | None = None,
    ) -> tuple[str, bool]:
        """Store files then create QUEUED job. Returns (job_id, created_new)."""
        from core.shared.enums.job_status import JobPhase, JobStatus
        from core.shared.models.user.data_result import DataResult
        from core.shared.utils.source_names import names_for_source

        user_service = await self._get_user_service()
        await user_service._folder_entry_repo.ensure_indexes()

        if idempotency_key:
            existing_id = await self.find_job_by_idempotency(user_id, idempotency_key)
            if existing_id:
                logger.info(
                    "event=idempotency_key_reused job_id=%s user_id=%s",
                    existing_id,
                    user_id,
                )
                return existing_id, False

        meta = self._prompt_metadata(prompt_config, source_type)
        now = datetime.now(timezone.utc)
        kind = "media" if source_type == "media" else "document"
        placeholder_results: list[DataResult] = []
        for index, (filename, _) in enumerate(files_data):
            display, original = names_for_source(filename, index, kind=kind)
            placeholder_results.append(
                DataResult(
                    name=display,
                    original_name=original,
                    index=index,
                    status=JobStatus.QUEUED.value,
                    phase=JobPhase.QUEUED.value,
                    success=False,
                )
            )

        job_id = await self.create_summary_job(
            user_id,
            name=name,
            original_name=original_name,
            library_folder_id=library_folder_id,
            status=JobStatus.QUEUED.value,
            queued_at=now,
            idempotency_key=idempotency_key,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
            reasoning_effort=prompt_config.reasoning_effort,
            results=placeholder_results,
            **meta,
        )

        # Race: another request may have created+stored first.
        existing_entry = await user_service._folder_entry_repo.get_folder_entry_by_id(
            job_id
        )
        if existing_entry.file_manifest:
            logger.info(
                "event=idempotency_key_reused job_id=%s user_id=%s",
                job_id,
                user_id,
            )
            return job_id, False

        # FASE 5 → FASE 3: product limits then credit reservation.
        from core.brevio_api.models.errors.api_codes import ApiErrorCode
        from core.brevio_api.models.errors.provider_errors import ProviderError
        from core.brevio_api.services.billing.product_limit_service import (
            AdmissionRequest,
            ProductLimitError,
            measure_documents,
        )

        products = await self._get_product_limit_service()
        user = await self.ensure_user_plan(user_id)
        plan = products.resolve_user_plan(user)
        has_byok = await self._user_has_byok(user_id, prompt_config.model)
        docs = measure_documents(files_data, source_type=source_type)
        try:
            admission = await products.admit(
                AdmissionRequest(
                    user_id=user_id,
                    job_id=job_id,
                    source_type=source_type,
                    model=prompt_config.model,
                    has_byok=has_byok,
                    documents=docs,
                ),
                plan=plan,
            )
        except ProductLimitError:
            await user_service.fail_processing_results(
                job_id, Exception("Product limit exceeded")
            )
            raise

        await user_service._folder_entry_repo.update_folder_entry(
            job_id,
            {
                "$set": {
                    "plan_snapshot": admission.snapshot.model_dump(mode="json"),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        try:
            await self.reserve_credits_for_admitted_job(
                user_id=user_id,
                job_id=job_id,
                prompt_config=prompt_config,
                source_type=source_type,
                files_data=files_data,
            )
        except ProviderError as credit_err:
            await products.release_admission(job_id)
            await user_service.fail_processing_results(job_id, credit_err)
            from core.brevio_api.models.errors.api_codes import CodedHTTPException

            raise CodedHTTPException(
                status_code=402,
                code=ApiErrorCode.CREDIT_LIMIT,
                detail=str(credit_err.message),
            ) from credit_err

        user = await user_service.get_user_by_id(user_id)
        if user is None or user.folder is None or user.folder.id is None:
            await products.release_admission(job_id)
            await user_service.fail_processing_results(
                job_id, Exception("User folder missing after job create")
            )
            await self.settle_job_credits(job_id, success=False)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )
        user_folder_id = user.folder.id
        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{job_id}/"
        )
        manifest: List[dict] = []
        try:
            for index, (filename, content) in enumerate(files_data):
                safe_name = sanitize_upload_filename(filename)
                dest = uploads_dir / str(index) / safe_name
                await self.save_media(content, dest)
                if not await wait_for_file(dest):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"File {dest} not created after saving",
                    )
                relative = f"{user_folder_id}/{job_id}/{index}/{safe_name}"
                manifest.append(
                    {
                        "index": index,
                        "filename": safe_name,
                        "relative_path": relative,
                    }
                )
                download_location = (
                    f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{job_id}/{index}"
                )
                # Attach download_location to placeholder by index.
                for result in placeholder_results:
                    if result.index == index:
                        result.download_location = download_location
                        await user_service.create_data_result(user_id, job_id, result)
                        break
            await user_service._folder_entry_repo.update_folder_entry(
                job_id,
                {
                    "$set": {
                        "file_manifest": manifest,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception as store_err:
            logger.error(
                "event=job_store_failed job_id=%s error=%s",
                job_id,
                type(store_err).__name__,
                exc_info=True,
            )
            try:
                await products.release_admission(job_id)
            except Exception:
                pass
            try:
                await user_service.fail_processing_results(job_id, store_err)
            except Exception:
                pass
            await self.settle_job_credits(job_id, success=False)
            try:
                import shutil

                if uploads_dir.exists():
                    shutil.rmtree(uploads_dir, ignore_errors=True)
            except Exception:
                pass
            raise

        await products.commit_admission(job_id)
        logger.info(
            "event=job_queued job_id=%s user_id=%s files=%s plan=%s",
            job_id,
            user_id,
            len(manifest),
            admission.snapshot.plan_id,
        )
        # FASE 6: register for fair dispatch (Celery enqueue happens in dispatcher).
        await self.schedule_or_dispatch(job_id)
        return job_id, True

    async def register_job_for_dispatch(self, job_id: str) -> None:
        """Register a commercially admitted QUEUED job with the fair scheduler."""
        from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
        from core.brevio_api.services.capacity import (
            FairScheduler,
            waiting_job_from_entry,
        )

        user_service = await self._get_user_service()
        entry = await user_service._folder_entry_repo.get_folder_entry_by_id(job_id)
        waiting = waiting_job_from_entry(entry)
        scheduler = FairScheduler()
        try:
            result = scheduler.register(waiting)
        finally:
            scheduler.close()
        if not result.ok:
            code = (
                ApiErrorCode.QUEUE_GLOBAL_LIMIT
                if result.reason == "QUEUE_GLOBAL_LIMIT"
                else ApiErrorCode.SCHEDULER_UNAVAILABLE
            )
            await user_service.fail_processing_results(
                job_id, Exception(f"Scheduler register failed: {result.reason}")
            )
            await self.settle_job_credits(job_id, success=False)
            raise CodedHTTPException(status_code=503, code=code, detail=result.reason)
        await user_service._folder_entry_repo.update_folder_entry(
            job_id,
            {
                "$set": {
                    "admission_status": "WAITING",
                    "admission_reason": result.reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def dispatch_waiting_jobs(self) -> dict:
        """Fair dispatcher tick: capacity acquire → Celery enqueue."""
        from core.brevio_api.services.capacity import FairScheduler
        from core.brevio_api.tasks import process_summary_task

        user_service = await self._get_user_service()
        repo = user_service._folder_entry_repo
        scheduler = FairScheduler()

        def _enqueue(jid: str) -> None:
            process_summary_task.delay(job_id=jid)

        async def _on_scheduled(jid: str, meta: dict) -> None:
            await repo.mark_job_enqueued(jid)
            await repo.update_folder_entry(
                jid,
                {
                    "$set": {
                        "admission_status": meta.get("admission_status", "SCHEDULED"),
                        "admission_reason": meta.get("admission_reason"),
                        "scheduled_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

        try:
            # FairScheduler.on_scheduled is sync callback — bridge via list.
            scheduled_ids = []

            def on_scheduled_sync(jid: str, meta: dict) -> None:
                scheduled_ids.append((jid, meta))

            decisions = scheduler.dispatch_once(
                enqueue_fn=_enqueue, on_scheduled=on_scheduled_sync
            )
            for jid, meta in scheduled_ids:
                await _on_scheduled(jid, meta)
            admitted = sum(1 for d in decisions if d.admission_result == "admit")
            rejected = sum(1 for d in decisions if d.admission_result == "reject")
            return {
                "dispatched": admitted,
                "rejected": rejected,
                "decisions": len(decisions),
            }
        finally:
            scheduler.close()

    async def release_capacity_for_job(self, job_id: str) -> None:
        """Idempotent release of global/user capacity slots."""
        from core.brevio_api.services.capacity import CapacityStore, FairScheduler

        user_id = ""
        try:
            user_service = await self._get_user_service()
            entry = await user_service._folder_entry_repo.get_folder_entry_by_id(job_id)
            user_id = str(entry.user_id)
        except Exception:
            pass
        store = CapacityStore()
        scheduler = FairScheduler(store=store)
        try:
            if not user_id:
                user_id = store.get_lease_user(job_id) or ""
            if not user_id:
                return
            store.release(job_id=job_id, user_id=user_id)
            scheduler.unregister(job_id, user_id)
        finally:
            store.close()

    async def schedule_or_dispatch(self, job_id: str) -> None:
        """Register for fairness then opportunistically dispatch a batch."""
        await self.register_job_for_dispatch(job_id)
        try:
            await self.dispatch_waiting_jobs()
        except Exception:
            logger.exception("event=opportunistic_dispatch_failed job_id=%s", job_id)

    async def mark_job_enqueued(self, job_id: str) -> None:
        user_service = await self._get_user_service()
        await user_service._folder_entry_repo.mark_job_enqueued(job_id)
        logger.info("event=job_enqueued job_id=%s", job_id)

    async def claim_summary_job(self, job_id: str):
        from core.brevio_api.services.capacity import CapacityStore

        store = CapacityStore()
        try:
            if not store.ping():
                logger.warning(
                    "event=claim_aborted_redis_down job_id=%s", job_id
                )
                return None
            if not store.has_lease(job_id):
                # Not capacity-admitted — ignore Celery delivery (fairness).
                logger.info(
                    "event=claim_skipped_no_capacity_lease job_id=%s", job_id
                )
                return None
            store.refresh_lease(job_id)
        finally:
            store.close()

        user_service = await self._get_user_service()
        claimed = await user_service._folder_entry_repo.claim_queued_job(job_id)
        if claimed is None:
            logger.info(
                "event=duplicate_delivery_ignored job_id=%s", job_id
            )
            return None
        await user_service._folder_entry_repo.update_folder_entry(
            job_id,
            {
                "$set": {
                    "admission_status": "RUNNING",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        logger.info("event=job_claimed job_id=%s", job_id)
        return claimed

    async def execute_stored_summary_job(self, job_id: str) -> Dict[str, Any]:
        """Run pipeline for a claimed job using on-disk files (no Celery bytes)."""
        from core.brevio.enums.language import LanguageType
        from core.brevio.enums.output_format_type import OutputFormatType
        from core.brevio.enums.summary_level import SummaryLevel
        from core.shared.enums.job_status import JobStatus
        from core.shared.enums.model import ModelType

        user_service = await self._get_user_service()
        entry = await user_service._folder_entry_repo.get_folder_entry_by_id(job_id)
        user_id = str(entry.user_id)
        if entry.status != JobStatus.PROCESSING.value:
            logger.info(
                "event=job_execute_skipped job_id=%s status=%s",
                job_id,
                entry.status,
            )
            return {"status": "skipped", "job_id": job_id}

        if not entry.model or not entry.language or not entry.format:
            raise ValueError(f"Job {job_id} missing prompt metadata")

        prompt_config = PromptConfig(
            model=ModelType(entry.model),
            category=entry.category or "",
            style=entry.style or "",
            format=OutputFormatType(entry.format),
            language=LanguageType[entry.language]
            if entry.language in LanguageType.__members__
            else next(
                (m for m in LanguageType if m.value == entry.language),
                LanguageType.ENGLISH,
            ),
            summary_level=SummaryLevel(entry.summary_level or "moderate"),
            reasoning_effort=entry.reasoning_effort,
        )

        user = await user_service.get_user_by_id(user_id)
        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )
        user_folder_id = str(user.folder.id)
        source_type = (entry.source_type or "documents").lower()

        if source_type == "youtube" and entry.job_payload:
            payload = dict(entry.job_payload)
            if "prompt_config" in payload and isinstance(payload["prompt_config"], dict):
                payload["prompt_config"]["id"] = ObjectId()
            brevio_generate = BrevioGenerate(**payload)
            try:
                result = await self.generate(
                    brevio_generate, user_id, folder_entry_id=job_id
                )
                await user_service._folder_entry_repo.transition_job_status(
                    job_id,
                    new_status=JobStatus.COMPLETED.value,
                    from_statuses=[JobStatus.PROCESSING.value],
                )
                await self.settle_job_credits(job_id, success=True)
                logger.info("event=job_completed job_id=%s", job_id)
                return result
            except Exception as exc:
                await user_service.fail_processing_results(job_id, exc)
                await self.settle_job_credits(job_id, success=False)
                raise

        try:
            saved_files: List[MediaEntry] = []
            for item in entry.file_manifest or []:
                rel = item.get("relative_path")
                if not rel:
                    continue
                path = FilePath(Constants.DESTINATION_FOLDER) / rel
                if not path.exists():
                    raise FileNotFoundError(f"Stored job file missing: {path}")
                saved_files.append(MediaEntry(path=path))

            if not saved_files:
                raise ValueError(f"Job {job_id} has no stored files")

            data = BrevioGenerate(
                data=saved_files,
                prompt_config=prompt_config,
                transcription_provider=entry.transcription_provider,
                transcription_model=entry.transcription_model,
            )
            if source_type == "media":
                result = await self._main.generate(
                    data,
                    user_service.create_data_result,
                    job_id,
                    user_folder_id,
                    user_id,
                )
            else:
                result = await self._main.generate_summary_documents(
                    data,
                    job_id,
                    user_folder_id,
                    user_id,
                    user_service.create_data_result,
                )
            await user_service._folder_entry_repo.transition_job_status(
                job_id,
                new_status=JobStatus.COMPLETED.value,
                from_statuses=[JobStatus.PROCESSING.value],
            )
            await self.release_capacity_for_job(job_id)
            await self.settle_job_credits(job_id, success=True)
            logger.info("event=job_completed job_id=%s", job_id)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as exc:
            await user_service.fail_processing_results(job_id, exc)
            await self.release_capacity_for_job(job_id)
            await self.settle_job_credits(job_id, success=False)
            raise

    async def reconcile_stale_jobs(self) -> Dict[str, int]:
        """Recover abandoned QUEUED/PROCESSING jobs. Mongo is authority."""
        from core.brevio_api.services.job_lifecycle import (
            heartbeat_alive,
            orphan_queued_seconds,
            seconds_since,
            stale_processing_grace_seconds,
            stale_queued_enqueued_seconds,
        )
        from core.shared.enums.job_status import JobStatus

        user_service = await self._get_user_service()
        repo = user_service._folder_entry_repo
        stats = {"failed_stale_processing": 0, "reenqueued": 0, "failed_orphan_queued": 0}

        open_jobs = await repo.list_jobs_by_status(
            [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]
        )
        for job in open_jobs:
            job_id = str(job.id)
            age_queued = seconds_since(job.queued_at or job.created_at)
            age_claimed = seconds_since(job.claimed_at)

            if job.status == JobStatus.PROCESSING.value:
                grace = stale_processing_grace_seconds()
                if age_claimed is not None and age_claimed < grace:
                    continue
                if heartbeat_alive(job_id):
                    continue
                logger.warning(
                    "event=reconciler_stale_job job_id=%s status=PROCESSING",
                    job_id,
                )
                await user_service.fail_processing_results(
                    job_id,
                    Exception("Job abandoned: worker heartbeat lost"),
                )
                await self.release_capacity_for_job(job_id)
                await self.settle_job_credits(job_id, success=False)
                # FASE 3: release reservation after FAILED.
                stats["failed_stale_processing"] += 1
                continue

            if job.status == JobStatus.QUEUED.value:
                if job.enqueued_at is None:
                    if age_queued is not None and age_queued >= orphan_queued_seconds():
                        # Re-register / dispatch via fair scheduler (not blind Celery).
                        if (job.enqueue_attempts or 0) < 3:
                            try:
                                await self.schedule_or_dispatch(job_id)
                                stats["reenqueued"] += 1
                                logger.info(
                                    "event=reconciler_reenqueued job_id=%s", job_id
                                )
                            except Exception as enq_err:
                                logger.error(
                                    "event=reconciler_enqueue_failed job_id=%s error=%s",
                                    job_id,
                                    type(enq_err).__name__,
                                )
                        else:
                            await user_service.fail_processing_results(
                                job_id,
                                Exception("Job orphaned: enqueue exhausted"),
                            )
                            await self.release_capacity_for_job(job_id)
                            await self.settle_job_credits(job_id, success=False)
                            stats["failed_orphan_queued"] += 1
                    continue
                age_enq = seconds_since(job.enqueued_at)
                if (
                    age_enq is not None
                    and age_enq >= stale_queued_enqueued_seconds()
                ):
                    logger.warning(
                        "event=reconciler_stale_queued job_id=%s", job_id
                    )
                    await user_service.fail_processing_results(
                        job_id,
                        Exception("Job stuck in QUEUED after enqueue"),
                    )
                    await self.release_capacity_for_job(job_id)
                    await self.settle_job_credits(job_id, success=False)
                    stats["failed_orphan_queued"] += 1

        # Reclaim expired capacity leases (worker crash without Mongo transition).
        try:
            from core.brevio_api.services.capacity import CapacityStore

            store = CapacityStore()
            try:
                stats["capacity_slots_reclaimed"] = store.reclaim_expired_holders()
            finally:
                store.close()
        except Exception:
            logger.exception("event=capacity_reclaim_error")

        # Opportunistic fair dispatch for WAITING jobs.
        try:
            dispatch_stats = await self.dispatch_waiting_jobs()
            stats["dispatched"] = dispatch_stats.get("dispatched", 0)
        except Exception:
            logger.exception("event=reconciler_dispatch_error")

        # Expired PENDING reservations for terminal / unknown jobs.
        try:
            credits = await self._get_credit_service()

            async def _job_status(jid: str):
                try:
                    entry = await repo.get_folder_entry_by_id(jid)
                    return entry.status
                except Exception:
                    return None

            credit_stats = await credits.reconcile_expired_reservations(
                job_status_lookup=_job_status
            )
            stats["credit_reservations_released"] = credit_stats.get("released", 0)
            stats["credit_reservations_skipped"] = credit_stats.get(
                "skipped_running", 0
            )
        except Exception:
            logger.exception("event=credit_reconciliation_error")

        return stats

    async def _resolve_library_folder(
        self,
        user_id: str,
        folder_id: str | None,
        folder_name: str | None,
    ):
        from core.brevio_api.repositories.library_folder_repository import (
            LibraryFolderRepository,
        )
        from core.brevio_api.services.library_folder_service import LibraryFolderService

        db = self._db.database()
        service = LibraryFolderService(
            LibraryFolderRepository(db.get_collection("library_folders")),
            FolderEntryRepository(db.get_collection("entries")),
        )
        return await service.resolve_destination(user_id, folder_id, folder_name)

    @staticmethod
    def _prompt_metadata(
        prompt_config: PromptConfig, source_type: str
    ) -> dict[str, str]:
        return {
            "language": prompt_config.language.name,
            "model": prompt_config.model.value,
            "category": prompt_config.category,
            "style": prompt_config.style,
            "format": prompt_config.format.value,
            "summary_level": prompt_config.summary_level.value,
            "source_type": source_type,
        }

    async def count_media_in_yt_playlist(self, url: HttpUrl) -> int:
        return await self._main.count_media_in_yt_playlist(url)

    async def get_total_duration(self, url: HttpUrl) -> float:
        duration_data = await self._main.get_media_duration(url)

        if not isinstance(duration_data, dict) or "durations" not in duration_data:
            logger.error("Invalid duration data format")
            raise ValueError("Invalid duration data format")

        return sum(int(item["duration"]) for item in duration_data["durations"])

    async def get_media_duration(self, url: HttpUrl) -> Dict[str, Any]:
        try:
            return await self._main.get_media_duration(url)
        except Exception as e:
            logger.error(f"Error retrieving media duration for {url}: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Error retrieving media duration"
            ) from e

    def get_languages(self) -> Any:
        return self._main.get_languages()

    async def get_all_category_style_combinations(self) -> Any:
        return await self._main.get_all_category_style_combinations()

    def get_all_summary_levels(self) -> Any:
        return self._main.get_all_summary_levels()

    def get_all_formats(self) -> Any:
        return self._main.get_all_formats()

    def get_models(self) -> List[str]:
        return self._main.get_models()

    async def generate(
        self,
        data: BrevioGenerate,
        _current_user_id: str,
        folder_entry_id: str | None = None,
    ) -> Dict[str, Any]:
        try:
            await self.init_services()

            assert self._user_service is not None

            if folder_entry_id:
                existing = await self._user_service._folder_entry_repo.get_folder_entry_by_id(
                    folder_entry_id
                )
                if str(existing.user_id) != str(_current_user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User does not own the supplied summary job",
                    )
                current_folder_entry_id = folder_entry_id
            else:
                folder_oid = await self._resolve_library_folder(
                    _current_user_id, data.library_folder_id, data.folder_name
                )
                sources = [
                    str(media.path or media.url or "") for media in (data.data or [])
                ]
                display_name, original_name = names_for_batch(
                    sources,
                    kind="video",
                    entry_name=getattr(data, "name", None),
                )
                if not original_name:
                    original_name = originals_for_batch(sources, kind="video")
                folder_entry = await self._user_service.create_folder_entry(
                    _current_user_id,
                    name=display_name,
                    original_name=original_name or None,
                    library_folder_id=folder_oid,
                    **self._prompt_metadata(data.prompt_config, "youtube"),
                )

                if folder_entry is None:
                    logger.error("Failed to create folder entry")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create folder entry",
                    )
                current_folder_entry_id = folder_entry

            user = await self._user_service.get_user_by_id(_current_user_id)

            if user is None or user.folder is None or user.folder.id is None:
                logger.error("User or user folder not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User or user folder not found",
                )
            user_folder_id = user.folder.id

            total_cost_media_minutes = 0.0

            for media in data.data:
                if media.url:
                    duration = await self.get_total_duration(media.url)
                    total_cost_media_minutes += (
                        duration / 60
                    )  # Convertir segundos a minutos
                else:
                    logger.error("Media URL is required")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Media URL is required",
                    )

            logger.info(f"Generating content for user {_current_user_id}")
            try:
                result = await self._main.generate(
                    data,
                    self._user_service.create_data_result,
                    current_folder_entry_id,
                    str(user_folder_id),
                    _current_user_id,
                )
                return result
            except Exception:
                try:
                    await self._user_service.fail_processing_results(
                        current_folder_entry_id,
                        Exception("Summary job terminated without COMPLETED"),
                    )
                except Exception as persist_error:
                    logger.error(
                        "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                        current_folder_entry_id,
                        persist_error,
                        exc_info=True,
                    )
                raise

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error during generation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during generation: {str(e)}",
            )

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: str,
        _prompt_config: PromptConfig,
        folder_entry_id: str | None = None,
        transcription_provider: str | None = None,
        transcription_model: str | None = None,
    ) -> Dict[str, Any]:
        user_service = await self._get_user_service()

        meta = self._prompt_metadata(_prompt_config, "media")
        folder_entry = folder_entry_id
        if folder_entry is None:
            folder_entry = await user_service.create_folder_entry(
                _current_user_id, **meta
            )
        else:
            existing_entry = (
                await user_service._folder_entry_repo.get_folder_entry_by_id(
                    folder_entry
                )
            )
            if str(existing_entry.user_id) != str(_current_user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not own the supplied summary job",
                )
            await user_service.update_folder_entry_metadata(folder_entry, **meta)

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id = folder_entry

        user = await user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            logger.error("User or user folder not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )

        saved_files: List[MediaEntry] = []
        total_media_minutes = 0.0

        tasks = [
            self.save_media(
                content,
                uploads_dir / str(index) / sanitize_upload_filename(filename),
            )
            for index, (filename, content) in enumerate(files_data)
        ]
        await asyncio.gather(*tasks)

        for index, (filename, _) in enumerate(files_data):
            file_path = uploads_dir / str(index) / sanitize_upload_filename(filename)
            if not await wait_for_file(file_path):
                logger.error(f"File {file_path} not created after saving")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File {file_path} not created after saving",
                )
            try:
                minutes = await self.count_minutes_media(file_path)
                total_media_minutes += minutes
                saved_files.append(MediaEntry(path=file_path))
            except ValidationError as e:
                logger.error(
                    f"Validation error for MediaEntry at {file_path}: {str(e)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid media entry for {file_path}: {str(e)}",
                )

        _data = BrevioGenerate(
            data=saved_files,
            prompt_config=_prompt_config,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
        )

        logger.info(f"Generating summary for media upload for user {_current_user_id}")
        try:
            result = await self._main.generate(
                _data,
                user_service.create_data_result,
                current_folder_entry_id,
                str(user_folder_id),
                _current_user_id,
            )
        except Exception:
            try:
                await user_service.fail_processing_results(
                    current_folder_entry_id,
                    Exception("Summary job terminated without COMPLETED"),
                )
            except Exception as persist_error:
                logger.error(
                    "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                    current_folder_entry_id,
                    persist_error,
                    exc_info=True,
                )
            raise

        if not isinstance(result, dict):
            logger.error("Unexpected response format from brevio service")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response format from brevio service",
            )

        return result

    async def generate_summary_documents(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: str,
        _prompt_config: PromptConfig,
        folder_entry_id: str | None = None,
    ) -> Dict[str, str]:
        user_service = await self._get_user_service()

        folder_entry = folder_entry_id
        meta = self._prompt_metadata(_prompt_config, "documents")
        if folder_entry is None:
            folder_entry = await user_service.create_folder_entry(
                _current_user_id, **meta
            )
        else:
            existing_entry = (
                await user_service._folder_entry_repo.get_folder_entry_by_id(
                    folder_entry
                )
            )
            if str(existing_entry.user_id) != str(_current_user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not own the supplied summary job",
                )
            await user_service.update_folder_entry_metadata(folder_entry, **meta)

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )

        current_folder_entry_id = folder_entry

        user = await user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            logger.error("User or user folder not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )

        tasks = [
            self.save_media(
                content,
                uploads_dir / str(index) / sanitize_upload_filename(filename),
            )
            for index, (filename, content) in enumerate(files_data)
        ]

        await asyncio.gather(*tasks)

        saved_files: List[MediaEntry] = []
        for index, (filename, _) in enumerate(files_data):
            file_path = uploads_dir / str(index) / sanitize_upload_filename(filename)
            if not await wait_for_file(file_path):
                logger.error(f"File {file_path} not created after saving")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File {file_path} not created after saving",
                )
            try:
                saved_files.append(MediaEntry(path=file_path))
            except ValidationError as e:
                logger.error(
                    f"Validation error for MediaEntry at {file_path}: {str(e)}"
                )
                raise ValueError(
                    f"Invalid media entry for {file_path}: {str(e)}",
                )

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)

        logger.info(f"Generating summary documents for user {_current_user_id}")
        try:
            result = await self._main.generate_summary_documents(
                _data,
                current_folder_entry_id,
                str(user_folder_id),
                _current_user_id,
                user_service.create_data_result,
            )
            return result
        except Exception:
            try:
                await user_service.fail_processing_results(
                    current_folder_entry_id,
                    Exception("Summary job terminated without COMPLETED"),
                )
            except Exception as persist_error:
                logger.error(
                    "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                    current_folder_entry_id,
                    persist_error,
                    exc_info=True,
                )
            raise

    def _resolve_download_dir(self, download_loc: str) -> FilePath:
        """Confine downloads to trusted roots (data/ in production)."""
        import tempfile

        from core.shared.utils.environment import is_production_environment

        candidate = FilePath(download_loc)
        roots = [FilePath(Constants.DESTINATION_FOLDER).resolve()]
        if not is_production_environment():
            roots.append(FilePath(tempfile.gettempdir()).resolve())
            # Pytest basetemp / project-local artifact dirs used by this repo.
            roots.extend(
                [
                    FilePath("core/brevio_api/tests").resolve(),
                    FilePath("core/brevio/tests").resolve(),
                    FilePath(".tmp").resolve(),
                ]
            )

        last_error: HTTPException | None = None
        for root in roots:
            try:
                return ensure_path_inside(root, candidate)
            except HTTPException as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path"
        )

    async def save_media(self, content: bytes, file_path: FilePath) -> None:
        try:
            safe_name = sanitize_upload_filename(file_path.name)
            intended = file_path.parent / safe_name
            destination = ensure_path_inside(
                FilePath(Constants.DESTINATION_FOLDER).resolve(),
                intended,
            )
            logger.debug(f"Saving media to {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)

            os.chmod(destination.parent, 0o755)

            await self._write_file(destination, content)
            logger.debug(f"Successfully saved media to {destination}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error saving media file {file_path}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error saving media file",
            )

    async def count_minutes_media(self, file_path: FilePath) -> float:
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(file_path),
            ]

            # Ejecutar el subprocess de forma asíncrona
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(
                    f"ffprobe falló en {file_path}: {stderr.decode().strip()}"
                )

            probe_data = json.loads(stdout.decode())
            duration_seconds = float(probe_data["format"]["duration"])
            duration_minutes = duration_seconds / 60
            return round(duration_minutes, 2)

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Error al obtener la duración de {file_path}: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error inesperado al calcular duración de {file_path}: {str(e)}"
            ) from e

    async def _write_file(self, file_path: FilePath, content: bytes) -> None:
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
                await f.flush()

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, os.fsync, f.fileno())
        except Exception as e:
            raise RuntimeError(f"Error al escribir en {file_path}: {str(e)}") from e

    async def download_summary_file(
        self,
        user_id: str,
        folder_entry_id: str,
        requested_format: str,
        result_index: int | None = None,
    ) -> Tuple[str, str, str]:
        """
        Returns (file_path, filename, media_type) for downloading a summary in the requested format.
        Generates .docx or .pdf on the fly if not already generated.
        """
        user_service = await self._get_user_service()

        if not ObjectId.is_valid(folder_entry_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid folder entry ID format",
            )

        folder_entry = await user_service._folder_entry_repo.get_folder_entry_by_id(
            folder_entry_id
        )
        if not folder_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FolderEntry with ID {folder_entry_id} not found",
            )

        if str(folder_entry.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this folder entry",
            )

        if not folder_entry.results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No results found in folder entry",
            )

        if result_index is None:
            if len(folder_entry.results) == 1:
                result_index = 0
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "result_index is required when the entry has multiple results"
                    ),
                )

        if result_index < 0 or result_index >= len(folder_entry.results):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result index {result_index} not found in folder entry",
            )

        result_item = folder_entry.results[result_index]
        if not result_item.is_completed():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Summary is not completed and cannot be downloaded "
                    f"(status={result_item.status or 'unknown'}, "
                    f"phase={result_item.phase or 'unknown'})"
                ),
            )

        download_loc = result_item.download_location
        if not download_loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download location not found for result item",
            )

        try:
            download_path = self._resolve_download_dir(download_loc)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download location not found for result item",
            )
        download_loc = str(download_path)
        md_path = os.path.join(download_loc, "summary.md")

        if not os.path.exists(md_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base summary file not found",
            )

        fmt = requested_format.lower().strip(".")

        if fmt in ["docx", "doc"]:
            docx_path = os.path.join(download_loc, "summary.docx")
            if not os.path.exists(docx_path):
                generated = await self.directory_manager.create_docx_version(md_path)
                if not generated or not os.path.exists(generated):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate DOCX file",
                    )
            return (
                docx_path,
                f"summary_{folder_entry_id}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        elif fmt == "pdf":
            generated = await self.directory_manager.create_pdf_version(
                md_path,
                document_id=folder_entry_id,
            )
            if not generated or not os.path.exists(generated):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate PDF file",
                )
            return (
                generated,
                f"summary_{folder_entry_id}.pdf",
                "application/pdf",
            )

        elif fmt in ["md", "markdown"]:
            return (
                md_path,
                f"summary_{folder_entry_id}.md",
                "text/markdown",
            )

        elif fmt in ["txt", "text"]:
            txt_path = os.path.join(download_loc, "summary.txt")
            if not os.path.exists(txt_path):
                async with aiofiles.open(md_path, "r", encoding="utf-8") as f_in:
                    content = await f_in.read()
                async with aiofiles.open(txt_path, "w", encoding="utf-8") as f_out:
                    await f_out.write(content)
            return (
                txt_path,
                f"summary_{folder_entry_id}.txt",
                "text/plain",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported download format: {requested_format}",
            )
