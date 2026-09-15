from datetime import datetime, timezone
from typing import Any, Dict

from bson import ObjectId
from pydantic import Field

from core.shared.models.user.base_model import BaseModel


class RefreshSession(BaseModel):
    user_id: ObjectId
    jti: str
    family_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False

    def to_document(self) -> Dict[str, Any]:
        return {
            "_id": self.id,
            "user_id": self.user_id,
            "jti": self.jti,
            "family_id": self.family_id,
            "token_hash": self.token_hash,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "revoked": self.revoked,
        }
