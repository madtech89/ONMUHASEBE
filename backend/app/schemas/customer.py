from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class CustomerLocationBase(BaseModel):
    name: str
    location_type: str = "diger"
    address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    delivery_notes: Optional[str] = None


class CustomerLocationCreate(CustomerLocationBase):
    pass


class CustomerLocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    delivery_notes: Optional[str] = None
    status: Optional[str] = None


class CustomerLocationResponse(CustomerLocationBase):
    id: int
    public_id: str
    tenant_id: int
    customer_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerBase(BaseModel):
    legal_name: str
    display_name: Optional[str] = None
    code: Optional[str] = None
    customer_type: str = "company"
    tax_office: Optional[str] = None
    tax_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    default_vat_rate: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    code: Optional[str] = None
    customer_type: Optional[str] = None
    tax_office: Optional[str] = None
    tax_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    default_vat_rate: Optional[str] = None
    status: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: int
    public_id: str
    tenant_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    location_count: int = 0

    model_config = {"from_attributes": True}


class CustomerDetailResponse(CustomerResponse):
    locations: List[CustomerLocationResponse] = []

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
