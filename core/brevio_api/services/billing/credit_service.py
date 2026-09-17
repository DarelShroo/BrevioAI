"""Credit reservation, immutable ledger, and job settlement (FASE 3).

Guarantees (standalone Mongo, no multi-doc transactions required):
- Balance never goes negative (atomic find_one_and_update with $gte).
- At most one active reservation per job_id (unique index).
- At most one settlement per job_id (unique index).
- Ledger is append-only; corrections are compensating entries.
- Release/settle are idempotent under concurrency.

Order for jobs (PLATFORM / BYOK / LOCAL):
  create job_id shell → estimate credits → atomic reserve → store files → enqueue
  On failure after reserve: settle(consumed=0) / release.
  BYOK still uses the user provider key; plan credits are reserved/settled the same.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from bson import ObjectId

from core.brevio_api.models.billing.credit_models import (
    BillingMode,
    CreditAccount,
    CreditLedgerEntry,
    CreditReservation,
    JobSettlement,
    LedgerReason,
    ReservationStatus,
    SettlementStatus,
    utcnow,
)
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.repositories.billing.credit_repositories import (
    CreditAccountRepository,
    CreditLedgerRepository,
    CreditReservationRepository,
    JobSettlementRepository,
    billing_collections,
)
from core.shared.enums.model import ModelType
from core.shared.utils.environment import env_float, env_int
from core.shared.utils.model_catalog import model_requires_api_key
from core.shared.utils.model_capabilities import get_model_capabilities

logger = logging.getLogger(__name__)


def reservation_ttl_seconds() -> int:
    # Default 6h > soft time limit 3600s with margin for queue wait.
    return max(600, env_int("CREDIT_RESERVATION_TTL_SECONDS", 6 * 3600))


def reservation_safety_margin() -> float:
    """Multiplier applied to maximum estimate credits (>= 1.0)."""
    return max(1.0, env_float("CREDIT_RESERVATION_SAFETY_MARGIN", 1.0))


def default_platform_reservation_credits() -> int:
    """Fallback when no document estimate is available (media/youtube)."""
    return max(0, env_int("CREDIT_DEFAULT_JOB_RESERVATION", 50))


def overrun_policy() -> str:
    """clamp = settle at most reserved; reject = raise on overrun request."""
    import os

    raw = os.getenv("CREDIT_OVERRUN_POLICY", "clamp")
    return str(raw).strip().lower() or "clamp"


@dataclass(frozen=True)
class ReservationResult:
    reservation: CreditReservation
    created: bool
    billing_mode: str


@dataclass(frozen=True)
class SettlementResult:
    settlement: JobSettlement
    created: bool


class CreditService:
    def __init__(
        self,
        accounts: CreditAccountRepository,
        reservations: CreditReservationRepository,
        ledger: CreditLedgerRepository,
        settlements: JobSettlementRepository,
        *,
        user_repo: Any = None,
    ) -> None:
        self.accounts = accounts
        self.reservations = reservations
        self.ledger = ledger
        self.settlements = settlements
        self._user_repo = user_repo
        self._indexes_ready = False

    @classmethod
    def from_db(cls, db, user_repo: Any = None) -> "CreditService":
        cols = billing_collections(db)
        return cls(
            CreditAccountRepository(cols["accounts"]),
            CreditReservationRepository(cols["reservations"]),
            CreditLedgerRepository(cols["ledger"]),
            JobSettlementRepository(cols["settlements"]),
            user_repo=user_repo,
        )

    async def ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self.accounts.ensure_indexes()
        await self.reservations.ensure_indexes()
        await self.ledger.ensure_indexes()
        await self.settlements.ensure_indexes()
        self._indexes_ready = True

    async def ensure_account(self, user_id: str) -> CreditAccount:
        """Idempotent: create CreditAccount from legacy user_credit if missing."""
        await self.ensure_indexes()
        existing = await self.accounts.get_by_user_id(user_id)
        if existing:
            return existing

        initial = 0
        legacy_raw = None
        if self._user_repo is not None:
            user = await self._user_repo.get_user_by_field("_id", user_id)
            if user is not None:
                legacy_raw = getattr(user, "user_credit", None)
                initial = self._safe_int_balance(legacy_raw, user_id=user_id)

        account = CreditAccount(user_id=ObjectId(user_id), balance=initial)
        created = await self.accounts.create(account)
        if initial > 0 and created.id == account.id:
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=created.id,
                    user_id=ObjectId(user_id),
                    delta=initial,
                    reason=LedgerReason.MIGRATE.value,
                    metadata={"from": "user_credit", "raw": repr(legacy_raw)},
                )
            )
            logger.info(
                "event=credit_account_migrated user_id=%s balance=%s",
                user_id,
                initial,
            )
        return created

    @staticmethod
    def _safe_int_balance(raw: Any, *, user_id: str) -> int:
        if raw is None:
            return 0
        try:
            if isinstance(raw, bool):
                raise ValueError("bool is not a valid credit balance")
            if isinstance(raw, float):
                if math.isnan(raw) or math.isinf(raw):
                    logger.error(
                        "event=credit_migration_corrupt user_id=%s raw=%s",
                        user_id,
                        raw,
                    )
                    raise ValueError(f"corrupt user_credit: {raw}")
                if raw < 0:
                    logger.error(
                        "event=credit_migration_negative user_id=%s raw=%s",
                        user_id,
                        raw,
                    )
                    raise ValueError(f"negative user_credit: {raw}")
                return int(math.floor(raw))
            value = int(raw)
            if value < 0:
                logger.error(
                    "event=credit_migration_negative user_id=%s raw=%s",
                    user_id,
                    raw,
                )
                raise ValueError(f"negative user_credit: {value}")
            return value
        except (TypeError, ValueError) as exc:
            logger.error(
                "event=credit_migration_invalid user_id=%s raw=%r error=%s",
                user_id,
                raw,
                exc,
            )
            raise

    async def get_balance(self, user_id: str) -> int:
        account = await self.ensure_account(user_id)
        return int(account.balance)

    async def apply_period_grant(
        self,
        user_id: str,
        *,
        included: int,
        rollover_max: int,
        grant_key: str,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[CreditAccount, bool]:
        """Grant period credits with rollover cap. Idempotent on grant_key.

        final_balance = min(current_balance + included, rollover_max)
        """
        await self.ensure_indexes()
        account = await self.ensure_account(user_id)
        if account.last_period_grant_key == grant_key:
            return account, False

        result = await self.accounts.atomic_period_grant(
            user_id,
            included=included,
            rollover_max=rollover_max,
            grant_key=grant_key,
        )
        if result is None:
            refreshed = await self.ensure_account(user_id)
            return refreshed, False

        updated, delta = result
        meta: dict[str, Any] = {
            "period_grant_key": grant_key,
            "included": included,
            "rollover_max": rollover_max,
            "balance_after": updated.balance,
        }
        if extra_metadata:
            meta.update(extra_metadata)
        try:
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=updated.id,
                    user_id=ObjectId(user_id),
                    delta=delta,
                    reason=LedgerReason.PERIOD_GRANT.value,
                    metadata=meta,
                )
            )
        except Exception as exc:
            from pymongo.errors import DuplicateKeyError

            if not isinstance(exc, DuplicateKeyError):
                raise
            logger.info(
                "event=period_grant_ledger_duplicate user_id=%s key=%s",
                user_id,
                grant_key,
            )
        logger.info(
            "event=period_credits_granted user_id=%s included=%s rollover_max=%s "
            "delta=%s balance=%s key=%s",
            user_id,
            included,
            rollover_max,
            delta,
            updated.balance,
            grant_key,
        )
        return updated, True

    async def ensure_period_credits(
        self,
        user_id: str,
        plan: Any,
        *,
        user: Any = None,
        grant_key: Optional[str] = None,
    ) -> CreditAccount:
        """Ensure current commercial period credits are applied (rollover-safe).

        Free / non-Stripe users renew on calendar period boundaries.
        Active Stripe subscribers renew via invoice.paid (explicit grant_key).
        """
        from core.brevio_api.services.billing.product_limit_service import (
            current_period_bounds,
        )

        included = int(plan.credits_per_period)
        rollover_max = int(getattr(plan, "rollover_max", included))
        if grant_key is None:
            status = getattr(user, "stripe_subscription_status", None) if user else None
            plan_id = str(getattr(plan, "plan_id", "") or "")
            if (
                status in ("active", "trialing")
                and plan_id not in ("", "free")
            ):
                # Stripe invoice path owns paid renewals.
                return await self.ensure_account(user_id)
            period_start, _ = current_period_bounds()
            grant_key = (
                f"cal:{plan_id}:{period_start.date().isoformat()}"
            )
        account, _ = await self.apply_period_grant(
            user_id,
            included=included,
            rollover_max=rollover_max,
            grant_key=grant_key,
        )
        return account

    async def grant_subscription_credits(
        self, user_id: str, amount: int, stripe_invoice_id: str, *, rollover_max: int
    ) -> bool:
        """Idempotently grant subscription credits with plan rollover cap."""
        await self.ensure_indexes()

        if amount <= 0:
            return False

        grant_key = f"stripe:{stripe_invoice_id}"
        oid = ObjectId(user_id)
        prior = await self.ledger.collection.find_one(
            {
                "user_id": oid,
                "metadata.stripe_invoice_id": stripe_invoice_id,
                "reason": {
                    "$in": [
                        LedgerReason.PERIOD_GRANT.value,
                        LedgerReason.SUBSCRIPTION_GRANT.value,
                    ]
                },
            },
            sort=[("created_at", 1)],
        )
        account = await self.ensure_account(user_id)

        # Legacy path: ledger has invoice grant but account.last_period_grant_key was never set.
        if prior is not None or account.last_period_grant_key == grant_key:
            if account.last_period_grant_key != grant_key and not str(
                account.last_period_grant_key or ""
            ).startswith(f"stripe:{stripe_invoice_id}"):
                await self.accounts.collection.update_one(
                    {"user_id": oid},
                    {"$set": {"last_period_grant_key": grant_key}},
                )
                account = await self.ensure_account(user_id)

            prior_included = None
            if isinstance(prior, dict):
                meta = prior.get("metadata") or {}
                if isinstance(meta, dict) and meta.get("included") is not None:
                    try:
                        prior_included = int(meta["included"])
                    except (TypeError, ValueError):
                        prior_included = None
                if prior_included is None:
                    try:
                        prior_included = int(prior.get("delta") or 0)
                    except (TypeError, ValueError):
                        prior_included = 0

            target = min(int(amount), int(rollover_max))
            # Only align when the prior grant was for a smaller included amount.
            if (
                prior_included is not None
                and prior_included < int(amount)
                and int(account.balance) < target
            ):
                delta = target - int(account.balance)
                align_key = f"stripe:{stripe_invoice_id}:align:{amount}"
                account, aligned = await self.apply_period_grant(
                    user_id,
                    included=delta,
                    rollover_max=rollover_max,
                    grant_key=align_key,
                    extra_metadata={
                        # Do not reuse metadata.stripe_invoice_id — unique ledger index.
                        "align_stripe_invoice_id": stripe_invoice_id,
                        "align_to": amount,
                        "prior_included": prior_included,
                    },
                )
                if aligned:
                    logger.info(
                        "event=subscription_credits_aligned user_id=%s delta=%s "
                        "balance=%s invoice_id=%s",
                        user_id,
                        delta,
                        account.balance,
                        stripe_invoice_id,
                    )
                    return True

            logger.info(
                "event=subscription_grant_duplicate user_id=%s invoice_id=%s",
                user_id,
                stripe_invoice_id,
            )
            return False

        account, created = await self.apply_period_grant(
            user_id,
            included=amount,
            rollover_max=rollover_max,
            grant_key=grant_key,
            extra_metadata={"stripe_invoice_id": stripe_invoice_id},
        )
        if created:
            logger.info(
                "event=subscription_credits_granted user_id=%s amount=%s "
                "rollover_max=%s balance=%s invoice_id=%s",
                user_id,
                amount,
                rollover_max,
                account.balance,
                stripe_invoice_id,
            )
            return True

        logger.info(
            "event=subscription_grant_duplicate user_id=%s invoice_id=%s",
            user_id,
            stripe_invoice_id,
        )
        return False

    def resolve_billing_mode(
        self,
        *,
        model: ModelType,
        has_byok: bool,
    ) -> str:
        if not model_requires_api_key(model):
            return BillingMode.LOCAL.value
        if has_byok:
            return BillingMode.BYOK.value
        return BillingMode.PLATFORM.value

    def compute_reservation_amount(
        self,
        *,
        billing_mode: str,
        maximum_credits: Optional[int] = None,
        expected_credits: Optional[int] = None,
    ) -> tuple[int, int]:
        """Return (reserve_amount, expected_amount).

        All billing modes (PLATFORM / BYOK / LOCAL) reserve from the user's
        CreditAccount. BYOK still uses the user API key for the provider; plan
        credits are the commercial quota and must move with real usage.
        """
        _ = billing_mode  # retained for call-site clarity / future per-mode margins
        maximum = int(maximum_credits) if maximum_credits is not None else None
        expected = int(expected_credits) if expected_credits is not None else None
        if maximum is None:
            maximum = default_platform_reservation_credits()
        if expected is None:
            expected = maximum
        if maximum < 0 or expected < 0:
            raise ValueError("credits must be non-negative")
        margin = reservation_safety_margin()
        reserved = int(math.ceil(maximum * margin))
        expected = min(expected, reserved)
        return reserved, expected

    async def reserve_for_job(
        self,
        *,
        user_id: str,
        job_id: str,
        amount: int,
        expected_amount: int = 0,
        billing_mode: str = BillingMode.PLATFORM.value,
    ) -> ReservationResult:
        """Idempotent reservation bound to job_id."""
        await self.ensure_indexes()
        if amount < 0 or expected_amount < 0:
            raise ValueError("reservation amounts must be >= 0")

        existing = await self.reservations.get_by_job_id(job_id)
        if existing is not None:
            logger.info(
                "event=credit_reservation_reused job_id=%s reservation_id=%s",
                job_id,
                existing.id,
            )
            return ReservationResult(
                reservation=existing, created=False, billing_mode=existing.billing_mode
            )

        account = await self.ensure_account(user_id)

        if amount > 0:
            updated = await self.accounts.atomic_debit_if_available(user_id, amount)
            if updated is None:
                logger.info(
                    "event=credit_reservation_failed user_id=%s job_id=%s amount=%s",
                    user_id,
                    job_id,
                    amount,
                )
                raise ProviderError(
                    kind=ProviderErrorKind.INSUFFICIENT_CREDITS,
                    message="Créditos insuficientes para procesar esta solicitud.",
                )
            account = updated

        reservation = CreditReservation(
            job_id=job_id,
            user_id=ObjectId(user_id),
            account_id=account.id,
            amount=amount,
            expected_amount=min(expected_amount, amount) if amount else 0,
            billing_mode=billing_mode,
            status=ReservationStatus.PENDING.value,
            expires_at=utcnow() + timedelta(seconds=reservation_ttl_seconds()),
        )
        try:
            created = await self.reservations.create(reservation)
        except Exception:
            if amount > 0:
                await self.accounts.atomic_credit(user_id, amount)
            raise

        if str(created.id) != str(reservation.id):
            # Duplicate job_id race: we debited but another reservation won.
            if amount > 0:
                await self.accounts.atomic_credit(user_id, amount)
            return ReservationResult(
                reservation=created, created=False, billing_mode=created.billing_mode
            )

        if amount > 0:
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=account.id,
                    user_id=ObjectId(user_id),
                    job_id=job_id,
                    reservation_id=created.id,
                    delta=-amount,
                    reason=LedgerReason.RESERVE.value,
                    metadata={"billing_mode": billing_mode},
                )
            )
        else:
            # Zero-amount reservation still recorded for audit (BYOK/LOCAL).
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=account.id,
                    user_id=ObjectId(user_id),
                    job_id=job_id,
                    reservation_id=created.id,
                    delta=0,
                    reason=LedgerReason.RESERVE.value,
                    metadata={"billing_mode": billing_mode, "zero": True},
                )
            )

        logger.info(
            "event=credit_reservation_created user_id=%s job_id=%s "
            "reservation_id=%s amount=%s billing_mode=%s",
            user_id,
            job_id,
            created.id,
            amount,
            billing_mode,
        )
        return ReservationResult(
            reservation=created, created=True, billing_mode=billing_mode
        )

    async def release_reservation(
        self,
        reservation: CreditReservation,
        *,
        reason: str = LedgerReason.RELEASE.value,
        metadata: Optional[dict] = None,
    ) -> CreditReservation:
        """Idempotent: PENDING → RELEASED and refund amount once."""
        if reservation.status == ReservationStatus.RELEASED.value:
            return reservation
        if reservation.status == ReservationStatus.COMMITTED.value:
            return reservation

        updated = await self.reservations.transition_status(
            reservation.id,
            from_status=ReservationStatus.PENDING.value,
            to_status=ReservationStatus.RELEASED.value,
            extra_set={"released_at": utcnow()},
        )
        if updated is None:
            current = await self.reservations.get_by_job_id(reservation.job_id)
            return current or reservation

        refund = int(updated.amount)
        if refund > 0:
            await self.accounts.atomic_credit(str(updated.user_id), refund)
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=updated.account_id,
                    user_id=updated.user_id,
                    job_id=updated.job_id,
                    reservation_id=updated.id,
                    delta=refund,
                    reason=reason,
                    metadata=metadata or {},
                )
            )
        else:
            await self.ledger.append(
                CreditLedgerEntry(
                    account_id=updated.account_id,
                    user_id=updated.user_id,
                    job_id=updated.job_id,
                    reservation_id=updated.id,
                    delta=0,
                    reason=reason,
                    metadata={**(metadata or {}), "zero": True},
                )
            )

        logger.info(
            "event=credit_reservation_released job_id=%s reservation_id=%s amount=%s",
            updated.job_id,
            updated.id,
            refund,
        )
        return updated

    async def settle_job(
        self,
        *,
        job_id: str,
        consumed_credits: int,
        metadata: Optional[dict] = None,
    ) -> SettlementResult:
        """Settle once per job. consumed is clamped to reserved unless policy rejects."""
        await self.ensure_indexes()
        if not isinstance(consumed_credits, int) or isinstance(consumed_credits, bool):
            raise ValueError("consumed_credits must be int")
        if consumed_credits < 0:
            raise ValueError("consumed_credits cannot be negative")

        existing = await self.settlements.get_by_job_id(job_id)
        if existing is not None:
            logger.info(
                "event=job_settlement_duplicate job_id=%s settlement_id=%s",
                job_id,
                existing.id,
            )
            reservation = await self.reservations.get_by_job_id(job_id)
            if reservation is not None:
                await self._finalize_reservation_after_settlement(
                    reservation, existing
                )
            return SettlementResult(settlement=existing, created=False)

        reservation = await self.reservations.get_by_job_id(job_id)
        if reservation is None:
            # No commercial reservation (legacy job) — record zero settlement.
            settlement = JobSettlement(
                job_id=job_id,
                user_id=ObjectId(),  # placeholder overwritten below if possible
                reserved_credits=0,
                consumed_credits=0,
                released_credits=0,
                billing_mode=BillingMode.LOCAL.value,
                status=SettlementStatus.SETTLED.value,
                metadata={"note": "no_reservation", **(metadata or {})},
            )
            # Cannot settle without user; treat as no-op settlement record skip.
            logger.info(
                "event=job_settlement_skipped job_id=%s reason=no_reservation",
                job_id,
            )
            return SettlementResult(settlement=settlement, created=False)

        reserved = int(reservation.amount)
        requested = consumed_credits
        overrun = requested > reserved
        consumed = requested
        if overrun:
            logger.warning(
                "event=credit_overrun_detected job_id=%s reserved=%s requested=%s",
                job_id,
                reserved,
                requested,
            )
            policy = overrun_policy()
            if policy == "reject":
                raise ProviderError(
                    kind=ProviderErrorKind.INSUFFICIENT_CREDITS,
                    message="El consumo supera la reserva de créditos del Job.",
                )
            consumed = reserved

        released = reserved - consumed
        if released < 0:
            released = 0

        settlement = JobSettlement(
            job_id=job_id,
            user_id=reservation.user_id,
            reservation_id=reservation.id,
            billing_mode=reservation.billing_mode,
            reserved_credits=reserved,
            consumed_credits=consumed,
            released_credits=released,
            status=SettlementStatus.SETTLED.value,
            overrun_detected=overrun,
            overrun_requested=requested if overrun else 0,
            metadata=metadata or {},
        )
        created = await self.settlements.create(settlement)
        if str(created.id) != str(settlement.id):
            logger.info(
                "event=job_settlement_duplicate job_id=%s settlement_id=%s",
                job_id,
                created.id,
            )
            # Crash recovery: settlement row may exist while reservation is still
            # PENDING (process died after insert, before balance finalize).
            await self._finalize_reservation_after_settlement(
                reservation, created
            )
            return SettlementResult(settlement=created, created=False)

        await self._finalize_reservation_after_settlement(reservation, created)

        logger.info(
            "event=job_settlement_created job_id=%s reserved=%s consumed=%s released=%s",
            job_id,
            reserved,
            consumed,
            released,
        )
        return SettlementResult(settlement=created, created=True)

    async def _finalize_reservation_after_settlement(
        self,
        reservation: CreditReservation,
        settlement: JobSettlement,
    ) -> None:
        """Apply PENDING→COMMITTED/RELEASED + refund remainder exactly once.

        Never uses release_reservation(full amount) from settle: that raced with
        partial consume and could refund reserved while settlement claimed consume.

        Refund claim uses ``refund_applied`` CAS so crash after settlement insert
        (or after status transition) still completes balance/ledger exactly once.
        """
        current = await self.reservations.get_by_job_id(reservation.job_id)
        if current is None:
            return

        reserved = int(settlement.reserved_credits)
        consumed = int(settlement.consumed_credits)
        released = int(settlement.released_credits)
        if released < 0:
            released = 0
        if released > reserved:
            released = reserved

        if current.status == ReservationStatus.PENDING.value:
            to_status = (
                ReservationStatus.RELEASED.value
                if released == reserved
                else ReservationStatus.COMMITTED.value
            )
            extra_set: dict[str, Any] = {}
            if to_status == ReservationStatus.RELEASED.value:
                extra_set["released_at"] = utcnow()
            else:
                extra_set["committed_at"] = utcnow()

            updated = await self.reservations.transition_status(
                current.id,
                from_status=ReservationStatus.PENDING.value,
                to_status=to_status,
                extra_set=extra_set,
            )
            if updated is not None:
                current = updated
            else:
                current = await self.reservations.get_by_job_id(reservation.job_id)
                if current is None:
                    return

        if current.status not in {
            ReservationStatus.COMMITTED.value,
            ReservationStatus.RELEASED.value,
        }:
            return
        if released <= 0:
            # Mark applied so retries do not re-enter oddly.
            await self.reservations.collection.find_one_and_update(
                {"_id": current.id, "refund_applied": {"$ne": True}},
                {"$set": {"refund_applied": True}},
            )
            return

        claimed = await self.reservations.collection.find_one_and_update(
            {"_id": current.id, "refund_applied": {"$ne": True}},
            {"$set": {"refund_applied": True}},
        )
        if claimed is None:
            return

        await self.accounts.atomic_credit(str(current.user_id), released)
        await self.ledger.append(
            CreditLedgerEntry(
                account_id=current.account_id,
                user_id=current.user_id,
                job_id=current.job_id,
                reservation_id=current.id,
                settlement_id=settlement.id,
                delta=released,
                reason=LedgerReason.RELEASE.value,
                metadata={
                    "consumed": consumed,
                    "reserved": reserved,
                    "settlement_id": str(settlement.id),
                },
            )
        )

    async def settle_from_usage(self, job_id: str) -> SettlementResult:
        """Aggregate CostRecords for job_id and settle once (idempotent)."""
        from core.brevio_api.repositories.billing.usage_repositories import (
            CostRecordRepository,
            UsageRecordRepository,
            usage_billing_collections,
        )
        from core.brevio_api.services.billing.usage_service import UsageBillingService

        cols = usage_billing_collections(self.accounts.collection.database)
        usage_svc = UsageBillingService(
            UsageRecordRepository(cols["usage"]),
            CostRecordRepository(cols["costs"]),
            credit_service=self,
            reservations=self.reservations,
        )
        return await usage_svc.settle_job_from_usage(job_id)

    async def settle_job_failure(self, job_id: str) -> SettlementResult:
        """FAILED: charge real usage so far (may be 0) and release remainder."""
        try:
            return await self.settle_from_usage(job_id)
        except Exception:
            logger.exception(
                "event=settle_from_usage_failed job_id=%s falling_back=0", job_id
            )
            return await self.settle_job(job_id=job_id, consumed_credits=0)

    async def settle_job_success_placeholder(self, job_id: str) -> SettlementResult:
        """Deprecated FASE 3 stub — delegates to real usage settlement."""
        try:
            return await self.settle_from_usage(job_id)
        except Exception:
            logger.exception(
                "event=settle_from_usage_failed job_id=%s falling_back=placeholder",
                job_id,
            )
            reservation = await self.reservations.get_by_job_id(job_id)
            if reservation is None:
                return await self.settle_job(job_id=job_id, consumed_credits=0)
            consumed = int(reservation.expected_amount or 0)
            if consumed <= 0 and reservation.amount > 0:
                consumed = int(reservation.amount)
            return await self.settle_job(
                job_id=job_id,
                consumed_credits=consumed,
                metadata={"source": "fase3_placeholder_fallback"},
            )

    async def reconcile_expired_reservations(self, *, job_status_lookup) -> dict:
        """Release or settle PENDING reservations past expires_at.

        job_status_lookup(job_id) -> status str | None

        - PROCESSING/QUEUED: skip (still active)
        - COMPLETED / FAILED / missing: settle from real UsageRecord aggregation
        """
        stats = {
            "released": 0,
            "settled_completed": 0,
            "skipped_running": 0,
        }
        expired = await self.reservations.list_expired_pending()
        for reservation in expired:
            status = None
            try:
                status = await job_status_lookup(reservation.job_id)
            except Exception:
                status = None
            if status in {"PROCESSING", "QUEUED"}:
                stats["skipped_running"] += 1
                continue
            if status == "COMPLETED":
                await self.settle_from_usage(reservation.job_id)
                stats["settled_completed"] += 1
                logger.info(
                    "event=credit_reconciliation job_id=%s reservation_id=%s "
                    "action=settle_from_usage_completed",
                    reservation.job_id,
                    reservation.id,
                )
                continue
            await self.settle_from_usage(reservation.job_id)
            stats["released"] += 1
            logger.info(
                "event=credit_reconciliation job_id=%s reservation_id=%s "
                "action=settle_from_usage_failure",
                reservation.job_id,
                reservation.id,
            )
        return stats
