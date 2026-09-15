from __future__ import annotations

from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.shared.enums.job_status import JobPhase


class TranscriptionError(Exception):
    """Typed transcription failure. Message is the stable error code for i18n."""

    def __init__(
        self,
        code: ApiErrorCode | str,
        *,
        phase: str = JobPhase.TRANSCRIBING.value,
    ) -> None:
        code_value = code.value if isinstance(code, ApiErrorCode) else code
        self.code = code_value
        self.phase = phase
        super().__init__(code_value)
