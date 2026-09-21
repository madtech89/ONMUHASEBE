import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, hash_token,
    create_access_token, create_refresh_token, create_mfa_pending_token,
)
from app.models.user import User, TenantUser
from app.models.auth import UserSession, MFAConfig, RecoveryCode, LoginAttempt
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

BRUTE_FORCE_WINDOW_MINUTES = 15
BRUTE_FORCE_MAX_ATTEMPTS = 5


async def check_brute_force(db: AsyncSession, identifier: str) -> bool:
    """Returns True if locked out."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=BRUTE_FORCE_WINDOW_MINUTES)
    result = await db.execute(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.identifier == identifier,
            LoginAttempt.success == False,  # noqa: E712
            LoginAttempt.attempted_at >= cutoff,
        )
    )
    count = result.scalar_one()
    return count >= BRUTE_FORCE_MAX_ATTEMPTS


async def record_login_attempt(
    db: AsyncSession, identifier: str, ip: Optional[str], email: Optional[str], success: bool
) -> None:
    attempt = LoginAttempt(
        identifier=identifier,
        ip_address=ip,
        email=email,
        success=success,
    )
    db.add(attempt)
    await db.flush()


async def create_user_session(
    db: AsyncSession,
    user: User,
    tenant_id: Optional[int],
    ip: Optional[str],
    user_agent: Optional[str],
) -> Tuple[str, str, str]:
    """Creates a new session. Returns (access_token, refresh_token, session_public_id)."""
    session_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(user.id, session_id)
    refresh_hash = hash_token(refresh_token)

    session = UserSession(
        public_id=session_id,
        user_id=user.id,
        tenant_id=tenant_id,
        refresh_token_hash=refresh_hash,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)

    # Get tenant's first match for user if tenant_id not provided
    effective_tenant_id = tenant_id
    if not effective_tenant_id:
        tu_result = await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id,
                TenantUser.status == "active",
            ).limit(1)
        )
        tu = tu_result.scalar_one_or_none()
        if tu:
            effective_tenant_id = tu.tenant_id

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        is_super_admin=user.is_super_admin,
        tenant_id=effective_tenant_id,
    )
    await db.flush()
    return access_token, refresh_token, session_id


async def revoke_session_by_refresh_hash(db: AsyncSession, token_hash: str) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.refresh_token_hash == token_hash)
        .values(is_revoked=True)
    )


async def revoke_all_user_sessions(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.is_revoked == False)  # noqa: E712
        .values(is_revoked=True)
    )


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_primary_tenant(db: AsyncSession, user_id: int) -> Optional[Tenant]:
    result = await db.execute(
        select(Tenant)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.status == "active",
            Tenant.status == "active",
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
