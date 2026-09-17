#!/usr/bin/env python3
"""Reset Free-plan period usage and credit balance for a user (dev helper).

Restores:
  - User.plan_id / plan_version → free (from commercial_plans.yaml)
  - product_period_usage counters for the current period → 0
  - credit_accounts.balance → free.credits_per_period
  - pending credit_reservations → RELEASED (dev cleanup)

Examples (from repo root):

  # Benchmark user from .env (BREVIO_BENCHMARK_IDENTITY)
  docker compose -f docker-compose.dev.yml exec backend \\
    python scripts/reset_free_plan.py

  docker compose -f docker-compose.dev.yml exec backend \\
    python scripts/reset_free_plan.py --identity Darelsm2

  docker compose -f docker-compose.dev.yml exec backend \\
    python scripts/reset_free_plan.py --all-free --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def resolve_mongo_uri(explicit: str | None) -> str:
    raw = (explicit or os.getenv("MONGODB_URI") or "").strip()
    if not raw:
        fail("MONGODB_URI is not set (pass --mongo-uri or set it in .env)")

    # Host-side convenience: compose URI uses hostname "database".
    # Inside the backend container that hostname is correct — leave it alone.
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    in_docker = Path("/.dockerenv").exists()
    if host in {"database", "mongodb", "mongo"} and not in_docker:
        port = os.getenv("MONGO_PORT", "27017")
        userinfo = ""
        if parsed.username:
            userinfo = parsed.username
            if parsed.password is not None:
                userinfo += f":{parsed.password}"
            userinfo += "@"
        netloc = f"{userinfo}127.0.0.1:{port}"
        raw = urlunparse(parsed._replace(netloc=netloc))
    return raw


def db_name_from_uri(uri: str) -> str:
    path = (urlparse(uri).path or "").lstrip("/")
    if path:
        return path.split("?")[0] or "brevio"
    return os.getenv("MONGO_INITDB_DATABASE", "brevio")


def current_period_bounds() -> tuple[datetime, datetime]:
    from core.brevio_api.services.billing.product_limit_service import (
        current_period_bounds as bounds,
    )

    return bounds()


def free_plan():
    from core.brevio_api.services.billing.plan_registry import get_plan

    return get_plan("free")


def find_users(coll, *, identity: str | None, all_free: bool) -> list[dict[str, Any]]:
    if all_free:
        return list(
            coll.find(
                {"$or": [{"plan_id": "free"}, {"plan_id": {"$exists": False}}, {"plan_id": None}]}
            )
        )
    if not identity:
        fail("Pass --identity, set BREVIO_BENCHMARK_IDENTITY, or use --all-free")
    query = {
        "$or": [
            {"username": identity},
            {"email": identity},
            {"identity": identity},
        ]
    }
    docs = list(coll.find(query))
    if not docs:
        fail(f"No user found for identity={identity!r}")
    return docs


def reset_user(
    db,
    user: dict[str, Any],
    *,
    plan,
    period_start: datetime,
    period_end: datetime,
    credits: int,
    dry_run: bool,
) -> dict[str, Any]:
    uid = user["_id"]
    users = db["users"]
    periods = db["product_period_usage"]
    accounts = db["credit_accounts"]
    reservations = db["credit_reservations"]

    before_plan = user.get("plan_id")
    before_version = user.get("plan_version")
    period_doc = periods.find_one(
        {"user_id": uid, "period_start": period_start, "period_end": period_end}
    )
    account = accounts.find_one({"user_id": uid})
    pending = reservations.count_documents(
        {"user_id": uid, "status": "PENDING"}
    )

    summary = {
        "user_id": str(uid),
        "username": user.get("username"),
        "email": user.get("email"),
        "plan_before": before_plan,
        "plan_version_before": before_version,
        "period_before": {
            "documents_used": (period_doc or {}).get("documents_used", 0),
            "pages_used": (period_doc or {}).get("pages_used", 0),
            "bytes_used": (period_doc or {}).get("bytes_used", 0),
            "credits_used": (period_doc or {}).get("credits_used", 0),
            "credits_hold_active": (period_doc or {}).get("credits_hold_active", 0),
            "credits_budget": (period_doc or {}).get("credits_budget", 0),
            "concurrent_jobs": (period_doc or {}).get("concurrent_jobs", 0),
        },
        "balance_before": (account or {}).get("balance"),
        "pending_reservations": pending,
        "plan_after": plan.plan_id,
        "plan_version_after": plan.version,
        "credits_after": credits,
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    now = datetime.now(timezone.utc)
    users.update_one(
        {"_id": uid},
        {
            "$set": {
                "plan_id": plan.plan_id,
                "plan_version": plan.version,
                "user_credit": credits,
                "updated_at": now,
            }
        },
    )

    period_fields = {
        "plan_id": plan.plan_id,
        "plan_version": plan.version,
        "documents_used": 0,
        "pages_used": 0,
        "bytes_used": 0,
        "credits_used": 0,
        "credits_hold_active": 0,
        "credits_budget": 0,
        "concurrent_jobs": 0,
        "updated_at": now,
    }
    if period_doc:
        periods.update_one(
            {"_id": period_doc["_id"]},
            {"$set": period_fields, "$inc": {"version": 1}},
        )
    else:
        periods.insert_one(
            {
                "_id": ObjectId(),
                "user_id": uid,
                "period_start": period_start,
                "period_end": period_end,
                "version": 1,
                "created_at": now,
                **period_fields,
            }
        )

    if account:
        accounts.update_one(
            {"_id": account["_id"]},
            {
                "$set": {"balance": credits, "updated_at": now},
                "$inc": {"version": 1},
            },
        )
        account_id = account["_id"]
        balance_before = int(account.get("balance") or 0)
    else:
        account_id = ObjectId()
        accounts.insert_one(
            {
                "_id": account_id,
                "user_id": uid,
                "balance": credits,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )
        balance_before = 0

    if pending:
        reservations.update_many(
            {"user_id": uid, "status": "PENDING"},
            {
                "$set": {
                    "status": "RELEASED",
                    "released_at": now,
                    "updated_at": now,
                }
            },
        )

    # Unique sparse index (reservation_id, reason): null+MIGRATE can only exist once.
    # Give each reset its own reservation_id so the script is re-runnable.
    delta = credits - balance_before
    if delta != 0:
        db["credit_ledger"].insert_one(
            {
                "_id": ObjectId(),
                "account_id": account_id,
                "user_id": uid,
                "reservation_id": ObjectId(),
                "delta": delta,
                "reason": "COMPENSATE",
                "created_at": now,
                "metadata": {
                    "source": "scripts/reset_free_plan.py",
                    "plan_id": plan.plan_id,
                    "note": "dev free-plan reset",
                    "balance_before": balance_before,
                    "balance_after": credits,
                },
            }
        )

    return summary


def print_summary(item: dict[str, Any]) -> None:
    flag = "DRY-RUN " if item["dry_run"] else ""
    print(f"{flag}user={item['username'] or item['email']} id={item['user_id']}")
    print(
        f"  plan: {item['plan_before']!r}/{item['plan_version_before']!r}"
        f" → {item['plan_after']!r}/{item['plan_version_after']!r}"
    )
    print(f"  period usage before: {item['period_before']}")
    print(
        f"  credits: balance {item['balance_before']!r} → {item['credits_after']}"
        f" (pending reservations={item['pending_reservations']})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset Free plan period usage + credit balance for a user."
    )
    parser.add_argument(
        "--identity",
        default=os.getenv("BREVIO_BENCHMARK_IDENTITY", "").strip() or None,
        help="Username or email (default: BREVIO_BENCHMARK_IDENTITY)",
    )
    parser.add_argument(
        "--all-free",
        action="store_true",
        help="Reset every user currently on the free plan (or missing plan_id)",
    )
    parser.add_argument(
        "--credits",
        type=int,
        default=None,
        help="Override credit balance (default: free.credits_per_period from YAML)",
    )
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="Mongo URI override (default: MONGODB_URI, remaps host 'database'→127.0.0.1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing",
    )
    args = parser.parse_args()

    uri = resolve_mongo_uri(args.mongo_uri)
    plan = free_plan()
    credits = args.credits if args.credits is not None else int(plan.credits_per_period)
    if credits < 0:
        fail("--credits must be >= 0")

    period_start, period_end = current_period_bounds()
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        fail(f"Cannot reach MongoDB ({uri.split('@')[-1]}): {exc}")

    db = client.get_database(db_name_from_uri(uri))
    users = find_users(db["users"], identity=args.identity, all_free=args.all_free)

    print(
        f"Free plan={plan.plan_id} v{plan.version} credits_per_period={plan.credits_per_period}"
    )
    print(f"Period UTC [{period_start.isoformat()} → {period_end.isoformat()})")
    print(f"Targets: {len(users)} user(s)")

    for user in users:
        summary = reset_user(
            db,
            user,
            plan=plan,
            period_start=period_start,
            period_end=period_end,
            credits=credits,
            dry_run=args.dry_run,
        )
        print_summary(summary)

    client.close()
    if args.dry_run:
        print("Dry run only — no changes written.")
    else:
        print("Done.")


if __name__ == "__main__":
    main()
