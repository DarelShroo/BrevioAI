from typing import Dict, Union
from .auth_base import AuthWithPassword, IdentityBase
from pydantic import EmailStr, Field, field_validator, model_validator, root_validator

class LoginUser(AuthWithPassword, IdentityBase):
    @field_validator('identity')
    def validate_identity(cls, v: Union[str, EmailStr]) -> Union[str, EmailStr]:
        if "@" in v:
            try:
                return EmailStr(v)
            except Exception:
                raise ValueError("El formato del correo electrónico es inválido")
        else:
            if len(v) > 100:
                raise ValueError("La longitud del campo debe ser de máximo 100 caracteres")
            return v

class RegisterUser(AuthWithPassword):
    username: str = Field("", strict=True, max_length=100)
    email: EmailStr

    @model_validator(mode='before')
    def check_username_length(cls, values):
        username = values.get('username')
        if username and len(username) < 6:
            raise ValueError("El nombre de usuario debe tener al menos 6 caracteres.")
        return values

    def to_dict(self) -> Dict:
        return self.model_dump(exclude_unset=True)

class RecoveryPasswordOtp(AuthWithPassword):
    email: EmailStr
    otp: int

class UserIdentity(IdentityBase):
    pass

class RecoveryPassword(UserIdentity):
    pass