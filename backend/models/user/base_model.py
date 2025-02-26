from bson import ObjectId
import pydantic
class BaseModel(pydantic.BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
