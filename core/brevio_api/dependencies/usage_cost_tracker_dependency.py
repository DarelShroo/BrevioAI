from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker


def get_cost_token_tracker() -> UsageCostTracker:
    return UsageCostTracker()
