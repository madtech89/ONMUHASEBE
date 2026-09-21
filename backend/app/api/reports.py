"""
Phase 2 — Reports API: Date-range meal report, PDF export, Excel export
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.meal import MealEntryEvent, MealType
from app.models.customer import Customer, CustomerLocation
from app.models.tenant import TenantSettings
from app.schemas.report import MealReportResponse, MealReportRow, MealReportSummary

router = APIRouter()


async def _build_report(
    db: AsyncSession,
    tenant_id: int,
    date_from: date,
    date_to: date,
    customer_id: Optional[int] = None,
    location_id: Optional[int] = None,
    meal_type_id: Optional[int] = None,
) -> MealReportResponse:

    conditions = [
        MealEntryEvent.tenant_id == tenant_id,
        MealEntryEvent.business_date >= date_from,
        MealEntryEvent.business_date <= date_to,
        MealEntryEvent.status == "active",
    ]
    if customer_id:
        conditions.append(MealEntryEvent.customer_id == customer_id)
    if location_id:
        conditions.append(MealEntryEvent.location_id == location_id)
    if meal_type_id:
        conditions.append(MealEntryEvent.meal_type_id == meal_type_id)

    # Aggregate by (business_date, customer_id, location_id, meal_type_id)
    agg_result = await db.execute(
        select(
            MealEntryEvent.business_date,
            MealEntryEvent.customer_id,
            MealEntryEvent.location_id,
            MealEntryEvent.meal_type_id,
            MealEntryEvent.unit_price_snapshot,
            MealEntryEvent.vat_rate_snapshot,
            func.sum(MealEntryEvent.quantity).label("total_quantity"),
            func.sum(MealEntryEvent.net_amount).label("total_net"),
            func.sum(MealEntryEvent.vat_amount).label("total_vat"),
            func.sum(MealEntryEvent.gross_amount).label("total_gross"),
        )
        .where(*conditions)
        .group_by(
            MealEntryEvent.business_date,
            MealEntryEvent.customer_id,
            MealEntryEvent.location_id,
            MealEntryEvent.meal_type_id,
            MealEntryEvent.unit_price_snapshot,
            MealEntryEvent.vat_rate_snapshot,
        )
        .order_by(MealEntryEvent.business_date, MealEntryEvent.customer_id)
    )
    rows_raw = agg_result.all()

    if not rows_raw:
        return MealReportResponse(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            rows=[],
            summary=MealReportSummary(
                total_quantity=Decimal("0"),
                total_net=Decimal("0"),
                total_vat=Decimal("0"),
                total_gross=Decimal("0"),
                by_meal_type={},
            ),
            generated_at=datetime.now(timezone.utc),
        )

    # Fetch lookup data
    cust_ids = list({r.customer_id for r in rows_raw})
    loc_ids = list({r.location_id for r in rows_raw if r.location_id})
    mt_ids = list({r.meal_type_id for r in rows_raw})

    customers_map = {}
    if cust_ids:
        cr = await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))
        customers_map = {c.id: c for c in cr.scalars().all()}

    locations_map = {}
    if loc_ids:
        lr = await db.execute(select(CustomerLocation).where(CustomerLocation.id.in_(loc_ids)))
        locations_map = {l.id: l for l in lr.scalars().all()}

    meal_types_map = {}
    if mt_ids:
        mtr = await db.execute(select(MealType).where(MealType.id.in_(mt_ids)))
        meal_types_map = {mt.id: mt for mt in mtr.scalars().all()}

    rows = []
    total_qty = Decimal("0")
    total_net = Decimal("0")
    total_vat = Decimal("0")
    total_gross = Decimal("0")
    by_meal_type: dict = {}

    for r in rows_raw:
        customer = customers_map.get(r.customer_id)
        location = locations_map.get(r.location_id) if r.location_id else None
        mt = meal_types_map.get(r.meal_type_id)

        qty = Decimal(str(r.total_quantity or 0))
        net = Decimal(str(r.total_net or 0))
        vat = Decimal(str(r.total_vat or 0))
        gross = Decimal(str(r.total_gross or 0))

        row = MealReportRow(
            business_date=r.business_date,
            customer_id=r.customer_id,
            customer_name=customer.display_name or customer.legal_name if customer else str(r.customer_id),
            location_id=r.location_id,
            location_name=location.name if location else None,
            meal_type_id=r.meal_type_id,
            meal_type_name=mt.name_tr if mt else str(r.meal_type_id),
            meal_type_code=mt.code if mt else "",
            total_quantity=qty,
            unit_price=Decimal(str(r.unit_price_snapshot)),
            vat_rate=Decimal(str(r.vat_rate_snapshot)),
            total_net=net,
            total_vat=vat,
            total_gross=gross,
        )
        rows.append(row)

        total_qty += qty
        total_net += net
        total_vat += vat
        total_gross += gross

        mt_code = mt.code if mt else str(r.meal_type_id)
        mt_name = mt.name_tr if mt else str(r.meal_type_id)
        if mt_code not in by_meal_type:
            by_meal_type[mt_code] = {"name": mt_name, "qty": Decimal("0"), "net": Decimal("0"), "vat": Decimal("0"), "gross": Decimal("0")}
        by_meal_type[mt_code]["qty"] += qty
        by_meal_type[mt_code]["net"] += net
        by_meal_type[mt_code]["vat"] += vat
        by_meal_type[mt_code]["gross"] += gross

    # Convert decimals to float for JSON serialization in by_meal_type
    by_meal_type_serializable = {
        k: {
            "name": v["name"],
            "qty": float(v["qty"]),
            "net": float(v["net"]),
            "vat": float(v["vat"]),
            "gross": float(v["gross"]),
        }
        for k, v in by_meal_type.items()
    }

    customer_name = None
    if customer_id and customer_id in customers_map:
        c = customers_map[customer_id]
        customer_name = c.display_name or c.legal_name

    return MealReportResponse(
        customer_id=customer_id,
        customer_name=customer_name,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        summary=MealReportSummary(
            total_quantity=total_qty,
            total_net=total_net,
            total_vat=total_vat,
            total_gross=total_gross,
            by_meal_type=by_meal_type_serializable,
        ),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/meals")
async def get_meal_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    customer_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    meal_type_id: Optional[int] = Query(None),
    ctx=Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="Başlangıç tarihi bitiş tarihinden büyük olamaz")
    return await _build_report(db, tenant.id, date_from, date_to, customer_id, location_id, meal_type_id)


@router.get("/meals/pdf")
async def export_meal_report_pdf(
    date_from: date = Query(...),
    date_to: date = Query(...),
    customer_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    ctx=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    report = await _build_report(db, tenant.id, date_from, date_to, customer_id, location_id)

    # Get tenant branding
    settings_result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    settings = settings_result.scalar_one_or_none()
    tenant_name = settings.ticari_unvan or tenant.name if settings else tenant.name
    tenant_phone = settings.telefon if settings else None
    tenant_address = settings.adres if settings else None
    tenant_tax_no = settings.vergi_no if settings else None

    from app.services.report_service import generate_meal_report_pdf
    pdf_bytes = generate_meal_report_pdf(
        report=report,
        tenant_name=tenant_name,
        tenant_phone=tenant_phone,
        tenant_address=tenant_address,
        tenant_tax_no=tenant_tax_no,
    )

    filename = f"yemek_raporu_{date_from}_{date_to}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/meals/excel")
async def export_meal_report_excel(
    date_from: date = Query(...),
    date_to: date = Query(...),
    customer_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    ctx=Depends(require_permission("reports.export")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    report = await _build_report(db, tenant.id, date_from, date_to, customer_id, location_id)

    settings_result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    settings = settings_result.scalar_one_or_none()
    tenant_name = settings.ticari_unvan or tenant.name if settings else tenant.name

    from app.services.report_service import generate_meal_report_excel
    xlsx_bytes = generate_meal_report_excel(report=report, tenant_name=tenant_name)

    filename = f"yemek_raporu_{date_from}_{date_to}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
