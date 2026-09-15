from enum import Enum


class ProviderErrorKind(str, Enum):
    INVALID_CREDENTIAL = "INVALID_CREDENTIAL"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"
    USER_CREDENTIAL_REQUIRED = "USER_CREDENTIAL_REQUIRED"
    PLATFORM_CREDENTIAL_UNAVAILABLE = "PLATFORM_CREDENTIAL_UNAVAILABLE"
    CREDENTIAL_UNAVAILABLE = "CREDENTIAL_UNAVAILABLE"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    MODEL_NOT_ALLOWED = "MODEL_NOT_ALLOWED"


class ProviderError(Exception):
    def __init__(
        self, kind: ProviderErrorKind, message: str, original_error: Exception = None
    ):
        self.kind = kind
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
