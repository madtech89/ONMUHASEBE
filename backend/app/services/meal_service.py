"""
Phase 2 — Meal Service
Handles:
- Price resolution (versioned, location-specific fallback)
- VAT amount calculation
- Atomic meal event + ledger posting
- Daily aggregate queries
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple

from fastapi import HTTPException
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meal import MealPriceVersion, MealEntryEvent, MealType
from app.models.customer import Customer, CustomerLocation
from app.models.ledger import LedgerAccount, LedgerEntry
from app.services.audit_service import log_audit


# ── VAT Calculation ────────────────────────────────────────────────────────────

def calculate_amounts(
    quantity: Decimal,
    unit_price: Decimal,
    vat_rate: Decimal,
    price_includes_vat: bool,
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Returns (net_amount, vat_amount, gross_amount) with 4-decimal precision.
    No floating-point used.
    """
    q = Decimal(str(quantity))
    p = Decimal(str(unit_price))
    r = Decimal(str(vat_rate))

    if price_includes_vat:
        # KDV Dahil: brüt fiyat verildi, KDV içinden çıkarılır
        gross_amount = (q * p).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        vat_divisor = Decimal("1") + r / Decimal("100")
        net_amount = (gross_amount / vat_divisor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        vat_amount = (gross_amount - net_amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        # KDV Hariç: net fiyat verildi, KDV üstüne eklenir
        net_amount = (q * p).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        vat_amount = (net_amount * r / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        gross_amount = (net_amount + vat_amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    return net_amount, vat_amount, gross_amount


# ── Price Resolution ───────────────────────────────────────────────────────────

async def resolve_price(
    db: AsyncSession,
    tenant_id: int,
    customer_id: int,
    location_id: Optional[int],
    meal_type_id: int,
    business_date: date,
) -> MealPriceVersion:
    """
    Resolution rule:
    1. If location_id provided → try location-specific price first
    2. Fall back to customer default (location_id IS NULL)
    FAIL CLOSED: raises 422 if no price found.
    """
    def build_query(loc_filter):
        return (
            select(MealPriceVersion)
            .where(
                MealPriceVersion.tenant_id == tenant_id,
                MealPriceVersion.customer_id == customer_id,
                MealPriceVersion.meal_type_id == meal_type_id,
                MealPriceVersion.is_active == True,
                MealPriceVersion.effective_from <= business_date,
                or_(
                    MealPriceVersion.effective_to.is_(None),
                    MealPriceVersion.effective_to >= business_date,
                ),
                loc_filter,
            )
            .order_by(MealPriceVersion.effective_from.desc())
            .limit(1)
        )

    # Try location-specific first
    if location_id:
        result = await db.execute(build_query(MealPriceVersion.location_id == location_id))
        price = result.scalar_one_or_none()
        if price:
            return price

    # Fall back to customer default
    result = await db.execute(build_query(MealPriceVersion.location_id.is_(None)))
    price = result.scalar_one_or_none()
    if price:
        return price

    raise HTTPException(
        status_code=422,
        detail="Bu müşteri/lokasyon ve tarih için uygulanabilir yemek fiyatı bulunamadı. "
               "Lütfen önce fiyat tanımı yapın.",
    )


# ── Ledger Account Helper ──────────────────────────────────────────────────────

async def get_or_create_ledger_account(
    db: AsyncSession,
    tenant_id: int,
    customer: Customer,
) -> LedgerAccount:
    """Get existing customer ledger account or create one atomically."""
    result = await db.execute(
        select(LedgerAccount).where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.entity_type == "customer",
            LedgerAccount.entity_id == customer.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = LedgerAccount(
            tenant_id=tenant_id,
            account_type="customer",
            entity_type="customer",
            entity_id=customer.id,
            name=customer.legal_name,
            code=customer.code,
            currency="TRY",
        )
        db.add(account)
        await db.flush()
    return account


# ── Atomic Meal Event + Ledger Posting ────────────────────────────────────────

async def create_meal_event_atomic(
    db: AsyncSession,
    tenant_id: int,
    customer_id: int,
    location_id: Optional[int],
    business_date: date,
    meal_type_id: int,
    quantity: Decimal,
    idempotency_key: str,
    created_by: Optional[int],
    correction_type: Optional[str] = None,
    corrects_event_id: Optional[int] = None,
    correction_reason: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> MealEntryEvent:
    """
    Creates a MealEntryEvent and a corresponding LedgerEntry ATOMICALLY.
    Idempotent: if idempotency_key exists, returns existing event.
    """
    # Idempotency check
    existing = await db.execute(
        select(MealEntryEvent).where(
            MealEntryEvent.tenant_id == tenant_id,
            MealEntryEvent.idempotency_key == idempotency_key,
        )
    )
    existing_event = existing.scalar_one_or_none()
    if existing_event:
        return existing_event

    # Fetch customer (for ledger account)
    cust_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")
    if customer.status != "active":
        raise HTTPException(status_code=422, detail="Pasif müşteri için yemek girişi yapılamaz")

    # Resolve price
    price = await resolve_price(db, tenant_id, customer_id, location_id, meal_type_id, business_date)

    # Calculate amounts
    net_amount, vat_amount, gross_amount = calculate_amounts(
        quantity, price.unit_price, price.vat_rate, price.price_includes_vat
    )

    # Create event
    event = MealEntryEvent(
        tenant_id=tenant_id,
        customer_id=customer_id,
        location_id=location_id,
        business_date=business_date,
        meal_type_id=meal_type_id,
        quantity=quantity,
        unit_price_snapshot=price.unit_price,
        vat_rate_snapshot=price.vat_rate,
        price_includes_vat_snapshot=price.price_includes_vat,
        net_amount=net_amount,
        vat_amount=vat_amount,
        gross_amount=gross_amount,
        price_version_id=price.id,
        idempotency_key=idempotency_key,
        correction_type=correction_type,
        corrects_event_id=corrects_event_id,
        correction_reason=correction_reason,
        created_by=created_by,
        status="active",
    )
    db.add(event)
    await db.flush()  # get event.id

    # Get or create ledger account
    account = await get_or_create_ledger_account(db, tenant_id, customer)

    # Description
    meal_type_result = await db.execute(select(MealType).where(MealType.id == meal_type_id))
    meal_type = meal_type_result.scalar_one_or_none()
    meal_name = meal_type.name_tr if meal_type else f"Meal {meal_type_id}"
    loc_suffix = ""
    if location_id:
        loc_result = await db.execute(select(CustomerLocation).where(CustomerLocation.id == location_id))
        loc = loc_result.scalar_one_or_none()
        if loc:
            loc_suffix = f" / {loc.name}"

    desc_prefix = "Düzeltme: " if correction_type == "correction" else ""
    description = (
        f"{desc_prefix}{business_date.strftime('%d.%m.%Y')} "
        f"{customer.display_name or customer.legal_name}{loc_suffix} - "
        f"{meal_name} x {abs(quantity)}"
    )

    # Ledger entry: DEBIT for meal service (positive qty → debit, negative qty → credit for correction)
    debit_amount = gross_amount if gross_amount > 0 else Decimal("0")
    credit_amount = abs(gross_amount) if gross_amount < 0 else Decimal("0")

    ledger_entry = LedgerEntry(
        tenant_id=tenant_id,
        account_id=account.id,
        business_date=business_date,
        description=description,
        debit_amount=debit_amount,
        credit_amount=credit_amount,
        source_type="meal_event",
        source_id=event.id,
        source_idempotency_key=f"meal_event:{idempotency_key}",
        created_by=created_by,
        status="active",
    )
    db.add(ledger_entry)

    # Audit
    await log_audit(
        db,
        action_type="meal_entry.created" if not correction_type else "meal_entry.correction_created",
        tenant_id=tenant_id,
        user_id=created_by,
        entity_type="meal_entry_event",
        entity_id=str(event.id),
        new_value={
            "business_date": str(business_date),
            "customer_id": customer_id,
            "meal_type_id": meal_type_id,
            "quantity": str(quantity),
            "gross_amount": str(gross_amount),
        },
        ip_address=ip_address,
        severity="info",
    )

    return event


# ── Daily Aggregate Query ──────────────────────────────────────────────────────

async def get_daily_aggregate(
    db: AsyncSession,
    tenant_id: int,
    business_date: date,
    customer_id: Optional[int] = None,
    location_id: Optional[int] = None,
) -> list:
    """
    Returns aggregated meal data for one or more (customer, location, date).
    Groups by: customer_id, location_id, meal_type_id.
    Corrections are included as negative quantities (naturally offsets).
    """
    from sqlalchemy import func as F

    conditions = [
        MealEntryEvent.tenant_id == tenant_id,
        MealEntryEvent.business_date == business_date,
        MealEntryEvent.status == "active",
    ]
    if customer_id:
        conditions.append(MealEntryEvent.customer_id == customer_id)
    if location_id:
        conditions.append(MealEntryEvent.location_id == location_id)

    result = await db.execute(
        select(
            MealEntryEvent.customer_id,
            MealEntryEvent.location_id,
            MealEntryEvent.meal_type_id,
            F.sum(MealEntryEvent.quantity).label("total_quantity"),
            F.sum(MealEntryEvent.net_amount).label("total_net"),
            F.sum(MealEntryEvent.vat_amount).label("total_vat"),
            F.sum(MealEntryEvent.gross_amount).label("total_gross"),
            F.max(MealEntryEvent.created_at).label("last_entry_at"),
        )
        .where(*conditions)
        .group_by(
            MealEntryEvent.customer_id,
            MealEntryEvent.location_id,
            MealEntryEvent.meal_type_id,
        )
        .order_by(MealEntryEvent.customer_id, MealEntryEvent.location_id, MealEntryEvent.meal_type_id)
    )
    return result.all()
