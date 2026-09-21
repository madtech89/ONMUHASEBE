"""
Phase 2 — Meal Types, Versioned Pricing, Meal Entry Events
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Index, Numeric, UniqueConstraint, or_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, PublicIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer, CustomerLocation


class MealType(Base):
    """
    Extensible meal type. tenant_id=NULL → system default (all tenants).
    tenant_id SET → tenant-specific custom meal type.
    """
    __tablename__ = "meal_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # NULL = system-wide, non-NULL = tenant custom
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        # (code, NULL) unique globally, (code, tenant_id) unique per tenant
        Index("ix_meal_types_code_tenant", "code", "tenant_id", unique=True),
        Index("ix_meal_types_sort", "sort_order"),
    )


class MealPriceVersion(Base, PublicIDMixin):
    """
    Date-versioned pricing. Never update historical records.
    Resolution: location-specific first, then customer default (location_id IS NULL).
    """
    __tablename__ = "meal_price_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customer_locations.id"), nullable=True, index=True
    )
    meal_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meal_types.id"), nullable=False
    )

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # False = KDV Hariç (net fiyat, KDV üstüne eklenir)
    # True  = KDV Dahil (brüt fiyat, KDV içinden çıkarılır)
    price_includes_vat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])
    location: Mapped[Optional["CustomerLocation"]] = relationship(foreign_keys=[location_id])
    meal_type: Mapped["MealType"] = relationship()

    __table_args__ = (
        # Performance index for price resolution queries
        Index(
            "ix_prices_lookup",
            "tenant_id", "customer_id", "location_id", "meal_type_id", "effective_from",
        ),
        Index("ix_prices_tenant_customer", "tenant_id", "customer_id", "effective_from"),
        Index("ix_prices_active", "tenant_id", "is_active"),
    )


class MealEntryEvent(Base, PublicIDMixin):
    """
    Immutable append-only meal quantity event.
    Corrections are new events with correction_type='correction' and negative quantity.
    Financial snapshot values are frozen at creation time.
    """
    __tablename__ = "meal_entry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customer_locations.id"), nullable=True, index=True
    )

    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("meal_types.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    # ── Immutable financial snapshot ────────────────────────────────────────
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    vat_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    price_includes_vat_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    price_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("meal_price_versions.id"), nullable=True
    )
    # ── Idempotency ─────────────────────────────────────────────────────────
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Correction chain ────────────────────────────────────────────────────
    correction_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # NULL = original entry, 'correction' = corrective entry (negative qty)
    corrects_event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("meal_entry_events.id"), nullable=True
    )
    correction_reason: Mapped[Optional[str]] = mapped_column(Text)

    # ── Audit ────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/void

    # Relationships
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])
    location: Mapped[Optional["CustomerLocation"]] = relationship(foreign_keys=[location_id])
    meal_type: Mapped["MealType"] = relationship()
    price_version: Mapped[Optional["MealPriceVersion"]] = relationship()
    corrects_event: Mapped[Optional["MealEntryEvent"]] = relationship(
        foreign_keys=[corrects_event_id], remote_side="MealEntryEvent.id"
    )
    created_by_user: Mapped[None] = relationship(
        "User", foreign_keys=[created_by], viewonly=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_meal_event_idempotency"),
        Index("ix_events_daily_agg", "tenant_id", "business_date", "customer_id", "location_id", "status"),
        Index("ix_events_customer_date", "tenant_id", "customer_id", "business_date"),
        Index("ix_events_date_range", "tenant_id", "business_date", "status"),
    )
