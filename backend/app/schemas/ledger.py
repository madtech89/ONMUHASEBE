from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class LedgerAccountResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: int
    account_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    name: str
    code: Optional[str] = None
    currency: str
    status: str
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")  # debit - credit (positive = customer owes)

    model_config = {"from_attributes": True}


class LedgerEntryResponse(BaseModel):
    id: int
    public_id: str
    business_date: date
    entry_date: datetime
    description: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    status: str
    created_at: datetime
    created_by_email: Optional[str] = None

    model_config = {"from_attributes": True}


class LedgerStatement(BaseModel):
    account: LedgerAccountResponse
    entries: List[LedgerEntryResponse]
    period_debit: Decimal
    period_credit: Decimal
    period_balance: Decimal
    opening_balance: Decimal
    closing_balance: Decimal
    date_from: Optional[date]
    date_to: Optional[date]
