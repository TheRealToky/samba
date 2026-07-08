"""Pydantic schemas for users and auth I/O."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import RoleEnum


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: RoleEnum
    created_at: datetime


class RoleUpdate(BaseModel):
    role: RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
