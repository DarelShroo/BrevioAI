from pathlib import Path
from typing import List, Optional, Type, Union

from bson import ObjectId
from pydantic import BaseModel, FilePath, HttpUrl, field_validator, model_validator

from core.brevio.models.prompt_config_model import PromptConfig


class MediaEntry(BaseModel):
    url: Optional[HttpUrl] = None
    path: Optional[FilePath] = None

    @model_validator(mode="after")
    def validate_media(self) -> "MediaEntry":
        if not self.url and not self.path:
            raise ValueError("Se requiere 'url' o 'path'")
        return self

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls: Type["MediaEntry"], v: Optional[str]) -> Optional[Path]:
        if v is None:
            return None

        path = Path(v) if not isinstance(v, Path) else v

        if not str(path).strip():
            raise ValueError("Path cannot be empty")

        return path


class BaseBrevioGenerate(BaseModel):
    prompt_config: PromptConfig

    @field_validator("prompt_config", mode="before")
    def validate_prompt_config(
        cls, v: Union[dict, PromptConfig]
    ) -> Union[dict, PromptConfig]:
        if isinstance(v, dict):
            # Handle case where _id might be a string
            if "_id" in v and isinstance(v["_id"], str):
                v["_id"] = ObjectId(v["_id"])
        return v


class BrevioGenerate(BaseBrevioGenerate):
    data: List[MediaEntry]
