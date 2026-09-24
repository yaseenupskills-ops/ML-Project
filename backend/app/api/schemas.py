"""Pydantic request/response models (PRD §7.2, §7.3)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    must_change_password: bool
    assigned_subject_ids: list[uuid.UUID]


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    role: str


class UserCreateResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    temporary_password: str
    must_change_password: bool


class UserUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    status: str | None = None
    notify_email: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    status: str
    notify_email: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime


class ResetPasswordResponse(BaseModel):
    temporary_password: str


class SubjectIdsRequest(BaseModel):
    subject_ids: list[uuid.UUID]
