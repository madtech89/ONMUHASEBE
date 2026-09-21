import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_context, require_permission, get_current_super_admin
from app.models.tenant import Tenant, TenantSettings, TenantModule, Module
from app.models.user import User, TenantUser
from app.schemas.tenant import (
    TenantCreate, TenantUpdate, TenantResponse,
    TenantSettingsSchema, TenantModuleResponse, ModuleResponse,
)
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/my", response_model=list[TenantResponse])
async def get_my_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all tenants the current user belongs to."""
    result = await db.execute(
        select(Tenant)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == current_user.id,
            TenantUser.status == "active",
            Tenant.status == "active",
        )
        .options(selectinload(Tenant.settings))
    )
    tenants = result.scalars().all()
    out = []
    for t in tenants:
        tr = TenantResponse.model_validate(t)
        if t.settings:
            tr.settings = TenantSettingsSchema.model_validate(t.settings)
        out.append(tr)
    return out


@router.get("/{tenant_public_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_public_id: str,
    ctx=Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    tr = TenantResponse.model_validate(tenant)
    if tenant.settings:
        tr.settings = TenantSettingsSchema.model_validate(tenant.settings)
    return tr


@router.put("/{tenant_public_id}/settings", response_model=TenantSettingsSchema)
async def update_tenant_settings(
    tenant_public_id: str,
    body: TenantSettingsSchema,
    ctx=Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    if tenant.settings:
        settings_obj = tenant.settings
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(settings_obj, field, value)
    else:
        settings_obj = TenantSettings(
            tenant_id=tenant.id,
            **body.model_dump(exclude_none=True),
        )
        db.add(settings_obj)

    await log_audit(
        db, "tenant.settings_updated",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="tenant", entity_id=str(tenant.id),
        description="Tenant settings updated"
    )
    await db.commit()
    await db.refresh(settings_obj)
    return TenantSettingsSchema.model_validate(settings_obj)


@router.get("/{tenant_public_id}/modules", response_model=list[TenantModuleResponse])
async def get_tenant_modules(
    tenant_public_id: str,
    ctx=Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(TenantModule).where(TenantModule.tenant_id == tenant.id)
    )
    tenant_modules = result.scalars().all()
    out = []
    for tm in tenant_modules:
        module_result = await db.execute(select(Module).where(Module.id == tm.module_id))
        module = module_result.scalar_one_or_none()
        if module:
            out.append(TenantModuleResponse(
                module=ModuleResponse.model_validate(module),
                is_enabled=tm.is_enabled,
                enabled_at=tm.enabled_at,
            ))
    return out
