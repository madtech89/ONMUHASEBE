import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, PublicIDMixin

if TYPE_CHECKING:
    from app.models.user import TenantUser


class Tenant(Base, TimestampMixin, PublicIDMixin):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    settings: Mapped[Optional["TenantSettings"]] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    tenant_users: Mapped[List["TenantUser"]] = relationship(back_populates="tenant")
    tenant_modules: Mapped[List["TenantModule"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tenants_status_created", "status", "created_at"),
    )


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), unique=True, nullable=False
    )

    ticari_unvan: Mapped[Optional[str]] = mapped_column(String(300))
    kisa_ad: Mapped[Optional[str]] = mapped_column(String(100))
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    favicon_url: Mapped[Optional[str]] = mapped_column(String(500))

    vergi_dairesi: Mapped[Optional[str]] = mapped_column(String(200))
    vergi_no: Mapped[Optional[str]] = mapped_column(String(50))

    adres: Mapped[Optional[str]] = mapped_column(Text)
    telefon: Mapped[Optional[str]] = mapped_column(String(50))
    eposta: Mapped[Optional[str]] = mapped_column(String(200))
    website: Mapped[Optional[str]] = mapped_column(String(300))

    para_birimi: Mapped[str] = mapped_column(String(10), default="TRY")
    kdv_orani: Mapped[Optional[str]] = mapped_column(String(10), default="20")
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Istanbul")

    iban: Mapped[Optional[str]] = mapped_column(String(100))
    banka_bilgileri: Mapped[Optional[str]] = mapped_column(Text)

    pdf_header: Mapped[Optional[str]] = mapped_column(Text)
    pdf_footer: Mapped[Optional[str]] = mapped_column(Text)

    belge_numaralama: Mapped[Optional[dict]] = mapped_column(JSON)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="settings")


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_tr: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tenant_modules: Mapped[List["TenantModule"]] = relationship(back_populates="module")


class TenantModule(Base):
    __tablename__ = "tenant_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(Integer, ForeignKey("modules.id"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    tenant: Mapped["Tenant"] = relationship(back_populates="tenant_modules")
    module: Mapped["Module"] = relationship(back_populates="tenant_modules")

    __table_args__ = (
        Index("ix_tenant_modules_unique", "tenant_id", "module_id", unique=True),
        Index("ix_tenant_modules_tenant", "tenant_id"),
    )
