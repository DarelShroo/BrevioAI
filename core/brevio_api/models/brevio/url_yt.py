import re
from urllib.parse import urlparse

from pydantic import BaseModel, HttpUrl, ValidationError, field_validator


class UrlYT(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        youtube_regex = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
        if not re.match(youtube_regex, str(v)):
            raise ValueError("La URL debe ser de YouTube")
        return v
