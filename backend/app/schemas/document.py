from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: int
    original_filename: str
    mime_type: str
    file_size: int
    sha256_hash: str
    category: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    document_date: Optional[datetime] = None
    ocr_status: str = "pending"
    human_verified: bool = False
    status: str
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
