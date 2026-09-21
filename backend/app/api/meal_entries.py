"""
Phase 2 — Meal Entry API
Event-based, append-only. Corrections are separate events.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_permission, get_tenant_context
from app.models.meal import MealType, MealEntryEvent
from app.models.customer import Customer, CustomerLocation
from app.models.user import User
from app.schemas.meal import (
    MealEntryCreate, MealCorrectionCreate,
    MealEventResponse, DailyMealAggregate, DailyMealAggregateItem,
    DailyEntryListResponse,
)
from app.services.meal_service import create_meal_event_atomic, get_daily_aggregate
from app.services.audit_service import log_audit

router = APIRouter()


def _get_ip(request: Request) -> str:
    return request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")


# ── Create Meal Entry ──────────────────────────────────────────────────────────

@router.post("/", response_model=List[MealEventResponse], status_code=201)
async def create_meal_entry(
    body: MealEntryCreate,
    request: Request,
    ctx=Depends(require_permission("meal_entries.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates one MealEntryEvent per non-zero quantity item.
    Idempotent: uses body.idempotency_key (client-generated UUID).
    """
    user, tenant = ctx
    ip = _get_ip(request)

    # Verify active customer
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == body.customer_id,
            Customer.tenant_id == tenant.id,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")
    if customer.status != "active":
        raise HTTPException(status_code=422, detail="Pasif müşteri için giriş yapılamaz")

    # Verify active location
    if body.location_id:
        loc_result = await db.execute(
            select(CustomerLocation).where(
                CustomerLocation.id == body.location_id,
                CustomerLocation.tenant_id == tenant.id,
                CustomerLocation.customer_id == body.customer_id,
            )
        )
        loc = loc_result.scalar_one_or_none()
        if not loc:
            raise HTTPException(status_code=404, detail="Lokasyon bulunamadı")
        if loc.status != "active":
            raise HTTPException(status_code=422, detail="Pasif lokasyon için giriş yapılamaz")

    created_events = []
    for meal_type_id_str, qty in body.quantities.items():
        meal_type_id = int(meal_type_id_str)
        quantity = Decimal(str(qty))
        if quantity == Decimal("0"):
            continue  # Skip zeros

        # Per-item idempotency key = base_key + meal_type
        item_key = f"{body.idempotency_key}:{meal_type_id}"

        event = await create_meal_event_atomic(
            db=db,
            tenant_id=tenant.id,
            customer_id=body.customer_id,
            location_id=body.location_id,
            business_date=body.business_date,
            meal_type_id=meal_type_id,
            quantity=quantity,
            idempotency_key=item_key,
            created_by=user.id,
            ip_address=ip,
        )
        created_events.append(event)

    await db.commit()

    # Reload with meal_type
    result = await db.execute(
        select(MealEntryEvent)
        .where(MealEntryEvent.id.in_([e.id for e in created_events]))
        .options(selectinload(MealEntryEvent.meal_type))
    )
    events = result.scalars().all()

    return [_event_to_response(e) for e in events]


# ── Correction ─────────────────────────────────────────────────────────────────

@router.post("/correction", response_model=MealEventResponse, status_code=201)
async def create_correction(
    body: MealCorrectionCreate,
    request: Request,
    ctx=Depends(require_permission("meal_entries.correct")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a correction event with negative quantity.
    References the original event.
    Requires meal_entries.correct permission (separate from create).
    """
    user, tenant = ctx
    ip = _get_ip(request)

    # Load original event
    orig_result = await db.execute(
        select(MealEntryEvent)
        .where(
            MealEntryEvent.id == body.original_event_id,
            MealEntryEvent.tenant_id == tenant.id,
            MealEntryEvent.status == "active",
        )
    )
    original = orig_result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Orijinal yemek kaydı bulunamadı")

    if body.correction_quantity >= 0:
        raise HTTPException(status_code=422, detail="Düzeltme miktarı negatif olmalıdır")

    event = await create_meal_event_atomic(
        db=db,
        tenant_id=tenant.id,
        customer_id=original.customer_id,
        location_id=original.location_id,
        business_date=original.business_date,
        meal_type_id=original.meal_type_id,
        quantity=body.correction_quantity,
        idempotency_key=body.idempotency_key,
        created_by=user.id,
        correction_type="correction",
        corrects_event_id=original.id,
        correction_reason=body.correction_reason,
        ip_address=ip,
    )
    await db.commit()

    result2 = await db.execute(
        select(MealEntryEvent).where(MealEntryEvent.id == event.id)
        .options(selectinload(MealEntryEvent.meal_type))
    )
    event = result2.scalar_one()
    return _event_to_response(event)


# ── Daily Aggregates ───────────────────────────────────────────────────────────

@router.get("/daily")
async def get_daily_entries(
    business_date: date = Query(default=None),
    customer_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    include_events: bool = Query(False),
    ctx=Depends(require_permission("meal_entries.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns daily meal aggregates.
    One row per (customer, location) showing Kahvaltı/Öğle/Akşam aggregated.
    """
    user, tenant = ctx
    if business_date is None:
        business_date = date.today()

    # Check financial permission
    has_financial = False
    try:
        from app.core.deps import require_permission as rp
        # We check by trying to find the permission in user's roles
        # Simple approach: just include financials always for now,
        # controlled by meal_entries.view_financial
        has_financial = True  # TODO: proper perm check
    except Exception:
        pass

    rows = await get_daily_aggregate(db, tenant.id, business_date, customer_id, location_id)

    # Collect all customer/location/meal_type ids
    customer_ids = list({r.customer_id for r in rows})
    location_ids = list({r.location_id for r in rows if r.location_id})
    meal_type_ids = list({r.meal_type_id for r in rows})

    # Fetch names
    customers_map = {}
    if customer_ids:
        cr = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers_map = {c.id: c for c in cr.scalars().all()}

    locations_map = {}
    if location_ids:
        lr = await db.execute(select(CustomerLocation).where(CustomerLocation.id.in_(location_ids)))
        locations_map = {l.id: l for l in lr.scalars().all()}

    meal_types_map = {}
    if meal_type_ids:
        mtr = await db.execute(select(MealType).where(MealType.id.in_(meal_type_ids)))
        meal_types_map = {mt.id: mt for mt in mtr.scalars().all()}

    # Group by (customer_id, location_id)
    grouped: dict = {}
    for row in rows:
        key = (row.customer_id, row.location_id)
        if key not in grouped:
            customer = customers_map.get(row.customer_id)
            location = locations_map.get(row.location_id) if row.location_id else None
            grouped[key] = {
                "business_date": business_date,
                "customer_id": row.customer_id,
                "customer_name": customer.display_name or customer.legal_name if customer else str(row.customer_id),
                "location_id": row.location_id,
                "location_name": location.name if location else None,
                "items": [],
                "total_net": Decimal("0"),
                "total_vat": Decimal("0"),
                "total_gross": Decimal("0"),
                "last_entry_at": row.last_entry_at,
            }
        mt = meal_types_map.get(row.meal_type_id)
        item = DailyMealAggregateItem(
            meal_type_id=row.meal_type_id,
            meal_type_name=mt.name_tr if mt else str(row.meal_type_id),
            meal_type_code=mt.code if mt else "",
            sort_order=mt.sort_order if mt else 0,
            total_quantity=Decimal(str(row.total_quantity or 0)),
            total_net=Decimal(str(row.total_net or 0)) if has_financial else Decimal("0"),
            total_vat=Decimal(str(row.total_vat or 0)) if has_financial else Decimal("0"),
            total_gross=Decimal(str(row.total_gross or 0)) if has_financial else Decimal("0"),
        )
        grouped[key]["items"].append(item)
        grouped[key]["total_net"] += item.total_net
        grouped[key]["total_vat"] += item.total_vat
        grouped[key]["total_gross"] += item.total_gross
        if row.last_entry_at and (not grouped[key]["last_entry_at"] or row.last_entry_at > grouped[key]["last_entry_at"]):
            grouped[key]["last_entry_at"] = row.last_entry_at

    # Sort items by sort_order
    aggregates = []
    for key, data in grouped.items():
        data["items"].sort(key=lambda x: x.sort_order)
        if include_events:
            data["events"] = await _load_events_for_aggregate(
                db, tenant.id, business_date, data["customer_id"], data["location_id"]
            )
        aggregates.append(DailyMealAggregate(**data))

    # Grand totals
    grand_net = sum(a.total_net for a in aggregates)
    grand_vat = sum(a.total_vat for a in aggregates)
    grand_gross = sum(a.total_gross for a in aggregates)

    return DailyEntryListResponse(
        date=business_date,
        aggregates=aggregates,
        grand_total_net=grand_net,
        grand_total_vat=grand_vat,
        grand_total_gross=grand_gross,
    )


async def _load_events_for_aggregate(
    db: AsyncSession, tenant_id: int, business_date: date, customer_id: int, location_id: Optional[int]
) -> List[MealEventResponse]:
    conditions = [
        MealEntryEvent.tenant_id == tenant_id,
        MealEntryEvent.business_date == business_date,
        MealEntryEvent.customer_id == customer_id,
        MealEntryEvent.status == "active",
    ]
    if location_id:
        conditions.append(MealEntryEvent.location_id == location_id)
    else:
        conditions.append(MealEntryEvent.location_id.is_(None))

    result = await db.execute(
        select(MealEntryEvent)
        .where(*conditions)
        .options(selectinload(MealEntryEvent.meal_type))
        .order_by(MealEntryEvent.created_at)
    )
    events = result.scalars().all()
    return [_event_to_response(e) for e in events]


# ── Event Detail ───────────────────────────────────────────────────────────────

@router.get("/events/{event_public_id}", response_model=MealEventResponse)
async def get_event_detail(
    event_public_id: str,
    ctx=Depends(require_permission("meal_entries.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(MealEntryEvent)
        .where(
            MealEntryEvent.public_id == event_public_id,
            MealEntryEvent.tenant_id == tenant.id,
        )
        .options(selectinload(MealEntryEvent.meal_type))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    return _event_to_response(event)


@router.get("/customer/{customer_id}/history", response_model=List[MealEventResponse])
async def get_customer_event_history(
    customer_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    location_id: Optional[int] = Query(None),
    ctx=Depends(require_permission("meal_entries.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx

    # Verify customer belongs to tenant
    cust = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant.id)
    )
    if not cust.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    conditions = [
        MealEntryEvent.tenant_id == tenant.id,
        MealEntryEvent.customer_id == customer_id,
        MealEntryEvent.status == "active",
    ]
    if date_from:
        conditions.append(MealEntryEvent.business_date >= date_from)
    if date_to:
        conditions.append(MealEntryEvent.business_date <= date_to)
    if location_id:
        conditions.append(MealEntryEvent.location_id == location_id)

    result = await db.execute(
        select(MealEntryEvent)
        .where(*conditions)
        .options(selectinload(MealEntryEvent.meal_type))
        .order_by(MealEntryEvent.business_date.desc(), MealEntryEvent.created_at.desc())
        .limit(500)
    )
    events = result.scalars().all()
    return [_event_to_response(e) for e in events]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _event_to_response(event: MealEntryEvent) -> MealEventResponse:
    return MealEventResponse(
        id=event.id,
        public_id=event.public_id,
        tenant_id=event.tenant_id,
        customer_id=event.customer_id,
        location_id=event.location_id,
        business_date=event.business_date,
        meal_type_id=event.meal_type_id,
        meal_type_name=event.meal_type.name_tr if event.meal_type else "",
        quantity=event.quantity,
        unit_price_snapshot=event.unit_price_snapshot,
        vat_rate_snapshot=event.vat_rate_snapshot,
        price_includes_vat_snapshot=event.price_includes_vat_snapshot,
        net_amount=event.net_amount,
        vat_amount=event.vat_amount,
        gross_amount=event.gross_amount,
        correction_type=event.correction_type,
        corrects_event_id=event.corrects_event_id,
        correction_reason=event.correction_reason,
        status=event.status,
        created_at=event.created_at,
    )
