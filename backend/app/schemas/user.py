from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role_code: Optional[str] = None  # role to assign in tenant

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    public_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str = ""
    phone: Optional[str] = None
    timezone: str = "Europe/Istanbul"
    locale: str = "tr"
    status: str
    is_super_admin: bool = False
    mfa_enabled: bool = False
    force_password_change: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUserResponse(BaseModel):
    user: UserResponse
    status: str
    is_owner: bool = False
    joined_at: Optional[datetime] = None
    roles: List[str] = []  # role codes

    model_config = {"from_attributes": True}
