from pydantic import BaseModel

from core.shared.enums.type_call import TypeCall


class HistoryTokenCall(BaseModel):
    type_call: TypeCall
    system_prompt_tokens: int
    user_prompt_tokens: int
    response_tokens: int
