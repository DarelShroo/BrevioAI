import logging
import os
import stripe
import time
from typing import Optional, Dict, Any, List

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.billing.stripe_event_repository import StripeEventRepository
from core.brevio_api.models.billing.stripe_event_model import StripeWebhookEvent
from core.brevio_api.services.billing.credit_service import CreditService

logger = logging.getLogger(__name__)

_PRICE_CACHE: Dict[str, Dict[str, float]] = {}
_PRICE_CACHE_TIME = 0


async def get_cached_stripe_prices() -> Dict[str, Dict[str, float]]:
    global _PRICE_CACHE, _PRICE_CACHE_TIME
    config = StripeConfig()
    if not config.secret_key:
        return {}
    if time.time() - _PRICE_CACHE_TIME < 300:
        return _PRICE_CACHE

    prices: Dict[str, Dict[str, float]] = {}
    for plan_id in ["pro", "business"]:
        prices[plan_id] = {}
        for cycle, key in [("month", f"{plan_id}_month"), ("year", f"{plan_id}_year")]:
            price_id = config.prices.get(key)
            if price_id and price_id.startswith("price_"):
                try:
                    p = await stripe.Price.retrieve_async(price_id)
                    prices[plan_id][cycle] = p.unit_amount / 100.0
                except Exception as e:
                    logger.error(f"Failed to fetch price {price_id}: {e}")

    _PRICE_CACHE = prices
    _PRICE_CACHE_TIME = time.time()
    return _PRICE_CACHE


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    # stripe-python v10+: StripeObject is not a mapping; use to_dict().
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return converted
        except Exception:
            pass
    to_dict_recursive = getattr(value, "to_dict_recursive", None)
    if callable(to_dict_recursive):
        try:
            converted = to_dict_recursive()
            if isinstance(converted, dict):
                return converted
        except Exception:
            pass
    try:
        return dict(value)
    except Exception:
        return {}


def extract_price_id(obj: Any) -> Optional[str]:
    """Resolve a Stripe Price ID from classic or 2024+ invoice/subscription shapes."""
    data = _as_dict(obj)
    price = data.get("price")
    if isinstance(price, str) and price.startswith("price_"):
        return price
    if isinstance(price, dict):
        pid = price.get("id")
        if isinstance(pid, str) and pid.startswith("price_"):
            return pid
    pricing = _as_dict(data.get("pricing"))
    details = _as_dict(pricing.get("price_details"))
    nested = details.get("price")
    if isinstance(nested, str) and nested.startswith("price_"):
        return nested
    plan = _as_dict(data.get("plan"))
    plan_id = plan.get("id")
    if isinstance(plan_id, str) and plan_id.startswith("price_"):
        return plan_id
    return None


def extract_subscription_id(obj: Any) -> Optional[str]:
    data = _as_dict(obj)
    sub = data.get("subscription")
    if isinstance(sub, str) and sub.startswith("sub_"):
        return sub
    if isinstance(sub, dict):
        sid = sub.get("id")
        if isinstance(sid, str) and sid.startswith("sub_"):
            return sid
    parent = _as_dict(data.get("parent"))
    sub_details = _as_dict(parent.get("subscription_details"))
    nested = sub_details.get("subscription")
    if isinstance(nested, str) and nested.startswith("sub_"):
        return nested
    lines = _as_dict(data.get("lines")).get("data") or []
    if isinstance(lines, list):
        for line in lines:
            line_d = _as_dict(line)
            line_parent = _as_dict(line_d.get("parent"))
            si = _as_dict(line_parent.get("subscription_item_details"))
            sid = si.get("subscription")
            if isinstance(sid, str) and sid.startswith("sub_"):
                return sid
            sid = extract_subscription_id(line_d)
            if sid:
                return sid
    return None


def extract_price_id_from_invoice(invoice: Any) -> Optional[str]:
    data = _as_dict(invoice)
    lines = _as_dict(data.get("lines")).get("data") or []
    if isinstance(lines, list):
        for line in lines:
            pid = extract_price_id(line)
            if pid:
                return pid
    return None


def extract_price_id_from_subscription(subscription: Any) -> Optional[str]:
    data = _as_dict(subscription)
    items = _as_dict(data.get("items")).get("data") or []
    if isinstance(items, list) and items:
        return extract_price_id(items[0])
    return None


class StripeConfig:
    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.environment = os.getenv("ENVIRONMENT", "development")

        self.prices = {
            "pro_month": (os.getenv("STRIPE_PRICE_PRO_MONTHLY") or "").strip() or None,
            "pro_year": (os.getenv("STRIPE_PRICE_PRO_ANNUALLY") or "").strip() or None,
            "business_month": (os.getenv("STRIPE_PRICE_BUSINESS_MONTHLY") or "").strip() or None,
            "business_year": (os.getenv("STRIPE_PRICE_BUSINESS_ANNUALLY") or "").strip() or None,
        }

        self.price_to_plan: Dict[str, str] = {}
        for key, price_id in self.prices.items():
            if price_id:
                plan_id = key.split("_")[0]
                self.price_to_plan[price_id] = plan_id

        if self.secret_key:
            if self.environment == "production" and not self.secret_key.startswith("sk_live_"):
                logger.warning("CRITICAL: Running in production but using Stripe test keys!")
            elif self.environment != "production" and self.secret_key.startswith("sk_live_"):
                logger.warning("CRITICAL: Running in development but using Stripe LIVE keys!")

            stripe.api_key = self.secret_key

    def get_price_id(self, plan_id: str, billing_cycle: str) -> str:
        key = f"{plan_id}_{billing_cycle}"
        price_id = self.prices.get(key)
        if not price_id:
            logger.error(f"Price ID not configured for {key}")
            raise HTTPException(status_code=400, detail="Plan pricing not configured")
        return price_id

    def get_plan_id_by_price_id(self, price_id: str) -> Optional[str]:
        if not price_id:
            return None
        return self.price_to_plan.get(price_id)


class StripeService:
    def __init__(
        self,
        user_service: UserService,
        stripe_event_repo: StripeEventRepository,
        credit_service: CreditService,
    ):
        self.user_service = user_service
        self.stripe_event_repo = stripe_event_repo
        self.credit_service = credit_service
        self.config = StripeConfig()

    @classmethod
    def from_db(cls, db: AsyncIOMotorDatabase) -> "StripeService":
        user_repo = UserRepository(db["users"])
        folder_repo = FolderEntryRepository(db["folder_entries"])
        user_service = UserService(user_repo, folder_repo)
        stripe_event_repo = StripeEventRepository(db["stripe_webhook_events"])
        credit_service = CreditService.from_db(db, user_repo=user_repo)
        return cls(user_service, stripe_event_repo, credit_service)

    async def create_checkout_session(
        self,
        user: User,
        plan_id: str,
        billing_cycle: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        if not self.config.secret_key:
            raise HTTPException(status_code=503, detail="Stripe integration not configured")

        if user.stripe_subscription_status in ["active", "trialing"] and user.plan_id != "free":
            raise HTTPException(
                status_code=400,
                detail="User already has an active subscription. Please manage your billing through the portal.",
            )

        price_id = self.config.get_price_id(plan_id, billing_cycle)

        try:
            customer_id = user.stripe_customer_id
            if not customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.username,
                    metadata={"user_id": str(user.id)},
                )
                customer_id = customer.id
                await self.user_service.user_repo.update_user(
                    user.id, {"stripe_customer_id": customer_id}
                )

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(user.id),
                metadata={"user_id": str(user.id), "plan_id": plan_id},
                subscription_data={"metadata": {"user_id": str(user.id), "plan_id": plan_id}},
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise HTTPException(status_code=500, detail="Payment service error")

    async def create_portal_session(self, user: User, return_url: str) -> str:
        if not self.config.secret_key:
            raise HTTPException(status_code=503, detail="Stripe integration not configured")

        if not user.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No active billing account")

        try:
            session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {str(e)}")
            raise HTTPException(status_code=500, detail="Billing portal error")

    async def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        if not self.config.webhook_secret:
            logger.warning("Stripe webhook received but no webhook secret configured")
            return

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.config.webhook_secret
            )
        except ValueError:
            logger.error("Invalid Stripe payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        event_id = event["id"]
        event_type = event["type"]

        logger.info(f"Received Stripe webhook: {event_type} [id: {event_id}]")

        import json

        raw_payload = json.loads(payload.decode("utf-8"))
        raw_data = raw_payload.get("data", {}).get("object", {})
        data = raw_data

        webhook_event = StripeWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=raw_data,
        )

        inserted = await self.stripe_event_repo.mark_as_pending(webhook_event)
        if not inserted:
            logger.info(f"Webhook event {event_id} already processed or in progress. Skipping.")
            return

        try:
            if event_type == "checkout.session.completed":
                await self._handle_checkout_completed(data)
            elif event_type in [
                "customer.subscription.created",
                "customer.subscription.updated",
            ]:
                await self._handle_subscription_updated(data)
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(data)
            elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
                await self._handle_invoice_paid(data)
            elif event_type == "invoice.payment_failed":
                logger.warning(
                    f"Payment failed for invoice {data.get('id')} customer {data.get('customer')}"
                )
            else:
                logger.debug(f"Unhandled Stripe webhook event type: {event_type}")

            await self.stripe_event_repo.mark_as_processed(event_id)

        except Exception as e:
            logger.error(f"Error processing webhook event {event_id}: {str(e)}")
            await self.stripe_event_repo.mark_as_failed(event_id, str(e))
            raise

    async def _apply_paid_plan(
        self,
        user: User,
        plan_id: str,
        *,
        subscription_id: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> User:
        from core.brevio_api.services.billing.plan_registry import get_plan

        try:
            plan = get_plan(plan_id)
        except KeyError:
            logger.error("event=stripe_unknown_plan plan_id=%s user_id=%s", plan_id, user.id)
            return user

        updates: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
        }
        if subscription_id:
            updates["stripe_subscription_id"] = subscription_id
        if status:
            updates["stripe_subscription_status"] = status
        if customer_id:
            updates["stripe_customer_id"] = customer_id

        updated = await self.user_service.user_repo.update_user(user.id, updates)
        logger.info(
            "event=stripe_plan_applied user_id=%s plan_id=%s version=%s status=%s",
            user.id,
            plan.plan_id,
            plan.version,
            status,
        )
        return updated or user

    async def _grant_plan_credits(
        self, user: User, plan_id: str, invoice_id: str
    ) -> bool:
        from core.brevio_api.services.billing.plan_registry import get_plan

        try:
            plan = get_plan(plan_id)
        except KeyError:
            logger.error(
                "event=stripe_credit_grant_unknown_plan plan_id=%s invoice=%s",
                plan_id,
                invoice_id,
            )
            return False
        if plan.credits_per_period <= 0:
            return False
        return await self.credit_service.grant_subscription_credits(
            str(user.id),
            int(plan.credits_per_period),
            invoice_id,
            rollover_max=int(plan.rollover_max),
        )

    async def _handle_checkout_completed(self, session: Any) -> None:
        data = _as_dict(session)
        metadata = _as_dict(data.get("metadata"))
        user_id = metadata.get("user_id") or data.get("client_reference_id")
        customer_id = data.get("customer")
        subscription_id = extract_subscription_id(data) or data.get("subscription")
        plan_id = metadata.get("plan_id")

        if not user_id:
            logger.error("No user_id in checkout session metadata")
            return

        logger.info(
            "Checkout completed for user %s plan_id=%s subscription=%s",
            user_id,
            plan_id,
            subscription_id,
        )

        user = await self.user_service.get_user_by_id(str(user_id))
        updates: Dict[str, Any] = {}
        if customer_id:
            updates["stripe_customer_id"] = customer_id
        if subscription_id:
            updates["stripe_subscription_id"] = subscription_id
        if updates:
            await self.user_service.user_repo.update_user(ObjectId(str(user_id)), updates)
            user = await self.user_service.get_user_by_id(str(user_id))

        # Prefer metadata plan; fall back to live subscription price mapping.
        if not plan_id and subscription_id and self.config.secret_key:
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                price_id = extract_price_id_from_subscription(sub)
                plan_id = self.config.get_plan_id_by_price_id(price_id) if price_id else None
            except Exception as e:
                logger.error("Failed to retrieve subscription %s: %s", subscription_id, e)

        if plan_id and plan_id != "free":
            user = await self._apply_paid_plan(
                user,
                str(plan_id),
                subscription_id=subscription_id if isinstance(subscription_id, str) else None,
                status="active",
                customer_id=customer_id if isinstance(customer_id, str) else None,
            )

        # Grant credits from the checkout invoice when present (idempotent with invoice.paid).
        invoice_id = data.get("invoice")
        if isinstance(invoice_id, dict):
            invoice_id = invoice_id.get("id")
        if plan_id and plan_id != "free" and isinstance(invoice_id, str):
            await self._grant_plan_credits(user, str(plan_id), invoice_id)
        elif plan_id and plan_id != "free" and subscription_id and self.config.secret_key:
            try:
                invoices = stripe.Invoice.list(
                    subscription=subscription_id, status="paid", limit=1
                )
                data_list = getattr(invoices, "data", None) or []
                if data_list:
                    inv = data_list[0]
                    inv_id = inv.get("id") if isinstance(inv, dict) else getattr(inv, "id", None)
                    if inv_id:
                        await self._grant_plan_credits(user, str(plan_id), str(inv_id))
            except Exception as e:
                logger.error(
                    "Checkout credit bootstrap failed for subscription %s: %s",
                    subscription_id,
                    e,
                )

    async def _handle_subscription_updated(self, subscription: Any) -> None:
        data = _as_dict(subscription)
        customer_id = data.get("customer")
        status = data.get("status")
        subscription_id = data.get("id")
        metadata = _as_dict(data.get("metadata"))

        user = await self.user_service.get_user_by_stripe_customer_id(customer_id)
        if not user:
            # Fallback: metadata.user_id from subscription_data
            uid = metadata.get("user_id")
            if uid:
                try:
                    user = await self.user_service.get_user_by_id(str(uid))
                except Exception:
                    user = None
        if not user:
            logger.error(f"User not found for Stripe customer {customer_id}")
            return

        logger.info(f"Subscription updated for customer {customer_id}, status: {status}")

        if status in ["canceled", "unpaid", "past_due", "incomplete_expired"]:
            await self.user_service.user_repo.update_user(
                user.id,
                {
                    "stripe_subscription_id": subscription_id,
                    "stripe_subscription_status": status,
                    "plan_id": "free",
                    "plan_version": "1",
                },
            )
            return

        if status in ["active", "trialing"]:
            plan_id = metadata.get("plan_id")
            if not plan_id:
                price_id = extract_price_id_from_subscription(data)
                plan_id = self.config.get_plan_id_by_price_id(price_id) if price_id else None
            if plan_id:
                await self._apply_paid_plan(
                    user,
                    str(plan_id),
                    subscription_id=subscription_id if isinstance(subscription_id, str) else None,
                    status=str(status),
                    customer_id=customer_id if isinstance(customer_id, str) else None,
                )
            else:
                logger.warning(
                    "Unknown price on subscription %s for customer %s",
                    subscription_id,
                    customer_id,
                )
                await self.user_service.user_repo.update_user(
                    user.id,
                    {
                        "stripe_subscription_id": subscription_id,
                        "stripe_subscription_status": status,
                    },
                )

    async def _handle_subscription_deleted(self, subscription: Any) -> None:
        data = _as_dict(subscription)
        customer_id = data.get("customer")

        user = await self.user_service.get_user_by_stripe_customer_id(customer_id)
        if not user:
            logger.error(f"User not found for Stripe customer {customer_id}")
            return

        logger.info(f"Subscription deleted for customer {customer_id}, reverting to free")
        await self.user_service.user_repo.update_user(
            user.id,
            {
                "stripe_subscription_status": "canceled",
                "plan_id": "free",
                "plan_version": "1",
            },
        )

    async def _handle_invoice_paid(self, invoice: Any) -> None:
        data = _as_dict(invoice)
        customer_id = data.get("customer")
        invoice_id = data.get("id")
        if not invoice_id:
            logger.error("Invoice payload missing id")
            return

        user = await self.user_service.get_user_by_stripe_customer_id(customer_id)
        if not user:
            logger.error(f"User not found for Stripe customer {customer_id}")
            return

        subscription_id = extract_subscription_id(data)
        if not subscription_id:
            # One-off invoices are ignored.
            logger.info(f"Invoice {invoice_id} is not for a subscription, skipping credit grant.")
            return

        price_id = extract_price_id_from_invoice(data)
        plan_id = self.config.get_plan_id_by_price_id(price_id) if price_id else None
        if not plan_id:
            # Fallback to subscription metadata / live retrieve.
            meta_plan = None
            try:
                if self.config.secret_key:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    sub_d = _as_dict(sub)
                    meta_plan = _as_dict(sub_d.get("metadata")).get("plan_id")
                    if not meta_plan:
                        pid = extract_price_id_from_subscription(sub_d)
                        meta_plan = self.config.get_plan_id_by_price_id(pid) if pid else None
            except Exception as e:
                logger.error("Failed subscription fallback for invoice %s: %s", invoice_id, e)
            plan_id = meta_plan

        if not plan_id:
            logger.error(f"Could not determine plan for invoice {invoice_id}")
            return

        user = await self._apply_paid_plan(
            user,
            str(plan_id),
            subscription_id=subscription_id,
            status="active",
            customer_id=customer_id if isinstance(customer_id, str) else None,
        )
        try:
            granted = await self._grant_plan_credits(user, str(plan_id), str(invoice_id))
            logger.info(
                "event=stripe_invoice_paid user_id=%s plan_id=%s invoice=%s granted=%s",
                user.id,
                plan_id,
                invoice_id,
                granted,
            )
        except Exception as e:
            logger.error(f"Failed to grant credits for invoice {invoice_id}: {e}")
            raise

    async def sync_user_subscription(
        self, user: User, *, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pull latest Stripe subscription/invoice state into local plan + credits.

        Used after Checkout return so the UI does not depend solely on webhook timing.
        When ``session_id`` is provided (Checkout success URL), prefer that session.
        """
        if not self.config.secret_key:
            raise HTTPException(status_code=503, detail="Stripe integration not configured")

        # Prefer Checkout Session when returning from payment — most reliable path.
        if session_id and str(session_id).startswith("cs_"):
            try:
                session = stripe.checkout.Session.retrieve(str(session_id))
                sess = _as_dict(session)
                meta = _as_dict(sess.get("metadata"))
                # Ownership check: session must belong to this user.
                ref = sess.get("client_reference_id") or meta.get("user_id")
                if ref and str(ref) != str(user.id):
                    raise HTTPException(status_code=403, detail="Checkout session mismatch")
                customer_id = sess.get("customer")
                if isinstance(customer_id, dict):
                    customer_id = customer_id.get("id")
                if customer_id and customer_id != user.stripe_customer_id:
                    await self.user_service.user_repo.update_user(
                        user.id, {"stripe_customer_id": customer_id}
                    )
                    user = await self.user_service.get_user_by_id(str(user.id))
                # Reuse checkout handler (plan + credits).
                await self._handle_checkout_completed(sess)
                user = await self.user_service.get_user_by_id(str(user.id))
                balance = await self.credit_service.get_balance(str(user.id))
                return {
                    "plan_id": user.plan_id,
                    "plan_version": getattr(user, "plan_version", None),
                    "stripe_subscription_status": user.stripe_subscription_status,
                    "credits_balance": balance,
                    "credits_granted": True,
                    "synced": True,
                    "via": "checkout_session",
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "sync via checkout session failed user=%s session=%s: %s",
                    user.id,
                    session_id,
                    e,
                )

        if not user.stripe_customer_id:
            return {
                "plan_id": user.plan_id,
                "synced": False,
                "reason": "no_customer",
            }

        subs = stripe.Subscription.list(
            customer=user.stripe_customer_id, status="all", limit=10
        )
        active = None
        for sub in getattr(subs, "data", []) or []:
            status = sub.get("status") if isinstance(sub, dict) else getattr(sub, "status", None)
            if status in ("active", "trialing"):
                active = sub
                break

        if active is None:
            # Do not downgrade during checkout race (session paid but sub not listed yet).
            if session_id:
                return {
                    "plan_id": user.plan_id,
                    "synced": False,
                    "reason": "subscription_pending",
                }
            await self.user_service.user_repo.update_user(
                user.id,
                {
                    "plan_id": "free",
                    "plan_version": "1",
                    "stripe_subscription_status": "canceled",
                },
            )
            return {"plan_id": "free", "synced": True, "status": "canceled"}

        sub_d = _as_dict(active)
        subscription_id = sub_d.get("id")
        status = sub_d.get("status")
        meta_plan = _as_dict(sub_d.get("metadata")).get("plan_id")
        price_id = extract_price_id_from_subscription(sub_d)
        plan_id = meta_plan or (
            self.config.get_plan_id_by_price_id(price_id) if price_id else None
        )
        if not plan_id:
            logger.error(
                "sync: unknown price_id=%s subscription=%s", price_id, subscription_id
            )
            return {
                "plan_id": user.plan_id,
                "synced": False,
                "reason": "unknown_price",
                "price_id": price_id,
            }

        user = await self._apply_paid_plan(
            user,
            str(plan_id),
            subscription_id=subscription_id if isinstance(subscription_id, str) else None,
            status=str(status) if status else "active",
            customer_id=user.stripe_customer_id,
        )

        granted = False
        try:
            invoices = stripe.Invoice.list(
                customer=user.stripe_customer_id, status="paid", limit=3
            )
            for inv in getattr(invoices, "data", []) or []:
                inv_d = _as_dict(inv)
                inv_sub = extract_subscription_id(inv_d)
                if subscription_id and inv_sub and inv_sub != subscription_id:
                    continue
                inv_id = inv_d.get("id")
                if not inv_id:
                    continue
                granted = await self._grant_plan_credits(user, str(plan_id), str(inv_id)) or granted
                break
        except Exception as e:
            logger.error("sync credit grant failed user=%s: %s", user.id, e)

        balance = await self.credit_service.get_balance(str(user.id))
        return {
            "plan_id": plan_id,
            "plan_version": getattr(user, "plan_version", None),
            "stripe_subscription_status": status,
            "credits_balance": balance,
            "credits_granted": granted,
            "synced": True,
            "via": "subscription_list",
        }
