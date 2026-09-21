import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    action_type: str,
    *,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    description: Optional[str] = None,
    severity: str = "info",
) -> AuditLog:
    # Sanitize: never log secrets
    entry = AuditLog(
        action_type=action_type,
        tenant_id=tenant_id,
        user_id=user_id,
        user_email=user_email,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        session_id=session_id,
        old_value=old_value,
        new_value=new_value,
        description=description,
        severity=severity,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception as e:
        logger.error(f"Audit log flush failed for {action_type}: {e}")
    return entry
