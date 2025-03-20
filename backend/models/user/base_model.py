from bson import ObjectId
from pydantic import BaseModel, ConfigDict, PlainSerializer
from typing import Annotated

def serialize_object_id(value: ObjectId) -> str:
    return str(value)

SerializedObjectId = Annotated[
    ObjectId,
    PlainSerializer(serialize_object_id, return_type=str)
]

class BaseModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )

    id: SerializedObjectId