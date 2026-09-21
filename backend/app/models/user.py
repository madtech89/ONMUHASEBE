from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, PublicIDMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.auth import MFAConfig, RecoveryCode, UserSession
    from app.models.role import UserRole


class User(Base, TimestampMixin, PublicIDMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)

    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Istanbul")
    locale: Mapped[str] = mapped_column(String(10), default="tr")

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # active | invited | suspended | disabled

    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    force_password_change: Mapped[bool] = mapped_column(Boolean, default=False)

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    tenant_users: Mapped[List["TenantUser"]] = relationship(back_populates="user")
    mfa_config: Mapped[Optional["MFAConfig"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    recovery_codes: Mapped[List["RecoveryCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_roles: Mapped[List["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email

    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_is_super_admin", "is_super_admin"),
    )


class TenantUser(Base):
    __tablename__ = "tenant_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active")
    # active | invited | suspended
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)

    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="tenant_users")
    user: Mapped["User"] = relationship(back_populates="tenant_users")

    __table_args__ = (
        Index("ix_tenant_users_unique", "tenant_id", "user_id", unique=True),
        Index("ix_tenant_users_tenant", "tenant_id"),
        Index("ix_tenant_users_user", "user_id"),
    )
