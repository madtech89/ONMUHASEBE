import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    token = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials
    return token


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Malformed token")

    result = await db.execute(
        select(User).where(User.id == user_id, User.status == "active")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_current_super_admin(
    current_user=Depends(get_current_user),
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


async def get_tenant_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None),
):
    """Enforces tenant isolation. Returns (user, tenant)."""
    from app.models.tenant import Tenant
    from app.models.user import TenantUser

    tenant_id_str = x_tenant_id

    # Try token payload as fallback
    if not tenant_id_str:
        token = request.cookies.get("access_token")
        if token:
            try:
                payload = decode_token(token)
                tid = payload.get("tenant_id")
                if tid:
                    tenant_id_str = str(tid)
            except Exception:
                pass

    if not tenant_id_str:
        raise HTTPException(
            status_code=400,
            detail="Tenant context required. Send X-Tenant-ID header.",
        )

    # Resolve tenant (by public_id UUID or numeric id)
    from sqlalchemy.orm import selectinload
    from app.models.tenant import TenantSettings as _TenantSettings  # noqa
    try:
        if "-" in tenant_id_str:  # UUID format
            result = await db.execute(
                select(Tenant).where(
                    Tenant.public_id == tenant_id_str,
                    Tenant.status == "active",
                ).options(selectinload(Tenant.settings))
            )
        else:
            result = await db.execute(
                select(Tenant).where(
                    Tenant.id == int(tenant_id_str),
                    Tenant.status == "active",
                ).options(selectinload(Tenant.settings))
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found or inactive")

    # Super admin bypasses membership check
    if current_user.is_super_admin:
        return current_user, tenant

    # CRITICAL: Verify user membership in this tenant
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == current_user.id,
            TenantUser.tenant_id == tenant.id,
            TenantUser.status == "active",
        )
    )
    if not tu_result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="Access denied: you are not a member of this tenant",
        )

    return current_user, tenant


def require_permission(permission_code: str):
    """Dependency factory: checks that the user has a specific permission in their tenant."""

    async def _check(
        db: AsyncSession = Depends(get_db),
        ctx=Depends(get_tenant_context),
    ):
        from app.models.role import Permission, RolePermission, Role, UserRole

        user, tenant = ctx

        if user.is_super_admin:
            return user, tenant

        result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant.id,
                Permission.code == permission_code,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission_code}",
            )

        return user, tenant

    return _check
