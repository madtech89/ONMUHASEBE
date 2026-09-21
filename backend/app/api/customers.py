"""
Phase 2 — Customer & Customer Location API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_permission, get_tenant_context
from app.models.customer import Customer, CustomerLocation
from app.models.ledger import LedgerAccount, LedgerEntry
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerDetailResponse, CustomerListResponse,
    CustomerLocationCreate, CustomerLocationUpdate, CustomerLocationResponse,
)
from app.services.audit_service import log_audit

router = APIRouter()


# ── Customer CRUD ─────────────────────────────────────────────────────────────

@router.get("/", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    ctx=Depends(require_permission("customers.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    conditions = [Customer.tenant_id == tenant.id]
    if status:
        conditions.append(Customer.status == status)
    if search:
        like = f"%{search}%"
        from sqlalchemy import or_
        conditions.append(
            or_(
                Customer.legal_name.ilike(like),
                Customer.display_name.ilike(like),
                Customer.code.ilike(like),
                Customer.phone.ilike(like),
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(Customer).where(*conditions)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Customer).where(*conditions)
        .order_by(Customer.legal_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    customers = result.scalars().all()

    # Location counts
    counts_result = await db.execute(
        select(CustomerLocation.customer_id, func.count(CustomerLocation.id))
        .where(
            CustomerLocation.tenant_id == tenant.id,
            CustomerLocation.status == "active",
        )
        .group_by(CustomerLocation.customer_id)
    )
    counts = {row[0]: row[1] for row in counts_result}

    # Check financial permission
    show_financials = False  # TODO: check customer_financials.view permission

    items = []
    for c in customers:
        resp = CustomerResponse.model_validate(c)
        resp.location_count = counts.get(c.id, 0)
        items.append(resp)

    return CustomerListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/", response_model=CustomerDetailResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    ctx=Depends(require_permission("customers.create")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx

    # Duplicate code check
    if body.code:
        existing = await db.execute(
            select(Customer).where(
                Customer.tenant_id == tenant.id,
                Customer.code == body.code,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"'{body.code}' kodlu müşteri zaten mevcut")

    customer = Customer(
        tenant_id=tenant.id,
        created_by=user.id,
        **body.model_dump(),
    )
    db.add(customer)
    await db.flush()

    await log_audit(
        db, "customer.created",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="customer", entity_id=str(customer.id),
        new_value={"legal_name": customer.legal_name, "code": customer.code},
        severity="info",
    )
    await db.commit()
    await db.refresh(customer)

    result = await db.execute(
        select(Customer).where(Customer.id == customer.id)
        .options(selectinload(Customer.locations))
    )
    customer = result.scalar_one()
    resp = CustomerDetailResponse.model_validate(customer)
    resp.location_count = 0
    return resp


@router.get("/{customer_public_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_public_id: str,
    ctx=Depends(require_permission("customers.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Customer)
        .where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
        .options(selectinload(Customer.locations))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    resp = CustomerDetailResponse.model_validate(customer)
    resp.location_count = len([l for l in customer.locations if l.status == "active"])
    return resp


@router.put("/{customer_public_id}", response_model=CustomerDetailResponse)
async def update_customer(
    customer_public_id: str,
    body: CustomerUpdate,
    ctx=Depends(require_permission("customers.edit")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Customer)
        .where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
        .options(selectinload(Customer.locations))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    # Code uniqueness check
    if body.code and body.code != customer.code:
        dup = await db.execute(
            select(Customer).where(
                Customer.tenant_id == tenant.id,
                Customer.code == body.code,
                Customer.id != customer.id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"'{body.code}' kodu başka müşteride kullanımda")

    old_status = customer.status
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(customer, field, value)

    await log_audit(
        db, "customer.updated",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="customer", entity_id=str(customer.id),
        new_value=body.model_dump(exclude_none=True),
        severity="info",
    )
    await db.commit()
    await db.refresh(customer)

    result2 = await db.execute(
        select(Customer).where(Customer.id == customer.id)
        .options(selectinload(Customer.locations))
    )
    customer = result2.scalar_one()
    resp = CustomerDetailResponse.model_validate(customer)
    resp.location_count = len([l for l in customer.locations if l.status == "active"])
    return resp


@router.delete("/{customer_public_id}", status_code=204)
async def deactivate_customer(
    customer_public_id: str,
    ctx=Depends(require_permission("customers.deactivate")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Customer).where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    customer.status = "inactive"
    await log_audit(
        db, "customer.deactivated",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="customer", entity_id=str(customer.id),
        severity="warning",
    )
    await db.commit()


# ── Customer Search (for meal entry quick search) ─────────────────────────────
# IMPORTANT: This MUST be defined before /{customer_public_id}/locations
# to prevent FastAPI from capturing "search" as the path parameter.

@router.get("/search/locations")
async def search_customer_locations(
    q: str = Query("", min_length=0),
    ctx=Depends(require_permission("customers.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns active customer+location pairs for meal entry search.
    Result: [{customer_id, customer_name, location_id, location_name, display}]
    """
    user, tenant = ctx
    from sqlalchemy import or_

    conditions = [
        Customer.tenant_id == tenant.id,
        Customer.status == "active",
        CustomerLocation.tenant_id == tenant.id,
        CustomerLocation.status == "active",
        CustomerLocation.customer_id == Customer.id,
    ]
    if q:
        like = f"%{q}%"
        conditions.append(
            or_(
                Customer.legal_name.ilike(like),
                Customer.display_name.ilike(like),
                CustomerLocation.name.ilike(like),
            )
        )

    result = await db.execute(
        select(
            Customer.id.label("customer_id"),
            Customer.legal_name.label("customer_name"),
            Customer.display_name.label("customer_display"),
            CustomerLocation.id.label("location_id"),
            CustomerLocation.public_id.label("location_public_id"),
            CustomerLocation.name.label("location_name"),
            CustomerLocation.location_type.label("location_type"),
        )
        .where(*conditions)
        .order_by(Customer.legal_name, CustomerLocation.name)
        .limit(30)
    )
    rows = result.all()
    return [
        {
            "customer_id": r.customer_id,
            "customer_name": r.customer_display or r.customer_name,
            "customer_legal_name": r.customer_name,
            "location_id": r.location_id,
            "location_public_id": r.location_public_id,
            "location_name": r.location_name,
            "location_type": r.location_type,
            "display": f"{r.customer_display or r.customer_name} — {r.location_name}",
        }
        for r in rows
    ]


# ── Customer Locations ─────────────────────────────────────────────────────────

@router.get("/{customer_public_id}/locations", response_model=list[CustomerLocationResponse])
async def list_locations(
    customer_public_id: str,
    ctx=Depends(require_permission("customers.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    cust_result = await db.execute(
        select(Customer).where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    result = await db.execute(
        select(CustomerLocation)
        .where(CustomerLocation.customer_id == customer.id, CustomerLocation.tenant_id == tenant.id)
        .order_by(CustomerLocation.name)
    )
    return [CustomerLocationResponse.model_validate(l) for l in result.scalars().all()]


@router.post("/{customer_public_id}/locations", response_model=CustomerLocationResponse, status_code=201)
async def create_location(
    customer_public_id: str,
    body: CustomerLocationCreate,
    ctx=Depends(require_permission("customers.edit")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    cust_result = await db.execute(
        select(Customer).where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    location = CustomerLocation(
        tenant_id=tenant.id,
        customer_id=customer.id,
        **body.model_dump(),
    )
    db.add(location)
    await log_audit(
        db, "location.created",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="customer_location", entity_id=str(customer.id),
        new_value={"name": location.name, "customer_id": customer.id},
        severity="info",
    )
    await db.commit()
    await db.refresh(location)
    return CustomerLocationResponse.model_validate(location)


@router.put("/{customer_public_id}/locations/{location_public_id}", response_model=CustomerLocationResponse)
async def update_location(
    customer_public_id: str,
    location_public_id: str,
    body: CustomerLocationUpdate,
    ctx=Depends(require_permission("customers.edit")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    # Verify customer belongs to tenant
    cust_result = await db.execute(
        select(Customer).where(Customer.public_id == customer_public_id, Customer.tenant_id == tenant.id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")

    loc_result = await db.execute(
        select(CustomerLocation).where(
            CustomerLocation.public_id == location_public_id,
            CustomerLocation.customer_id == customer.id,
            CustomerLocation.tenant_id == tenant.id,
        )
    )
    location = loc_result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Lokasyon bulunamadı")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(location, field, value)

    await log_audit(
        db, "location.updated",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="customer_location", entity_id=str(location.id),
        severity="info",
    )
    await db.commit()
    await db.refresh(location)
    return CustomerLocationResponse.model_validate(location)

