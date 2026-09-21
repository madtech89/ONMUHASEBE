import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_permission
from app.models.role import Role, Permission, RolePermission, UserRole
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, PermissionResponse,
    AssignPermissionsRequest,
)
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_all_permissions(
    ctx=Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    return [PermissionResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    ctx=Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Role).where(
            (Role.tenant_id == tenant.id) | (Role.tenant_id == None)  # noqa: E711
        ).order_by(Role.name)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    roles = result.scalars().all()
    out = []
    for role in roles:
        rr = RoleResponse.model_validate(role)
        rr.permissions = [PermissionResponse.model_validate(rp.permission) for rp in role.role_permissions]
        out.append(rr)
    return out


@router.post("/", response_model=RoleResponse)
async def create_role(
    body: RoleCreate,
    ctx=Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    existing = await db.execute(
        select(Role).where(Role.code == body.code, Role.tenant_id == tenant.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Role code already exists")

    role = Role(tenant_id=tenant.id, code=body.code, name=body.name, description=body.description)
    db.add(role)
    await log_audit(
        db, "role.created",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="role", description=f"Role '{body.code}' created"
    )
    await db.commit()
    await db.refresh(role)
    rr = RoleResponse.model_validate(role)
    rr.permissions = []
    return rr


@router.put("/{role_id}/permissions")
async def set_role_permissions(
    role_id: int,
    body: AssignPermissionsRequest,
    ctx=Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    role_result = await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == tenant.id)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    old_perms = [rp.permission.code for rp in role.role_permissions]

    # Delete existing
    for rp in role.role_permissions:
        await db.delete(rp)
    await db.flush()

    # Add new
    for perm_code in body.permission_codes:
        perm_result = await db.execute(
            select(Permission).where(Permission.code == perm_code)
        )
        perm = perm_result.scalar_one_or_none()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await log_audit(
        db, "role.permissions_changed",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="role", entity_id=str(role.id),
        old_value={"permissions": old_perms},
        new_value={"permissions": body.permission_codes},
        severity="warning"
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    ctx=Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    role_result = await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == tenant.id, Role.is_system_role == False)  # noqa: E712
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found or is a system role")

    await db.delete(role)
    await log_audit(
        db, "role.deleted",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="role", entity_id=str(role_id),
        severity="warning"
    )
    await db.commit()
    return {"ok": True}
