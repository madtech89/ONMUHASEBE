"""
Phase 2 — Meal Pricing API (date-versioned)
"""
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.meal import MealType, MealPriceVersion
from app.models.customer import Customer, CustomerLocation
from app.schemas.meal import PriceVersionCreate, PriceVersionResponse, MealTypeResponse
from app.services.audit_service import log_audit

router = APIRouter()


@router.get("/meal-types", response_model=List[MealTypeResponse])
async def list_meal_types(
    ctx=Depends(require_permission("customers.view")),
    db: AsyncSession = Depends(get_db),
):
    """Returns system meal types + tenant-specific meal types."""
    user, tenant = ctx
    result = await db.execute(
        select(MealType)
        .where(
            or_(MealType.tenant_id.is_(None), MealType.tenant_id == tenant.id),
            MealType.is_active == True,
        )
        .order_by(MealType.sort_order, MealType.name_tr)
    )
    return [MealTypeResponse.model_validate(mt) for mt in result.scalars().all()]


@router.get("/customer/{customer_id}", response_model=List[PriceVersionResponse])
async def get_customer_prices(
    customer_id: int,
    location_id: Optional[int] = Query(None),
    meal_type_id: Optional[int] = Query(None),
    active_only: bool = Query(False),
    ctx=Depends(require_permission("meal_prices.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get all price versions for a customer (optionally filtered by location/meal type)."""
    user, tenant = ctx

    # Verify customer belongs to tenant
    cust = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant.id)
    )
    if not cust.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    conditions = [
        MealPriceVersion.tenant_id == tenant.id,
        MealPriceVersion.customer_id == customer_id,
    ]
    if location_id is not None:
        conditions.append(MealPriceVersion.location_id == location_id)
    if meal_type_id:
        conditions.append(MealPriceVersion.meal_type_id == meal_type_id)
    if active_only:
        today = date.today()
        conditions.append(MealPriceVersion.is_active == True)
        conditions.append(MealPriceVersion.effective_from <= today)
        conditions.append(
            or_(MealPriceVersion.effective_to.is_(None), MealPriceVersion.effective_to >= today)
        )

    result = await db.execute(
        select(MealPriceVersion)
        .where(*conditions)
        .options(selectinload(MealPriceVersion.meal_type))
        .order_by(MealPriceVersion.meal_type_id, MealPriceVersion.effective_from.desc())
    )
    prices = result.scalars().all()

    out = []
    for p in prices:
        resp = PriceVersionResponse.model_validate(p)
        resp.meal_type_name = p.meal_type.name_tr if p.meal_type else ""
        out.append(resp)
    return out


@router.post("/", response_model=PriceVersionResponse, status_code=201)
async def create_price_version(
    body: PriceVersionCreate,
    ctx=Depends(require_permission("meal_prices.manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new date-versioned price.
    If an open-ended price exists for the same scope, its effective_to is closed
    to effective_from - 1 day (safe period closing).
    Prevents overlapping price periods.
    """
    user, tenant = ctx

    # Verify customer
    cust = await db.execute(
        select(Customer).where(Customer.id == body.customer_id, Customer.tenant_id == tenant.id)
    )
    if not cust.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    # Verify location if provided
    if body.location_id:
        loc = await db.execute(
            select(CustomerLocation).where(
                CustomerLocation.id == body.location_id,
                CustomerLocation.tenant_id == tenant.id,
                CustomerLocation.customer_id == body.customer_id,
            )
        )
        if not loc.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Lokasyon bulunamadı veya bu müşteriye ait değil")

    # Overlap check: find any existing active price in same scope that would overlap
    overlap_conditions = [
        MealPriceVersion.tenant_id == tenant.id,
        MealPriceVersion.customer_id == body.customer_id,
        MealPriceVersion.meal_type_id == body.meal_type_id,
        MealPriceVersion.is_active == True,
    ]
    if body.location_id:
        overlap_conditions.append(MealPriceVersion.location_id == body.location_id)
    else:
        overlap_conditions.append(MealPriceVersion.location_id.is_(None))

    # Find prices that overlap with the new effective_from
    overlap_result = await db.execute(
        select(MealPriceVersion)
        .where(
            *overlap_conditions,
            or_(
                MealPriceVersion.effective_to.is_(None),
                MealPriceVersion.effective_to >= body.effective_from,
            ),
            MealPriceVersion.effective_from <= body.effective_from,
        )
        .order_by(MealPriceVersion.effective_from.desc())
    )
    overlapping = overlap_result.scalars().all()
    if overlapping:
        # Close the previous period
        for prev in overlapping:
            if prev.effective_from == body.effective_from:
                raise HTTPException(
                    status_code=409,
                    detail=f"Aynı başlangıç tarihi ({body.effective_from}) için zaten bir fiyat mevcut."
                )
            prev.effective_to = body.effective_from - timedelta(days=1)

    # Also check for future prices that might conflict
    future_result = await db.execute(
        select(MealPriceVersion)
        .where(
            *overlap_conditions,
            MealPriceVersion.effective_from > body.effective_from,
        )
        .order_by(MealPriceVersion.effective_from.asc())
        .limit(1)
    )
    next_price = future_result.scalar_one_or_none()
    effective_to = None
    if next_price:
        effective_to = next_price.effective_from - timedelta(days=1)

    new_price = MealPriceVersion(
        tenant_id=tenant.id,
        customer_id=body.customer_id,
        location_id=body.location_id,
        meal_type_id=body.meal_type_id,
        effective_from=body.effective_from,
        effective_to=effective_to,
        unit_price=body.unit_price,
        vat_rate=body.vat_rate,
        price_includes_vat=body.price_includes_vat,
        is_active=True,
        reason=body.reason,
        created_by=user.id,
    )
    db.add(new_price)

    await log_audit(
        db, "price.created",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="meal_price_version", entity_id=None,
        new_value={
            "customer_id": body.customer_id,
            "location_id": body.location_id,
            "meal_type_id": body.meal_type_id,
            "effective_from": str(body.effective_from),
            "unit_price": str(body.unit_price),
        },
        severity="info",
    )
    await db.commit()
    await db.refresh(new_price)

    result2 = await db.execute(
        select(MealPriceVersion).where(MealPriceVersion.id == new_price.id)
        .options(selectinload(MealPriceVersion.meal_type))
    )
    new_price = result2.scalar_one()
    resp = PriceVersionResponse.model_validate(new_price)
    resp.meal_type_name = new_price.meal_type.name_tr if new_price.meal_type else ""
    return resp


@router.delete("/{price_id}", status_code=204)
async def deactivate_price(
    price_id: int,
    ctx=Depends(require_permission("meal_prices.manage")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(MealPriceVersion).where(
            MealPriceVersion.id == price_id,
            MealPriceVersion.tenant_id == tenant.id,
        )
    )
    price = result.scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Fiyat bulunamadı")

    price.is_active = False
    await log_audit(
        db, "price.deactivated",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="meal_price_version", entity_id=str(price.id),
        severity="warning",
    )
    await db.commit()
