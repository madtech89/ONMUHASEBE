from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class TenantSettingsSchema(BaseModel):
    ticari_unvan: Optional[str] = None
    kisa_ad: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    vergi_dairesi: Optional[str] = None
    vergi_no: Optional[str] = None
    adres: Optional[str] = None
    telefon: Optional[str] = None
    eposta: Optional[str] = None
    website: Optional[str] = None
    para_birimi: str = "TRY"
    kdv_orani: Optional[str] = "20"
    timezone: str = "Europe/Istanbul"
    iban: Optional[str] = None
    banka_bilgileri: Optional[str] = None
    pdf_header: Optional[str] = None
    pdf_footer: Optional[str] = None
    belge_numaralama: Optional[dict] = None

    model_config = {"from_attributes": True}


class TenantCreate(BaseModel):
    name: str
    short_name: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    status: Optional[str] = None


class TenantResponse(BaseModel):
    id: int
    public_id: str
    name: str
    short_name: Optional[str] = None
    status: str
    created_at: datetime
    settings: Optional[TenantSettingsSchema] = None

    model_config = {"from_attributes": True}


class ModuleResponse(BaseModel):
    id: int
    code: str
    name_tr: str
    name_en: str
    description: Optional[str] = None
    is_core: bool
    sort_order: int

    model_config = {"from_attributes": True}


class TenantModuleResponse(BaseModel):
    module: ModuleResponse
    is_enabled: bool
    enabled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TenantStatsResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    user_count: int
    document_count: int
    active_modules: int
    status: str
