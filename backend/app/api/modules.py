import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_permission
from app.models.tenant import Module, TenantModule
from app.schemas.tenant import ModuleResponse, TenantModuleResponse
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[TenantModuleResponse])
async def list_modules(
    ctx=Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    modules_result = await db.execute(select(Module).order_by(Module.sort_order))
    all_modules = {m.id: m for m in modules_result.scalars().all()}

    tm_result = await db.execute(
        select(TenantModule).where(TenantModule.tenant_id == tenant.id)
    )
    tenant_modules = {tm.module_id: tm for tm in tm_result.scalars().all()}

    out = []
    for mod_id, module in all_modules.items():
        tm = tenant_modules.get(mod_id)
        out.append(TenantModuleResponse(
            module=ModuleResponse.model_validate(module),
            is_enabled=tm.is_enabled if tm else False,
            enabled_at=tm.enabled_at if tm else None,
        ))
    return out


@router.put("/{module_code}/toggle")
async def toggle_module(
    module_code: str,
    ctx=Depends(require_permission("modules.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx

    module_result = await db.execute(select(Module).where(Module.code == module_code))
    module = module_result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if module.is_core:
        raise HTTPException(status_code=400, detail="Core modules cannot be toggled")

    tm_result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant.id,
            TenantModule.module_id == module.id,
        )
    )
    tm = tm_result.scalar_one_or_none()

    if tm:
        tm.is_enabled = not tm.is_enabled
        if tm.is_enabled:
            tm.enabled_at = datetime.now(timezone.utc)
            tm.disabled_at = None
        else:
            tm.disabled_at = datetime.now(timezone.utc)
        new_state = tm.is_enabled
    else:
        tm = TenantModule(
            tenant_id=tenant.id,
            module_id=module.id,
            is_enabled=True,
            enabled_at=datetime.now(timezone.utc),
        )
        db.add(tm)
        new_state = True

    await log_audit(
        db, "module.toggled",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="module", entity_id=module_code,
        description=f"Module '{module_code}' {'enabled' if new_state else 'disabled'}"
    )
    await db.commit()
    return {"ok": True, "module": module_code, "enabled": new_state}
