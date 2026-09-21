from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator


class MealTypeResponse(BaseModel):
    id: int
    code: str
    name_tr: str
    name_en: str
    sort_order: int
    is_active: bool
    tenant_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Price Versions ────────────────────────────────────────────────────────────

class PriceVersionCreate(BaseModel):
    customer_id: int
    location_id: Optional[int] = None
    meal_type_id: int
    effective_from: date
    unit_price: Decimal
    vat_rate: Decimal
    price_includes_vat: bool = False
    reason: Optional[str] = None

    @field_validator("unit_price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Birim fiyat sıfırdan büyük olmalıdır")
        return v

    @field_validator("vat_rate")
    @classmethod
    def vat_valid(cls, v):
        if v < 0 or v > 100:
            raise ValueError("KDV oranı 0-100 arasında olmalıdır")
        return v


class PriceVersionResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: int
    customer_id: int
    location_id: Optional[int] = None
    meal_type_id: int
    meal_type_name: str = ""
    effective_from: date
    effective_to: Optional[date] = None
    unit_price: Decimal
    vat_rate: Decimal
    price_includes_vat: bool
    is_active: bool
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Meal Entry Events ─────────────────────────────────────────────────────────

class MealEntryCreate(BaseModel):
    customer_id: int
    location_id: Optional[int] = None
    business_date: date
    quantities: dict  # {meal_type_id: quantity}  e.g. {"1": 10, "2": 30}
    idempotency_key: str  # Client-generated UUID

    @field_validator("quantities")
    @classmethod
    def validate_quantities(cls, v):
        if not v:
            raise ValueError("En az bir yemek miktarı girilmelidir")
        for k, qty in v.items():
            if Decimal(str(qty)) < 0:
                raise ValueError("Normal giriş formu ile negatif miktar girilemez")
            if Decimal(str(qty)) == 0:
                continue  # zeros filtered server-side
        return v


class MealCorrectionCreate(BaseModel):
    original_event_id: int
    correction_quantity: Decimal  # negative value
    correction_reason: str
    idempotency_key: str


class MealEventResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: int
    customer_id: int
    location_id: Optional[int] = None
    business_date: date
    meal_type_id: int
    meal_type_name: str = ""
    quantity: Decimal
    unit_price_snapshot: Decimal
    vat_rate_snapshot: Decimal
    price_includes_vat_snapshot: bool
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    correction_type: Optional[str] = None
    corrects_event_id: Optional[int] = None
    correction_reason: Optional[str] = None
    status: str
    created_at: datetime
    created_by_email: Optional[str] = None

    model_config = {"from_attributes": True}


class DailyMealAggregateItem(BaseModel):
    meal_type_id: int
    meal_type_name: str
    meal_type_code: str
    sort_order: int
    total_quantity: Decimal
    total_net: Decimal
    total_vat: Decimal
    total_gross: Decimal


class DailyMealAggregate(BaseModel):
    business_date: date
    customer_id: int
    customer_name: str
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    items: List[DailyMealAggregateItem]
    total_net: Decimal
    total_vat: Decimal
    total_gross: Decimal
    last_entry_at: Optional[datetime] = None
    events: Optional[List[MealEventResponse]] = None  # only when detail requested


class DailyEntryListResponse(BaseModel):
    date: date
    aggregates: List[DailyMealAggregate]
    grand_total_net: Decimal
    grand_total_vat: Decimal
    grand_total_gross: Decimal
