import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
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
    # Re-fetch with settings eagerly loaded to avoid async lazy-load error
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant.id)
        .options(selectinload(Tenant.settings))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
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

    # Fetch settings separately to avoid lazy-loading in async context
    settings_result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    settings_obj = settings_result.scalar_one_or_none()

    if settings_obj:
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


ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/{tenant_public_id}/logo")
async def upload_tenant_logo(
    tenant_public_id: str,
    file: UploadFile = File(...),
    ctx=Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Upload tenant logo. Stored locally, served via GET /logo endpoint."""
    user, tenant = ctx
    # Verify tenant ownership
    if tenant.public_id != tenant_public_id:
        raise HTTPException(status_code=403, detail="Erişim reddedildi")

    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=400, detail="Desteklenmeyen dosya tipi. JPG, PNG, GIF, WebP veya SVG yükleyin.")

    content = await file.read()
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="Logo boyutu 5 MB'ı geçemez")

    from app.services.storage_service import storage
    # Store with deterministic key so uploading a new one overwrites the old
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png"
    storage_key = f"logos/{tenant.id}/logo.{ext}"
    await storage.store(content, storage_key)

    # Update logo_url in settings
    settings_result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    settings_obj = settings_result.scalar_one_or_none()
    if not settings_obj:
        settings_obj = TenantSettings(tenant_id=tenant.id)
        db.add(settings_obj)

    logo_url = f"/api/tenants/{tenant_public_id}/logo"
    settings_obj.logo_url = logo_url
    await db.commit()

    return {"logo_url": logo_url, "message": "Logo yüklendi"}


@router.get("/{tenant_public_id}/logo")
async def get_tenant_logo(
    tenant_public_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve tenant logo (publicly accessible for display)."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.public_id == tenant_public_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant bulunamadı")

    from app.services.storage_service import storage
    import os
    # Try common extensions
    for ext in ["png", "jpg", "jpeg", "gif", "webp", "svg"]:
        storage_key = f"logos/{tenant.id}/logo.{ext}"
        try:
            content = await storage.retrieve(storage_key)
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext.replace('jpg', 'jpeg')}"
            return Response(content=content, media_type=mime)
        except FileNotFoundError:
            continue
    raise HTTPException(status_code=404, detail="Logo bulunamadı")


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
