import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    """Central immutable audit trail. Regular users cannot delete entries."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        default=lambda: str(uuid.uuid4()), index=True
    )

    # Context
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Action
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Examples: user.created | user.login | user.login_failed | mfa.enabled
    #           tenant.created | role.permission_changed | document.uploaded
    #           payment.created | payment.cancelled

    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Request info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Change diff
    old_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(Text)

    severity: Mapped[str] = mapped_column(String(20), default="info")
    # info | warning | critical

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_tenant_time", "tenant_id", "created_at"),
        Index("ix_audit_action_time", "action_type", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_user", "user_id", "created_at"),
    )
