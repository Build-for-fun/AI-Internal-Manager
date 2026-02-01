"""Authentication schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    role: str | None = None
    department: str | None = None
    team: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: str
    full_name: str
    role: str | None
    department: str | None
    team: str | None
    is_active: bool
    preferences: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Schema for decoded JWT token data."""

    user_id: str
    email: str
    exp: datetime
