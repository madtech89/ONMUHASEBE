import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.core.security import hash_password
from app.models.tenant import Tenant, TenantSettings, TenantModule, Module
from app.models.user import User, TenantUser
from app.models.document import Document
from app.schemas.tenant import TenantCreate, TenantResponse, TenantStatsResponse
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


class TenantStatusUpdate(BaseModel):
    status: str  # active | suspended | disabled
    reason: Optional[str] = None


@router.get("/tenants", response_model=list[TenantResponse])
async def list_all_tenants(
    super_admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(page_size)
        .options(selectinload(Tenant.settings))
    )
    tenants = result.scalars().all()
    out = []
    for t in tenants:
        tr = TenantResponse.model_validate(t)
        out.append(tr)
    return out


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    body: TenantCreate,
    super_admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = Tenant(name=body.name, short_name=body.short_name)
    db.add(tenant)
    await db.flush()

    # Create default empty settings
    settings_obj = TenantSettings(tenant_id=tenant.id, ticari_unvan=body.name)
    db.add(settings_obj)

    # Enable core modules
    core_modules_result = await db.execute(
        select(Module).where(Module.is_core == True)  # noqa: E712
    )
    for module in core_modules_result.scalars().all():
        db.add(TenantModule(
            tenant_id=tenant.id, module_id=module.id,
            is_enabled=True, enabled_at=datetime.now(timezone.utc)
        ))

    await log_audit(
        db, "tenant.created",
        user_id=super_admin.id, user_email=super_admin.email,
        entity_type="tenant", entity_id=str(tenant.id),
        new_value={"name": body.name}, severity="info"
    )
    await db.commit()
    # Reload tenant with settings eagerly to avoid lazy-loading issue
    result2 = await db.execute(
        select(Tenant).where(Tenant.id == tenant.id).options(selectinload(Tenant.settings))
    )
    tenant = result2.scalar_one()
    return TenantResponse.model_validate(tenant)


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: int,
    body: TenantStatusUpdate,
    super_admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_status = tenant.status
    tenant.status = body.status

    await log_audit(
        db, "tenant.status_changed",
        user_id=super_admin.id, user_email=super_admin.email,
        entity_type="tenant", entity_id=str(tenant.id),
        old_value={"status": old_status},
        new_value={"status": body.status, "reason": body.reason},
        severity="critical"
    )
    await db.commit()
    return {"ok": True, "tenant_id": tenant_id, "status": body.status}


@router.get("/tenants/{tenant_id}/stats", response_model=TenantStatsResponse)
async def tenant_stats(
    tenant_id: int,
    super_admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count_result = await db.execute(
        select(func.count(TenantUser.id)).where(
            TenantUser.tenant_id == tenant_id, TenantUser.status == "active"
        )
    )
    user_count = user_count_result.scalar_one()

    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.tenant_id == tenant_id, Document.status == "active"
        )
    )
    doc_count = doc_count_result.scalar_one()

    mod_count_result = await db.execute(
        select(func.count(TenantModule.id)).where(
            TenantModule.tenant_id == tenant_id, TenantModule.is_enabled == True  # noqa: E712
        )
    )
    mod_count = mod_count_result.scalar_one()

    return TenantStatsResponse(
        tenant_id=tenant_id, tenant_name=tenant.name,
        user_count=user_count, document_count=doc_count,
        active_modules=mod_count, status=tenant.status
    )


@router.get("/system/health")
async def system_health(
    super_admin: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    tenant_count_result = await db.execute(select(func.count(Tenant.id)))
    user_count_result = await db.execute(select(func.count(User.id)))

    return {
        "status": "ok",
        "database": db_status,
        "tenants": tenant_count_result.scalar_one(),
        "users": user_count_result.scalar_one(),
    }
