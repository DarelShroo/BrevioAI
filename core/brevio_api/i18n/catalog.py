"""Backend error message localization catalog."""

from __future__ import annotations

from typing import Dict

from core.brevio_api.models.errors.api_codes import ApiErrorCode

ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        ApiErrorCode.CREDENTIAL_ID_INVALID.value: "Invalid credential ID",
        ApiErrorCode.CREDENTIAL_NAME_REQUIRED.value: "Credential name is required",
        ApiErrorCode.CREDENTIAL_NOT_FOUND.value: "Credential not found",
        ApiErrorCode.NOTHING_TO_UPDATE.value: "Nothing to update",
        ApiErrorCode.EXAMPLE_NOT_FOUND.value: "Example not found",
        ApiErrorCode.SUMMARY_NOT_FOUND.value: "Summary not found",
        ApiErrorCode.PDF_NOT_FOUND.value: "PDF not found",
        ApiErrorCode.MISSING_SIGNATURE.value: "Missing signature",
        ApiErrorCode.INVALID_PAYLOAD.value: "Invalid payload",
        ApiErrorCode.PASSWORD_TOO_SHORT.value: "Password must be at least 8 characters long",
        ApiErrorCode.PASSWORD_NO_UPPERCASE.value: "Password must contain at least one uppercase letter",
        ApiErrorCode.PASSWORD_NO_LOWERCASE.value: "Password must contain at least one lowercase letter",
        ApiErrorCode.PASSWORD_NO_DIGIT.value: "Password must contain at least one number",
        ApiErrorCode.PASSWORD_NO_SPECIAL.value: "Password must contain at least one special character",
        ApiErrorCode.USERNAME_TOO_SHORT.value: "Username must be at least 6 characters long",
        ApiErrorCode.INVALID_IDENTITY_FORMAT.value: "Invalid identity format: must be a valid username or email",
        ApiErrorCode.SUMMARY_GENERATION_FAILED.value: "Summary generation failed",
        ApiErrorCode.FOLDER_NOT_FOUND.value: "Folder not found",
        ApiErrorCode.FOLDER_NAME_INVALID.value: "Invalid folder name",
        ApiErrorCode.ENTRY_NOT_FOUND.value: "Entry not found",
        ApiErrorCode.FILE_FORMAT_NOT_ALLOWED.value: "File format not allowed",
    },
    "es": {
        ApiErrorCode.CREDENTIAL_ID_INVALID.value: "ID de credencial inválido",
        ApiErrorCode.CREDENTIAL_NAME_REQUIRED.value: "El nombre de la credencial es obligatorio",
        ApiErrorCode.CREDENTIAL_NOT_FOUND.value: "Credencial no encontrada",
        ApiErrorCode.NOTHING_TO_UPDATE.value: "Nada que actualizar",
        ApiErrorCode.EXAMPLE_NOT_FOUND.value: "Ejemplo no encontrado",
        ApiErrorCode.SUMMARY_NOT_FOUND.value: "Resumen no encontrado",
        ApiErrorCode.PDF_NOT_FOUND.value: "PDF no encontrado",
        ApiErrorCode.MISSING_SIGNATURE.value: "Falta la firma de autenticación",
        ApiErrorCode.INVALID_PAYLOAD.value: "Carga útil no válida",
        ApiErrorCode.PASSWORD_TOO_SHORT.value: "La contraseña debe tener al menos 8 caracteres",
        ApiErrorCode.PASSWORD_NO_UPPERCASE.value: "La contraseña debe tener al menos una letra mayúscula",
        ApiErrorCode.PASSWORD_NO_LOWERCASE.value: "La contraseña debe tener al menos una letra minúscula",
        ApiErrorCode.PASSWORD_NO_DIGIT.value: "La contraseña debe tener al menos un número",
        ApiErrorCode.PASSWORD_NO_SPECIAL.value: "La contraseña debe tener al menos un carácter especial",
        ApiErrorCode.USERNAME_TOO_SHORT.value: "El nombre de usuario debe tener al menos 6 caracteres",
        ApiErrorCode.INVALID_IDENTITY_FORMAT.value: "Formato de identidad no válido: debe ser un usuario o correo válido",
        ApiErrorCode.SUMMARY_GENERATION_FAILED.value: "Falló la generación del resumen",
        ApiErrorCode.FOLDER_NOT_FOUND.value: "Carpeta no encontrada",
        ApiErrorCode.FOLDER_NAME_INVALID.value: "Nombre de carpeta no válido",
        ApiErrorCode.ENTRY_NOT_FOUND.value: "Entrada no encontrada",
        ApiErrorCode.FILE_FORMAT_NOT_ALLOWED.value: "Formato de archivo no permitido",
    },
}


def get_localized_error_message(code: ApiErrorCode | str, locale: str = "en") -> str:
    """Retrieve localized error message with explicit fallback."""
    code_value = code.value if isinstance(code, ApiErrorCode) else str(code)
    loc_messages = ERROR_MESSAGES.get(locale, ERROR_MESSAGES["en"])
    if code_value in loc_messages:
        return loc_messages[code_value]
    if code_value in ERROR_MESSAGES["en"]:
        return ERROR_MESSAGES["en"][code_value]
    return code_value
