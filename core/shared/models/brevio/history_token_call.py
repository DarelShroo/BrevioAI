from pydantic import BaseModel, computed_field

from core.shared.enums.type_call import TypeCall


class HistoryTokenCall(BaseModel):
    type_call: TypeCall
    system_prompt_tokens: int
    user_prompt_tokens: int
    response_tokens: int
    request_index: int = 0
    duration_seconds: float = 0.0
    finish_reason: str = "unknown"
    requested_output_tokens: int = 0
    budget_utilization: float = 0.0
    chunk_id: str | None = None
    reduce_level: int | None = None
    batch_index: int | None = None
    split_depth: int | None = None
    is_final_reduce: bool | None = None

    @computed_field
    @property
    def input_tokens(self) -> int:
        return self.system_prompt_tokens + self.user_prompt_tokens

    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.response_tokens
