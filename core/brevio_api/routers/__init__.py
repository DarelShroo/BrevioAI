from .auth_router import AuthRoutes, auth_router
from .brevio_router import brevio_router
from .events_router import events_router
from .user_credential_router import router as user_credential_router
from .user_router import user_router

__all__ = [
    "AuthRoutes",
    "auth_router",
    "brevio_router",
    "events_router",
    "user_router",
    "user_credential_router",
]
