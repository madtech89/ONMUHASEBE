"""
Phase 2 — Generic Ledger: Accounts & Entries
Extensible for customer/supplier/employee/bank ledgers.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, DateTime, Date,
    ForeignKey, Index, Numeric, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, PublicIDMixin


class LedgerAccount(Base, PublicIDMixin):
    """
    One ledger account per entity (customer, supplier, employee, etc.).
    Auto-created when first transaction is posted.
    """
    __tablename__ = "ledger_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    account_type: Mapped[str] = mapped_column(String(20), default="customer")
    # customer / supplier / employee / bank

    # Polymorphic entity reference
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))  # 'customer'
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(10), default="TRY")
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    entries: Mapped[List["LedgerEntry"]] = relationship(
        back_populates="account",
        order_by="LedgerEntry.business_date",
    )

    __table_args__ = (
        # Each entity has exactly one account per tenant
        UniqueConstraint("tenant_id", "entity_type", "entity_id", name="uq_ledger_account_entity"),
        Index("ix_ledger_accounts_tenant", "tenant_id"),
        Index("ix_ledger_accounts_type", "tenant_id", "account_type"),
    )


class LedgerEntry(Base, PublicIDMixin):
    """
    Double-entry-compatible ledger line.
    Phase 2: DEBIT entries from meal events.
    Phase 3+: CREDIT entries from payments.
    Idempotent: same source cannot post twice.
    """
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ledger_accounts.id"), nullable=False, index=True
    )

    entry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    description: Mapped[Optional[str]] = mapped_column(String(500))

    # One of debit or credit will be non-zero
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, default=Decimal("0"))
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, default=Decimal("0"))

    # Source reference for idempotency and traceability
    source_type: Mapped[Optional[str]] = mapped_column(String(30))  # meal_event / payment / manual
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Composite idempotency: tenant + source_type + source_idempotency_key
    source_idempotency_key: Mapped[Optional[str]] = mapped_column(String(200))

    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / void

    account: Mapped["LedgerAccount"] = relationship(back_populates="entries")

    __table_args__ = (
        # Prevent duplicate ledger posting for same event
        UniqueConstraint(
            "tenant_id", "source_type", "source_idempotency_key",
            name="uq_ledger_entry_idempotency",
        ),
        Index("ix_ledger_entries_account_date", "account_id", "business_date"),
        Index("ix_ledger_entries_tenant_date", "tenant_id", "business_date"),
        Index("ix_ledger_entries_source", "source_type", "source_id"),
    )
