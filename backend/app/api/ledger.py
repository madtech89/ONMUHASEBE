"""
Phase 2 — Customer Ledger API
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.customer import Customer
from app.models.ledger import LedgerAccount, LedgerEntry
from app.schemas.ledger import LedgerAccountResponse, LedgerStatement, LedgerEntryResponse

router = APIRouter()


async def _get_or_create_account(db: AsyncSession, tenant_id: int, customer_id: int) -> LedgerAccount:
    result = await db.execute(
        select(LedgerAccount).where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.entity_type == "customer",
            LedgerAccount.entity_id == customer_id,
        )
    )
    return result.scalar_one_or_none()


@router.get("/customer/{customer_id}")
async def get_customer_ledger(
    customer_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    ctx=Depends(require_permission("ledger.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns customer ledger statement with period filtering.
    Shows debit/credit entries and running balance.
    """
    user, tenant = ctx

    # Verify customer
    cust_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant.id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    account = await _get_or_create_account(db, tenant.id, customer_id)

    if not account:
        # Return empty ledger
        account_resp = LedgerAccountResponse(
            id=0,
            public_id="",
            tenant_id=tenant.id,
            account_type="customer",
            entity_type="customer",
            entity_id=customer_id,
            name=customer.legal_name,
            currency="TRY",
            status="active",
            total_debit=Decimal("0"),
            total_credit=Decimal("0"),
            balance=Decimal("0"),
        )
        return LedgerStatement(
            account=account_resp,
            entries=[],
            period_debit=Decimal("0"),
            period_credit=Decimal("0"),
            period_balance=Decimal("0"),
            opening_balance=Decimal("0"),
            closing_balance=Decimal("0"),
            date_from=date_from,
            date_to=date_to,
        )

    # Total balance (all time)
    total_result = await db.execute(
        select(
            func.sum(LedgerEntry.debit_amount).label("total_debit"),
            func.sum(LedgerEntry.credit_amount).label("total_credit"),
        )
        .where(
            LedgerEntry.account_id == account.id,
            LedgerEntry.status == "active",
        )
    )
    totals = total_result.first()
    total_debit = Decimal(str(totals.total_debit or 0))
    total_credit = Decimal(str(totals.total_credit or 0))
    total_balance = total_debit - total_credit

    # Opening balance (before date_from)
    opening_balance = Decimal("0")
    if date_from:
        open_result = await db.execute(
            select(
                func.sum(LedgerEntry.debit_amount).label("d"),
                func.sum(LedgerEntry.credit_amount).label("c"),
            )
            .where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.status == "active",
                LedgerEntry.business_date < date_from,
            )
        )
        open_row = open_result.first()
        opening_balance = Decimal(str(open_row.d or 0)) - Decimal(str(open_row.c or 0))

    # Period entries
    entry_conditions = [
        LedgerEntry.account_id == account.id,
        LedgerEntry.status == "active",
    ]
    if date_from:
        entry_conditions.append(LedgerEntry.business_date >= date_from)
    if date_to:
        entry_conditions.append(LedgerEntry.business_date <= date_to)

    entries_result = await db.execute(
        select(LedgerEntry)
        .where(*entry_conditions)
        .order_by(LedgerEntry.business_date.asc(), LedgerEntry.created_at.asc())
    )
    entries = entries_result.scalars().all()

    period_debit = sum((Decimal(str(e.debit_amount)) for e in entries), Decimal("0"))
    period_credit = sum((Decimal(str(e.credit_amount)) for e in entries), Decimal("0"))
    period_balance = period_debit - period_credit
    closing_balance = opening_balance + period_balance

    account_resp = LedgerAccountResponse(
        id=account.id,
        public_id=account.public_id,
        tenant_id=account.tenant_id,
        account_type=account.account_type,
        entity_type=account.entity_type,
        entity_id=account.entity_id,
        name=account.name,
        code=account.code,
        currency=account.currency,
        status=account.status,
        total_debit=total_debit,
        total_credit=total_credit,
        balance=total_balance,
    )

    entry_responses = [
        LedgerEntryResponse(
            id=e.id,
            public_id=e.public_id,
            business_date=e.business_date,
            entry_date=e.entry_date,
            description=e.description,
            debit_amount=Decimal(str(e.debit_amount)),
            credit_amount=Decimal(str(e.credit_amount)),
            source_type=e.source_type,
            source_id=e.source_id,
            status=e.status,
            created_at=e.created_at,
        )
        for e in entries
    ]

    return LedgerStatement(
        account=account_resp,
        entries=entry_responses,
        period_debit=period_debit,
        period_credit=period_credit,
        period_balance=period_balance,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        date_from=date_from,
        date_to=date_to,
    )
