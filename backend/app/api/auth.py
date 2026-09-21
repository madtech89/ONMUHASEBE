import logging
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    verify_password, hash_password, decode_token, hash_token,
    generate_totp_secret, encrypt_totp_secret, decrypt_totp_secret,
    get_totp_qr_base64, verify_totp, generate_recovery_codes,
    verify_recovery_code, create_access_token, limiter,
)
from app.models.auth import UserSession, MFAConfig, RecoveryCode
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse, MFAVerifyRequest,
    MFASetupInitResponse, MFAEnableRequest, PasswordChangeRequest,
    UserMeResponse, SessionResponse,
)
from app.services.audit_service import log_audit
from app.services.auth_service import (
    check_brute_force, record_login_attempt,
    create_user_session, revoke_session_by_refresh_hash,
    revoke_all_user_sessions, get_user_by_email,
    get_user_primary_tenant,
)

logger = logging.getLogger(__name__)
router = APIRouter()

COOKIE_KWARGS = {
    "httponly": True,
    "secure": settings.COOKIE_SECURE,
    "samesite": "lax",
    "path": "/",
}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token", value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **COOKIE_KWARGS
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, **COOKIE_KWARGS
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host or "unknown")


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]
    identifier = f"{ip}:{body.email.lower()}"

    if await check_brute_force(db, identifier):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please wait 15 minutes.",
        )

    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        await record_login_attempt(db, identifier, ip, body.email.lower(), success=False)
        await log_audit(
            db, "user.login_failed",
            user_email=body.email.lower(),
            ip_address=ip, user_agent=user_agent,
            description="Invalid credentials", severity="warning"
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.status != "active":
        raise HTTPException(status_code=403, detail=f"Account is {user.status}")

    await record_login_attempt(db, identifier, ip, body.email.lower(), success=True)

    # MFA flow
    if user.mfa_enabled:
        from app.core.security import create_mfa_pending_token
        temp_token = create_mfa_pending_token(user.id)
        await log_audit(
            db, "user.login_mfa_required",
            user_id=user.id, user_email=user.email,
            ip_address=ip, severity="info"
        )
        await db.commit()
        return LoginResponse(requires_mfa=True, temp_token=temp_token)

    # Full login
    access_token, refresh_token, session_id = await create_user_session(
        db, user, tenant_id=None, ip=ip, user_agent=user_agent
    )
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await log_audit(
        db, "user.login",
        user_id=user.id, user_email=user.email,
        ip_address=ip, user_agent=user_agent,
        session_id=session_id, severity="info"
    )
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    user_data = UserMeResponse.model_validate(user)
    user_data.full_name = user.full_name
    return LoginResponse(user=user_data)


@router.post("/mfa/verify", response_model=LoginResponse)
@limiter.limit("10/minute")
async def verify_mfa(
    request: Request,
    body: MFAVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]

    try:
        payload = decode_token(body.temp_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="MFA session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid MFA token")

    if payload.get("type") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User not found")

    # Try TOTP first
    mfa_result = await db.execute(
        select(MFAConfig).where(MFAConfig.user_id == user_id, MFAConfig.is_verified == True)  # noqa: E712
    )
    mfa_config = mfa_result.scalar_one_or_none()

    code_valid = False
    if mfa_config:
        secret = decrypt_totp_secret(mfa_config.totp_secret_encrypted)
        code_valid = verify_totp(secret, body.code)

    # Try recovery code if TOTP failed
    if not code_valid and len(body.code) > 6:
        rc_result = await db.execute(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.is_used == False,  # noqa: E712
            )
        )
        for rc in rc_result.scalars().all():
            if verify_recovery_code(body.code, rc.code_hash):
                rc.is_used = True
                rc.used_at = datetime.now(timezone.utc)
                code_valid = True
                await log_audit(
                    db, "mfa.recovery_code_used",
                    user_id=user.id, user_email=user.email,
                    ip_address=ip, severity="warning",
                    description="MFA recovery code used"
                )
                break

    if not code_valid:
        await log_audit(
            db, "user.mfa_failed",
            user_id=user.id, user_email=user.email,
            ip_address=ip, severity="warning"
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    access_token, refresh_token, session_id = await create_user_session(
        db, user, tenant_id=None, ip=ip, user_agent=user_agent
    )
    user.last_login_at = datetime.now(timezone.utc)
    await log_audit(
        db, "user.login",
        user_id=user.id, user_email=user.email,
        ip_address=ip, session_id=session_id, severity="info"
    )
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    user_data = UserMeResponse.model_validate(user)
    user_data.full_name = user.full_name
    return LoginResponse(user=user_data)


@router.get("/me", response_model=UserMeResponse)
async def me(current_user: User = Depends(get_current_user)):
    data = UserMeResponse.model_validate(current_user)
    data.full_name = current_user.full_name
    return data


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    session_id = payload.get("sid")
    token_hash = hash_token(token)

    result = await db.execute(
        select(UserSession).where(
            UserSession.public_id == session_id,
            UserSession.is_revoked == False,  # noqa: E712
        )
    )
    session = result.scalar_one_or_none()
    if not session or session.refresh_token_hash != token_hash:
        # Possible token reuse — revoke session
        if session:
            session.is_revoked = True
            await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    # Rotate: issue new tokens
    user_result = await db.execute(
        select(User).where(User.id == session.user_id, User.status == "active")
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    from app.core.security import create_refresh_token
    new_refresh = create_refresh_token(user.id, session_id)
    new_hash = hash_token(new_refresh)

    session.refresh_token_hash = new_hash
    session.last_used_at = datetime.now(timezone.utc)

    new_access = create_access_token(
        user_id=user.id,
        email=user.email,
        is_super_admin=user.is_super_admin,
        tenant_id=session.tenant_id,
    )
    await db.commit()

    _set_auth_cookies(response, new_access, new_refresh)
    return {"ok": True}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_token(token)
            session_id = payload.get("sid")
            token_hash = hash_token(token)
            await revoke_session_by_refresh_hash(db, token_hash)
            await db.commit()
        except Exception:
            pass
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip = _get_client_ip(request)
    await revoke_all_user_sessions(db, current_user.id)
    await log_audit(
        db, "user.logout_all",
        user_id=current_user.id, user_email=current_user.email,
        ip_address=ip, severity="warning",
        description="User logged out from all devices"
    )
    await db.commit()
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/change-password")
async def change_password(
    request: Request,
    body: PasswordChangeRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip = _get_client_ip(request)
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = hash_password(body.new_password)
    current_user.force_password_change = False

    await revoke_all_user_sessions(db, current_user.id)
    await log_audit(
        db, "user.password_changed",
        user_id=current_user.id, user_email=current_user.email,
        ip_address=ip, severity="warning",
        description="Password changed, all sessions revoked"
    )
    await db.commit()
    _clear_auth_cookies(response)
    return {"ok": True, "message": "Password changed. Please log in again."}


# ─── MFA Setup ────────────────────────────────────────────────────────────────

@router.post("/mfa/setup", response_model=MFASetupInitResponse)
async def mfa_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate MFA setup: generate secret + QR + recovery codes."""
    ip = _get_client_ip(request)
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)

    # Upsert MFA config (not yet verified)
    existing = await db.execute(
        select(MFAConfig).where(MFAConfig.user_id == current_user.id)
    )
    mfa = existing.scalar_one_or_none()
    if mfa:
        mfa.totp_secret_encrypted = encrypted
        mfa.is_verified = False
        mfa.verified_at = None
    else:
        mfa = MFAConfig(
            user_id=current_user.id,
            totp_secret_encrypted=encrypted,
            is_verified=False,
        )
        db.add(mfa)

    # Generate and store recovery codes
    await db.execute(
        select(RecoveryCode).where(RecoveryCode.user_id == current_user.id)
    )
    # Delete old codes
    old_codes_result = await db.execute(
        select(RecoveryCode).where(RecoveryCode.user_id == current_user.id)
    )
    for old in old_codes_result.scalars().all():
        await db.delete(old)

    plaintext_codes, hashed_codes = generate_recovery_codes(8)
    for hc in hashed_codes:
        db.add(RecoveryCode(user_id=current_user.id, code_hash=hc))

    await log_audit(
        db, "mfa.setup_initiated",
        user_id=current_user.id, user_email=current_user.email,
        ip_address=ip, severity="info"
    )
    await db.commit()

    qr = get_totp_qr_base64(secret, current_user.email)
    return MFASetupInitResponse(secret=secret, qr_image=qr, recovery_codes=plaintext_codes)


@router.post("/mfa/enable")
async def mfa_enable(
    request: Request,
    body: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm and enable MFA after verifying TOTP code."""
    ip = _get_client_ip(request)
    result = await db.execute(
        select(MFAConfig).where(MFAConfig.user_id == current_user.id)
    )
    mfa = result.scalar_one_or_none()
    if not mfa:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")

    secret = decrypt_totp_secret(mfa.totp_secret_encrypted)
    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    mfa.is_verified = True
    mfa.verified_at = datetime.now(timezone.utc)
    current_user.mfa_enabled = True

    await log_audit(
        db, "mfa.enabled",
        user_id=current_user.id, user_email=current_user.email,
        ip_address=ip, severity="warning",
        description="MFA successfully enabled"
    )
    await db.commit()
    return {"ok": True, "message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def mfa_disable(
    request: Request,
    body: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip = _get_client_ip(request)
    result = await db.execute(
        select(MFAConfig).where(MFAConfig.user_id == current_user.id, MFAConfig.is_verified == True)  # noqa: E712
    )
    mfa = result.scalar_one_or_none()
    if not mfa:
        raise HTTPException(status_code=400, detail="MFA not enabled")

    secret = decrypt_totp_secret(mfa.totp_secret_encrypted)
    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    mfa.is_verified = False
    current_user.mfa_enabled = False

    await log_audit(
        db, "mfa.disabled",
        user_id=current_user.id, user_email=current_user.email,
        ip_address=ip, severity="critical",
        description="MFA disabled by user"
    )
    await db.commit()
    return {"ok": True}


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_token = request.cookies.get("refresh_token")
    current_hash = hash_token(current_token) if current_token else None

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_revoked == False,  # noqa: E712
        ).order_by(UserSession.last_used_at.desc())
    )
    sessions = result.scalars().all()

    out = []
    for s in sessions:
        sr = SessionResponse.model_validate(s)
        sr.is_current = (current_hash is not None and s.refresh_token_hash == current_hash)
        out.append(sr)
    return out
