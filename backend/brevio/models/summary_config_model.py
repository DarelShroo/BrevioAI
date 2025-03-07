from pydantic import BaseModel, field_validator
from backend.brevio.enums.model import ModelType

class SummaryConfig(BaseModel):
    model: ModelType
    category: str | None = None
    style: str | None = None

    @field_validator('model', mode='before')
    def convert_enum(cls, value, info):
        enum_type = cls.model_fields[info.field_name].annotation
        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid {info.field_name}: {value}")
        return value