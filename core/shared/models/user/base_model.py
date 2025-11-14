from typing import Annotated, Any, Dict, Optional

from bson import ObjectId
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, PlainSerializer, field_validator


def serialize_object_id(value: ObjectId) -> str:
    return str(value)


def validate_object_id(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError(f"Invalid ObjectId: {value}")


SerializedObjectId = Annotated[
    ObjectId, PlainSerializer(serialize_object_id, return_type=str)
]


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: Optional[SerializedObjectId] = Field(
        default_factory=ObjectId,
        alias="_id",
        description="Unique identifier for the model",
    )

    @field_validator("id", mode="before")
    @classmethod
    def check_id(cls, v: Any) -> ObjectId:
        if v is None:
            return ObjectId()
        return validate_object_id(v)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)

    async def to_mongo(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        if "_id" not in data and "id" in data:
            data["_id"] = data["id"]
        data.pop("id", None)
        return {k: v for k, v in data.items() if v is not None}
