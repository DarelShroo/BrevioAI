from pydantic import BaseModel


class UsageCostTracker:
    def __init__(self) -> None:
        self.total_media_minutes_cost = 0.0
        self.total_tokens_cost = 0.0
        self.total_processing_time_cost = 0.0

    def add_media_minutes_cost(self, cost: float) -> None:
        self.total_media_minutes_cost += cost

    def add_tokens_cost(self, cost: float) -> None:
        print("Adding tokens cost: %.6f", cost)
        self.total_tokens_cost += cost

    def add_processing_time_cost(self, cost: float) -> None:
        self.total_processing_time_cost += cost

    def get_total_cost(self) -> float:
        return (
            self.total_media_minutes_cost
            + self.total_tokens_cost
            + self.total_processing_time_cost
        )

    def get_cost_breakdown(self) -> dict:
        return {
            "media_minutes_cost": self.total_media_minutes_cost,
            "tokens_cost": self.total_tokens_cost,
            "processing_time_cost": self.total_processing_time_cost,
            "total_cost": self.get_total_cost(),
        }

    def reset_costs(self) -> None:
        self.total_media_minutes_cost = 0.0
        self.total_tokens_cost = 0.0
        self.total_processing_time_cost = 0.0
