from pydantic import BaseModel, ConfigDict


class BaseResponseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
