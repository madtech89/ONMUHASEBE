from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class MealReportRow(BaseModel):
    business_date: date
    customer_id: int
    customer_name: str
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    meal_type_id: int
    meal_type_name: str
    meal_type_code: str
    total_quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    total_net: Decimal
    total_vat: Decimal
    total_gross: Decimal


class MealReportSummary(BaseModel):
    total_quantity: Decimal
    total_net: Decimal
    total_vat: Decimal
    total_gross: Decimal
    by_meal_type: dict  # {meal_type_code: {qty, net, vat, gross}}


class MealReportResponse(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    location_id: Optional[int] = None
    date_from: date
    date_to: date
    rows: List[MealReportRow]
    summary: MealReportSummary
    generated_at: datetime


class ReportFilterRequest(BaseModel):
    date_from: date
    date_to: date
    customer_id: Optional[int] = None
    location_id: Optional[int] = None
    meal_type_id: Optional[int] = None
    group_by_location: bool = True
    include_daily_detail: bool = False
