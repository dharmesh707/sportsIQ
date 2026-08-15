from datetime import datetime

from pydantic import EmailStr, Field

from .base import CamelModel


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8)


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
