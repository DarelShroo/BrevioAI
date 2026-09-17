"""Minimal fair dispatcher: priority + weighted deficit round-robin.

Policy (FASE 6)
---------------
1. HTTP admits a Job commercially (product limits + credits) → status QUEUED.
2. Job is registered in a per-user Redis wait queue (fairness unit = user_id).
3. A single dispatcher (Redis lock) repeatedly:
   a. Adds ``scheduler_weight`` to each eligible user's deficit.
   b. Selects the eligible user with highest
      ``(scheduler_priority, deficit, oldest_queued_age)``.
   c. Pops the oldest job for that user.
   d. Acquires global + user capacity leases (Redis Lua).
   e. Enqueues Celery with ``job_id`` only.
4. Priority is soft: higher priority wins ties / gets more weight via deficit,
   but Free users keep receiving turns (no absolute starvation by design of DRR).
5. Provider quota remains a separate Redis system per provider call.

Redis down → fail-closed (no dispatch, no capacity acquire).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.brevio_api.services.capacity.capacity_store import CapacityStore
from core.brevio_api.services.capacity.config import (
    capacity_lease_ttl_seconds,
    global_max_concurrent_jobs,
    global_max_queued_jobs,
    max_queued_jobs_per_user,
    scheduler_dispatch_batch,
    scheduler_lock_ttl_seconds,
    starvation_age_seconds,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WaitingJob:
    job_id: str
    user_id: str
    plan_id: str
    priority: int
    weight: int
    user_max: int
    queued_at: float  # epoch seconds


@dataclass(frozen=True)
class RegisterResult:
    ok: bool
    reason: str
    queued_global: int
    queued_user: int


@dataclass(frozen=True)
class DispatchDecision:
    job_id: str
    user_id: str
    plan_id: str
    priority: int
    weight: int
    admission_result: str
    admission_reason: str
    global_active: int
    global_limit: int
    user_active: int
    user_limit: int


class FairScheduler:
    USERS_SET = "brevio:scheduler:waiting:users"
    LOCK_KEY = "brevio:scheduler:lock"
    GLOBAL_QUEUED = "brevio:scheduler:queued:count"

    def __init__(self, redis_client: Any | None = None, store: CapacityStore | None = None):
        self._store = store or CapacityStore(redis_client)
        self._client = redis_client
        self._owns_client = redis_client is None and store is None

    def _redis(self) -> Any:
        if self._client is not None:
            return self._client
        # Reuse capacity store client
        return self._store._get()

    def close(self) -> None:
        if self._owns_client:
            self._store.close()

    @staticmethod
    def user_queue_key(user_id: str) -> str:
        return f"brevio:scheduler:waiting:user:{user_id}"

    @staticmethod
    def user_meta_key(user_id: str) -> str:
        return f"brevio:scheduler:meta:user:{user_id}"

    @staticmethod
    def job_meta_key(job_id: str) -> str:
        return f"brevio:scheduler:meta:job:{job_id}"

    def ping(self) -> bool:
        return self._store.ping()

    def register(self, job: WaitingJob) -> RegisterResult:
        """Idempotent register of a commercially admitted QUEUED job.

        GLOBAL_QUEUED + per-user queue cardinality are enforced atomically via Lua
        so concurrent registers cannot race past the configured ceilings.
        """
        if not self.ping():
            return RegisterResult(False, "SCHEDULER_UNAVAILABLE", 0, 0)
        client = self._redis()
        try:
            if client.exists(self.job_meta_key(job.job_id)):
                gq = int(client.get(self.GLOBAL_QUEUED) or 0)
                uq = int(client.zcard(self.user_queue_key(job.user_id)) or 0)
                return RegisterResult(True, "idempotent", gq, uq)

            gmax = int(global_max_queued_jobs())
            umax = int(max_queued_jobs_per_user())
            # Atomic: check global + user cardinality, then ZADD + INCR.
            lua = """
            local gkey = KEYS[1]
            local uqkey = KEYS[2]
            local meta = KEYS[3]
            local users = KEYS[4]
            local umeta = KEYS[5]
            local job_id = ARGV[1]
            local score = tonumber(ARGV[2])
            local gmax = tonumber(ARGV[3])
            local umax = tonumber(ARGV[4])
            local user_id = ARGV[5]
            local plan_id = ARGV[6]
            local priority = ARGV[7]
            local weight = ARGV[8]
            local user_max = ARGV[9]
            local queued_at = ARGV[10]

            if redis.call('EXISTS', meta) == 1 then
              local g = tonumber(redis.call('GET', gkey) or '0')
              local u = redis.call('ZCARD', uqkey)
              return {1, 'idempotent', g, u}
            end
            local g = tonumber(redis.call('GET', gkey) or '0')
            if g >= gmax then
              return {0, 'QUEUE_GLOBAL_LIMIT', g, 0}
            end
            local u = redis.call('ZCARD', uqkey)
            if u >= umax then
              return {0, 'QUEUE_GLOBAL_LIMIT', g, u}
            end
            redis.call('HSET', meta,
              'user_id', user_id,
              'plan_id', plan_id,
              'priority', priority,
              'weight', weight,
              'user_max', user_max,
              'queued_at', queued_at)
            redis.call('ZADD', uqkey, score, job_id)
            redis.call('SADD', users, user_id)
            redis.call('HSET', umeta,
              'priority', priority,
              'weight', weight,
              'user_max', user_max)
            g = redis.call('INCR', gkey)
            u = redis.call('ZCARD', uqkey)
            return {1, 'registered', g, u}
            """
            raw = client.eval(
                lua,
                5,
                self.GLOBAL_QUEUED,
                self.user_queue_key(job.user_id),
                self.job_meta_key(job.job_id),
                self.USERS_SET,
                self.user_meta_key(job.user_id),
                job.job_id,
                str(job.queued_at),
                str(gmax),
                str(umax),
                job.user_id,
                job.plan_id,
                str(job.priority),
                str(max(1, job.weight)),
                str(max(1, job.user_max)),
                str(job.queued_at),
            )
            ok = int(raw[0]) == 1
            reason = str(raw[1])
            gq2 = int(raw[2])
            uq2 = int(raw[3])
            if not ok:
                return RegisterResult(False, reason, gq2, uq2)
            logger.info(
                "event=scheduler_register job_id=%s user_id=%s plan_id=%s "
                "priority=%s weight=%s queued_global=%s queued_user=%s",
                job.job_id,
                job.user_id,
                job.plan_id,
                job.priority,
                job.weight,
                gq2,
                uq2,
            )
            return RegisterResult(True, reason, gq2, uq2)
        except Exception as exc:
            logger.error(
                "event=scheduler_register_failed job_id=%s error=%s",
                job.job_id,
                type(exc).__name__,
            )
            return RegisterResult(False, "SCHEDULER_UNAVAILABLE", 0, 0)

    def unregister(self, job_id: str, user_id: Optional[str] = None) -> None:
        client = self._redis()
        try:
            meta = client.hgetall(self.job_meta_key(job_id)) or {}
            uid = user_id or meta.get("user_id")
            removed = client.zrem(self.user_queue_key(uid), job_id) if uid else 0
            client.delete(self.job_meta_key(job_id))
            if removed:
                gq = int(client.get(self.GLOBAL_QUEUED) or 0)
                if gq <= 1:
                    client.set(self.GLOBAL_QUEUED, 0)
                else:
                    client.decr(self.GLOBAL_QUEUED)
            if uid and client.zcard(self.user_queue_key(uid)) == 0:
                client.srem(self.USERS_SET, uid)
        except Exception:
            logger.exception("event=scheduler_unregister_failed job_id=%s", job_id)

    def _acquire_lock(self) -> Optional[str]:
        token = str(uuid.uuid4())
        try:
            ok = self._redis().set(
                self.LOCK_KEY,
                token,
                nx=True,
                ex=scheduler_lock_ttl_seconds(),
            )
            return token if ok else None
        except Exception:
            return None

    def _release_lock(self, token: str) -> None:
        lua = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
          return redis.call('DEL', KEYS[1])
        end
        return 0
        """
        try:
            self._redis().eval(lua, 1, self.LOCK_KEY, token)
        except Exception:
            pass

    def _eligible_users(self) -> List[str]:
        client = self._redis()
        users = list(client.smembers(self.USERS_SET) or [])
        eligible = []
        for uid in users:
            if int(client.zcard(self.user_queue_key(uid)) or 0) <= 0:
                client.srem(self.USERS_SET, uid)
                continue
            meta = client.hgetall(self.user_meta_key(uid)) or {}
            user_max = max(1, int(meta.get("user_max") or 1))
            if self._store.user_active(uid) >= user_max:
                continue
            eligible.append(uid)
        return eligible

    def _bump_deficits(self, users: List[str]) -> None:
        client = self._redis()
        for uid in users:
            meta = client.hgetall(self.user_meta_key(uid)) or {}
            weight = max(1, int(meta.get("weight") or 1))
            client.hincrby(self.user_meta_key(uid), "deficit", weight)

    def _pick_user(self, users: List[str]) -> Optional[str]:
        client = self._redis()
        best = None
        best_key = None
        now = time.time()
        for uid in users:
            meta = client.hgetall(self.user_meta_key(uid)) or {}
            priority = int(meta.get("priority") or 0)
            deficit = int(meta.get("deficit") or 0)
            head = client.zrange(self.user_queue_key(uid), 0, 0, withscores=True)
            age = 0.0
            if head:
                age = max(0.0, now - float(head[0][1]))
            # Soft priority: priority dominates, then deficit (weight), then age.
            key = (priority, deficit, age)
            if best_key is None or key > best_key:
                best_key = key
                best = uid
        return best

    def dispatch_once(
        self,
        *,
        enqueue_fn: Callable[[str], None],
        on_scheduled: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> List[DispatchDecision]:
        """Run one locked dispatch batch. ``enqueue_fn(job_id)`` sends to Celery."""
        decisions: List[DispatchDecision] = []
        if not self.ping():
            logger.warning("event=scheduler_dispatch_skipped reason=SCHEDULER_UNAVAILABLE")
            return decisions

        # Reclaim expired capacity leases before selecting.
        try:
            reclaimed = self._store.reclaim_expired_holders()
            if reclaimed:
                logger.info("event=capacity_slots_reclaimed count=%s", reclaimed)
        except Exception:
            logger.exception("event=capacity_reclaim_error")

        token = self._acquire_lock()
        if not token:
            return decisions
        try:
            batch = scheduler_dispatch_batch()
            gmax = global_max_concurrent_jobs()
            for _ in range(batch):
                if self._store.global_active() >= gmax:
                    break
                users = self._eligible_users()
                if not users:
                    break
                self._bump_deficits(users)
                uid = self._pick_user(users)
                if not uid:
                    break
                client = self._redis()
                head = client.zrange(self.user_queue_key(uid), 0, 0)
                if not head:
                    continue
                job_id = head[0]
                meta = client.hgetall(self.job_meta_key(job_id)) or {}
                if not meta:
                    self.unregister(job_id, uid)
                    continue
                user_max = max(1, int(meta.get("user_max") or 1))
                priority = int(meta.get("priority") or 0)
                weight = max(1, int(meta.get("weight") or 1))
                plan_id = meta.get("plan_id") or ""
                queued_at = float(meta.get("queued_at") or 0)
                age = time.time() - queued_at if queued_at else 0
                if age >= starvation_age_seconds():
                    logger.warning(
                        "event=scheduler_starvation job_id=%s user_id=%s age_s=%.0f",
                        job_id,
                        uid,
                        age,
                    )

                acq = self._store.acquire(
                    job_id=job_id,
                    user_id=uid,
                    user_max=user_max,
                    global_max=gmax,
                    lease_ttl=capacity_lease_ttl_seconds(),
                )
                if not acq.ok:
                    logger.info(
                        "event=scheduler_reject job_id=%s user_id=%s reason=%s "
                        "global_active=%s global_limit=%s user_active=%s user_limit=%s",
                        job_id,
                        uid,
                        acq.reason,
                        acq.global_active,
                        gmax,
                        acq.user_active,
                        user_max,
                    )
                    decisions.append(
                        DispatchDecision(
                            job_id=job_id,
                            user_id=uid,
                            plan_id=plan_id,
                            priority=priority,
                            weight=weight,
                            admission_result="reject",
                            admission_reason=acq.reason,
                            global_active=acq.global_active,
                            global_limit=gmax,
                            user_active=acq.user_active,
                            user_limit=user_max,
                        )
                    )
                    # Capacity full — stop this batch.
                    if acq.reason == "CAPACITY_GLOBAL_LIMIT":
                        break
                    # User limit: temporarily skip by zeroing deficit advantage
                    client.hset(self.user_meta_key(uid), "deficit", 0)
                    continue

                self._store.remember_lease_user(job_id, uid)
                self.unregister(job_id, uid)
                client.hincrby(self.user_meta_key(uid), "deficit", -1)
                try:
                    enqueue_fn(job_id)
                except Exception:
                    # Roll back capacity + re-register
                    self._store.release(job_id=job_id, user_id=uid)
                    self.register(
                        WaitingJob(
                            job_id=job_id,
                            user_id=uid,
                            plan_id=plan_id,
                            priority=priority,
                            weight=weight,
                            user_max=user_max,
                            queued_at=queued_at or time.time(),
                        )
                    )
                    logger.exception(
                        "event=scheduler_enqueue_failed job_id=%s", job_id
                    )
                    continue

                if on_scheduled:
                    try:
                        on_scheduled(
                            job_id,
                            {
                                "admission_status": "SCHEDULED",
                                "admission_reason": "dispatched",
                                "scheduled_at": time.time(),
                            },
                        )
                    except Exception:
                        logger.exception(
                            "event=scheduler_on_scheduled_failed job_id=%s", job_id
                        )

                logger.info(
                    "event=scheduler_dispatch job_id=%s user_id=%s plan_id=%s "
                    "priority=%s weight=%s admission_result=admit "
                    "admission_reason=dispatched global_active=%s global_limit=%s "
                    "user_active=%s user_limit=%s",
                    job_id,
                    uid,
                    plan_id,
                    priority,
                    weight,
                    acq.global_active,
                    gmax,
                    acq.user_active,
                    user_max,
                )
                decisions.append(
                    DispatchDecision(
                        job_id=job_id,
                        user_id=uid,
                        plan_id=plan_id,
                        priority=priority,
                        weight=weight,
                        admission_result="admit",
                        admission_reason="dispatched",
                        global_active=acq.global_active,
                        global_limit=gmax,
                        user_active=acq.user_active,
                        user_limit=user_max,
                    )
                )
            return decisions
        finally:
            self._release_lock(token)


def waiting_job_from_entry(entry, *, user_id: str | None = None) -> WaitingJob:
    snap = entry.plan_snapshot or {}
    uid = user_id or str(entry.user_id)
    queued = entry.queued_at or entry.created_at
    queued_at = queued.timestamp() if queued is not None else time.time()
    return WaitingJob(
        job_id=str(entry.id),
        user_id=uid,
        plan_id=str(snap.get("plan_id") or "free"),
        priority=int(snap.get("scheduler_priority") or 10),
        weight=max(1, int(snap.get("scheduler_weight") or 1)),
        user_max=max(1, int(snap.get("max_concurrent_jobs") or 1)),
        queued_at=queued_at,
    )
