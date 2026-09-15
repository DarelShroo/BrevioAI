from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.access_policy import TranscriptionAccessPolicy
from core.brevio.services.transcription.catalog import (
    build_transcription_providers_payload,
    resolve_transcription_model,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.models import (
    default_transcription_model,
    get_transcription_model,
)
from core.brevio_api.models.errors.api_codes import ApiErrorCode


def test_openai_default_is_gpt_transcribe_not_whisper() -> None:
    default = default_transcription_model(TranscriptionProviderType.OPENAI)
    assert default.id == "gpt-transcribe"
    assert default.recommended is True
    assert default.status == "stable"
    whisper = get_transcription_model("whisper-1")
    assert whisper is not None
    assert whisper.status == "deprecated"
    assert whisper.recommended is False
    assert whisper.retirement == "2027-02-26"


def test_google_and_xai_models_are_catalogued() -> None:
    gemini = get_transcription_model("gemini-3.5-transcribe")
    assert gemini is not None
    assert gemini.provider is TranscriptionProviderType.GOOGLE
    xai = default_transcription_model(TranscriptionProviderType.XAI)
    assert xai.id == "stt"
    assert xai.vendor_model_id is None


def test_resolve_rejects_model_from_another_provider() -> None:
    try:
        resolve_transcription_model(
            TranscriptionProviderType.OPENAI, "gemini-3.5-transcribe"
        )
        raise AssertionError("expected TranscriptionError")
    except TranscriptionError as exc:
        assert exc.code == ApiErrorCode.TRANSCRIPTION_PROVIDER_UNKNOWN.value


def test_payload_includes_models_and_hides_local_in_production() -> None:
    payload = build_transcription_providers_payload(
        TranscriptionAccessPolicy(environment="production")
    )
    model_ids = {item["id"] for item in payload["models"]}
    assert "gpt-transcribe" in model_ids
    assert "gemini-3.5-transcribe" in model_ids
    assert "stt" in model_ids
    local = next(item for item in payload["models"] if item["id"] == "local_whisper")
    assert local["user_access"] is False
    assert "local_whisper" not in payload["selectable"]
    assert payload["default"] == "openai"
    assert payload["default_model"] == "gpt-transcribe"
