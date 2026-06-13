"""
User Pydantic schemas
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: str = "member"


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating user fields (all optional)."""
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    """Public user info (no password)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime


class UserInDB(UserOut):
    """Internal: includes password hash. Never return this from API."""
    password_hash: str
