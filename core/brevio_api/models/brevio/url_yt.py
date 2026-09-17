from pydantic import BaseModel, HttpUrl, field_validator

from core.shared.utils.youtube_url import normalize_youtube_url


class UrlYT(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: HttpUrl) -> HttpUrl:
        # Raises ValueError on non-HTTPS / non-YouTube hosts (SSRF hardening).
        normalize_youtube_url(v)
        return v
