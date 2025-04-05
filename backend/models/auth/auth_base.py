import re
from typing import Union  # 'Type' ya no es necesario

from pydantic import BaseModel, EmailStr, Field, field_validator


class AuthWithPassword(BaseModel):
    password: str = Field(
        ...,
        min_length=8,
    )

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe tener al menos una letra mayúscula.")
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe tener al menos una letra minúscula.")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe tener al menos un número.")
        if not re.search(r"[\W_]", value):
            raise ValueError("La contraseña debe tener al menos un carácter especial.")

        return value


class IdentityBase(BaseModel):
    identity: Union[str, EmailStr]

    @field_validator("identity")
    def validate_identity(cls, v: Union[str, EmailStr]) -> Union[str, EmailStr]:
        if isinstance(v, str):
            if "@" in v:
                try:
                    from email_validator import EmailNotValidError, validate_email

                    # Pass allow_smtputf8=False to ensure compatibility with all mail systems
                    # test_environment=True to explicitly allow example.com domains
                    email_info = validate_email(
                        v, allow_smtputf8=False, test_environment=True
                    )
                    return email_info.normalized  # Return the normalized email
                except EmailNotValidError:
                    raise ValueError("El formato del correo electrónico es inválido")
            else:
                if len(v) > 100:
                    raise ValueError(
                        "La longitud del campo debe ser de máximo 100 caracteres"
                    )
                return v
        raise ValueError("El valor de identidad no es válido")
