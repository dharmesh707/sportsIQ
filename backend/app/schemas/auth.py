from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from .base import CamelModel


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_must_be_reasonably_strong(cls, value: str) -> str:
        if value.isdigit():
            raise ValueError("Password cannot be entirely numeric.")
        if value.lower() == value or value.upper() == value:
            raise ValueError("Password must contain both uppercase and lowercase letters.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number.")
        return value


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: str
    email: EmailStr
    created_at: datetime


class AuthResponse(CamelModel):
    access_token: str
    user: UserOut


class MeResponse(CamelModel):
    user: UserOut
