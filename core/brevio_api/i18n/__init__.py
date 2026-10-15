"""Backend i18n package."""

from core.brevio_api.i18n.catalog import get_localized_error_message
from core.brevio_api.i18n.locale import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    resolve_request_locale,
)

__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "resolve_request_locale",
    "get_localized_error_message",
]
