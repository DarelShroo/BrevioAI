"""Tests for backend i18n locale negotiation and error message catalog."""

from core.brevio_api.i18n.catalog import get_localized_error_message
from core.brevio_api.i18n.locale import parse_accept_language, resolve_request_locale
from core.brevio_api.models.errors.api_codes import ApiErrorCode


def test_parse_accept_language_formats() -> None:
    assert parse_accept_language("es-ES,es;q=0.9,en;q=0.8") == ["es", "es", "en"]
    assert parse_accept_language("fr-CA, fr;q=0.9") == ["fr", "fr"]
    assert parse_accept_language("") == []
    assert parse_accept_language(None) == []


def test_resolve_request_locale_selection() -> None:
    assert resolve_request_locale("es-ES,es;q=0.9") == "es"
    assert resolve_request_locale("de-DE,de;q=0.9") == "de"
    assert resolve_request_locale("fr-FR,fr;q=0.9") == "fr"
    assert resolve_request_locale("ja") == "ja"
    assert resolve_request_locale("xx-YY,zz") == "en"  # fallback to default
    assert resolve_request_locale(None) == "en"


def test_localized_error_messages_by_code() -> None:
    msg_en = get_localized_error_message(ApiErrorCode.CREDENTIAL_NOT_FOUND, locale="en")
    msg_es = get_localized_error_message(ApiErrorCode.CREDENTIAL_NOT_FOUND, locale="es")

    assert msg_en == "Credential not found"
    assert msg_es == "Credencial no encontrada"

    # Validation errors
    pw_en = get_localized_error_message(ApiErrorCode.PASSWORD_TOO_SHORT, locale="en")
    pw_es = get_localized_error_message(ApiErrorCode.PASSWORD_TOO_SHORT, locale="es")
    assert pw_en == "Password must be at least 8 characters long"
    assert pw_es == "La contraseña debe tener al menos 8 caracteres"
