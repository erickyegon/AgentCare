"""Auth & user schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Patients may self-register; staff/admin accounts are provisioned by an admin/seed.
    phone: str | None = Field(default=None, max_length=40)
    date_of_birth: date | None = None
    preferred_language: str = "English"
    emergency_contact: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    name: str


class ProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=40)
    date_of_birth: date | None = None
    preferred_language: str | None = None
    emergency_contact: str | None = Field(default=None, max_length=255)


class PatientProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date_of_birth: date | None
    phone: str | None
    preferred_language: str
    emergency_contact: str | None
    mrn: str | None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    profile: PatientProfileOut | None = None
