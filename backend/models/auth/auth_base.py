from typing import Union
from pydantic import BaseModel, EmailStr, Field, field_validator
import re
class AuthWithPassword(BaseModel):
    password: str = Field(
        ...,
        min_length=8,
    )
    @field_validator('password')
    def validate_password(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('La contraseña debe tener al menos una letra mayúscula.')
        if not re.search(r'[a-z]', value):
            raise ValueError('La contraseña debe tener al menos una letra minúscula.')
        if not re.search(r'\d', value):
            raise ValueError('La contraseña debe tener al menos un número.')
        if not re.search(r'[\W_]', value):
            raise ValueError('La contraseña debe tener al menos un carácter especial.')

        return value

class IdentityBase(BaseModel):
    identity: Union[str, EmailStr]


