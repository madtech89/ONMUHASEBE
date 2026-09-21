"""
Phase 2 — Customer Master & Customer Locations
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, PublicIDMixin

if TYPE_CHECKING:
    from app.models.meal import MealPriceVersion, MealEntryEvent
    from app.models.ledger import LedgerAccount


LOCATION_TYPES = ("santiye", "ofis", "isyeri", "fabrika", "depo", "sube", "diger")
CUSTOMER_TYPES = ("company", "individual", "other")


class Customer(Base, TimestampMixin, PublicIDMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_name: Mapped[str] = mapped_column(String(300), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(150))

    customer_type: Mapped[str] = mapped_column(String(20), default="company")  # company/individual/other

    tax_office: Mapped[Optional[str]] = mapped_column(String(200))
    tax_number: Mapped[Optional[str]] = mapped_column(String(50))

    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    address: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Customer-level default VAT override (uses tenant default if NULL)
    default_vat_rate: Mapped[Optional[str]] = mapped_column(String(10))

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active/inactive
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    locations: Mapped[List["CustomerLocation"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerLocation.name",
    )

    __table_args__ = (
        # MySQL allows multiple NULL codes in a unique index (NULL != NULL per MySQL)
        UniqueConstraint("tenant_id", "code", name="uq_customer_code_tenant"),
        Index("ix_customers_tenant_status", "tenant_id", "status"),
        Index("ix_customers_tenant_name", "tenant_id", "legal_name"),
    )

    @property
    def short_name(self) -> str:
        return self.display_name or self.legal_name


class CustomerLocation(Base, TimestampMixin, PublicIDMixin):
    __tablename__ = "customer_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    location_type: Mapped[str] = mapped_column(String(30), default="diger")

    address: Mapped[Optional[str]] = mapped_column(Text)
    contact_person: Mapped[Optional[str]] = mapped_column(String(200))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # Relationship back to customer
    customer: Mapped["Customer"] = relationship(back_populates="locations")

    __table_args__ = (
        Index("ix_customer_locations_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_customer_locations_tenant_status", "tenant_id", "status"),
    )
