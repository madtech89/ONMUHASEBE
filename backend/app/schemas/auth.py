from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserMeResponse(BaseModel):
    id: int
    public_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str = ""
    is_super_admin: bool = False
    mfa_enabled: bool = False
    status: str
    force_password_change: bool = False
    last_login_at: Optional[datetime] = None
    locale: str = "tr"

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    requires_mfa: bool = False
    temp_token: Optional[str] = None
    user: Optional[UserMeResponse] = None
    message: str = "ok"


class MFAVerifyRequest(BaseModel):
    temp_token: str
    code: str  # 6-digit TOTP or recovery code


class MFASetupInitResponse(BaseModel):
    secret: str
    qr_image: str  # base64 PNG data URL
    recovery_codes: list[str]


class MFAEnableRequest(BaseModel):
    code: str  # Verify before enabling


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SessionResponse(BaseModel):
    public_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


class RefreshResponse(BaseModel):
    ok: bool = True
