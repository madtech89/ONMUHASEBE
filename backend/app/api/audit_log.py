import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    description: Optional[str] = None
    severity: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    ctx=Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_email: Optional[str] = None,
):
    user, tenant = ctx
    offset = (page - 1) * page_size

    query = select(AuditLog).where(AuditLog.tenant_id == tenant.id)
    if action_type:
        query = query.where(AuditLog.action_type.contains(action_type))
    if severity:
        query = query.where(AuditLog.severity == severity)
    if user_email:
        query = query.where(AuditLog.user_email.contains(user_email))

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size,
    )
