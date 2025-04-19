from typing import Any

from pydantic import field_validator

from core.brevio.enums.model import ModelType
from core.brevio.models.base_model import BaseModel


class SummaryConfig(BaseModel):
    model: ModelType
    category: str | None = None
    style: str | None = None

    @field_validator("model", mode="before")
    @classmethod
    def convert_enum(cls, value: Any, info: Any) -> Any:
        enum_type = cls.__annotations__.get(info.field_name, None)

        if enum_type is None or not hasattr(enum_type, "__getitem__"):
            raise ValueError(f"Invalid field: {info.field_name}")

        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid {info.field_name}: {value}")

        return value
