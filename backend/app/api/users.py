import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_permission, get_current_user
from app.core.security import hash_password
from app.models.user import User, TenantUser
from app.models.role import Role, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, TenantUserResponse
from app.schemas.role import AssignRoleRequest
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[TenantUserResponse])
async def list_users(
    ctx=Depends(require_permission("users.view")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    user, tenant = ctx
    offset = (page - 1) * page_size
    result = await db.execute(
        select(TenantUser)
        .where(TenantUser.tenant_id == tenant.id)
        .offset(offset).limit(page_size)
    )
    tenant_users = result.scalars().all()

    out = []
    for tu in tenant_users:
        u_result = await db.execute(select(User).where(User.id == tu.user_id))
        u = u_result.scalar_one_or_none()
        if u:
            # Get roles for this user in this tenant
            role_result = await db.execute(
                select(Role).join(UserRole, UserRole.role_id == Role.id).where(
                    UserRole.user_id == u.id,
                    UserRole.tenant_id == tenant.id,
                )
            )
            roles = [r.code for r in role_result.scalars().all()]
            ur = UserResponse.model_validate(u)
            ur.full_name = u.full_name
            out.append(TenantUserResponse(
                user=ur, status=tu.status,
                is_owner=tu.is_owner, joined_at=tu.joined_at,
                roles=roles
            ))
    return out


@router.post("/", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    ctx=Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    acting_user, tenant = ctx

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
    )
    db.add(user)
    await db.flush()

    # Add to tenant
    tu = TenantUser(tenant_id=tenant.id, user_id=user.id, status="active")
    db.add(tu)
    await db.flush()

    # Assign role if specified
    if body.role_code:
        role_result = await db.execute(
            select(Role).where(Role.code == body.role_code, Role.tenant_id == tenant.id)
        )
        role = role_result.scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id))

    await log_audit(
        db, "user.created",
        tenant_id=tenant.id, user_id=acting_user.id, user_email=acting_user.email,
        entity_type="user", entity_id=str(user.id),
        new_value={"email": user.email, "first_name": user.first_name},
        description=f"User {user.email} created"
    )
    await db.commit()
    await db.refresh(user)
    resp = UserResponse.model_validate(user)
    resp.full_name = user.full_name
    return resp


@router.get("/{user_public_id}", response_model=TenantUserResponse)
async def get_user(
    user_public_id: str,
    ctx=Depends(require_permission("users.view")),
    db: AsyncSession = Depends(get_db),
):
    acting_user, tenant = ctx

    user_result = await db.execute(
        select(User).where(User.public_id == user_public_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify this user belongs to the tenant
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == tenant.id,
        )
    )
    tu = tu_result.scalar_one_or_none()
    if not tu:
        raise HTTPException(status_code=404, detail="User not in this tenant")

    role_result = await db.execute(
        select(Role).join(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.tenant_id == tenant.id,
        )
    )
    roles = [r.code for r in role_result.scalars().all()]
    ur = UserResponse.model_validate(user)
    ur.full_name = user.full_name
    return TenantUserResponse(user=ur, status=tu.status, is_owner=tu.is_owner, roles=roles)


@router.put("/{user_public_id}", response_model=UserResponse)
async def update_user(
    user_public_id: str,
    body: UserUpdate,
    ctx=Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    acting_user, tenant = ctx
    user_result = await db.execute(select(User).where(User.public_id == user_public_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user is in tenant
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id
        )
    )
    if not tu_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not in this tenant")

    old = {"first_name": user.first_name, "last_name": user.last_name, "status": user.status}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await log_audit(
        db, "user.updated",
        tenant_id=tenant.id, user_id=acting_user.id, user_email=acting_user.email,
        entity_type="user", entity_id=str(user.id),
        old_value=old, new_value=body.model_dump(exclude_none=True),
    )
    await db.commit()
    await db.refresh(user)
    resp = UserResponse.model_validate(user)
    resp.full_name = user.full_name
    return resp


@router.post("/{user_public_id}/assign-role")
async def assign_role(
    user_public_id: str,
    body: AssignRoleRequest,
    ctx=Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    acting_user, tenant = ctx
    user_result = await db.execute(select(User).where(User.public_id == user_public_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_result = await db.execute(
        select(Role).where(Role.id == body.role_id, Role.tenant_id == tenant.id)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found in this tenant")

    # Upsert
    existing = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.tenant_id == tenant.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id))

    await log_audit(
        db, "user.role_assigned",
        tenant_id=tenant.id, user_id=acting_user.id, user_email=acting_user.email,
        entity_type="user", entity_id=str(user.id),
        description=f"Role '{role.code}' assigned to {user.email}"
    )
    await db.commit()
    return {"ok": True}
