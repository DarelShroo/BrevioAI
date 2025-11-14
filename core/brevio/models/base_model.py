from typing import Annotated, Any, Dict, Optional

try:
    from bson import ObjectId
except ImportError:
    # Fallback for environments without bson
    class _ObjectId:
        """Stub ObjectId when bson is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, PlainSerializer


def serialize_object_id(value: ObjectId) -> str:
    return str(value)


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

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)
