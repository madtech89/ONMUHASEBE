import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_permission
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.storage_service import storage, compute_sha256, make_storage_key
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/gif",
    "image/webp", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    document_date: Optional[str] = Form(None),
    related_entity_type: Optional[str] = Form(None),
    related_entity_id: Optional[str] = Form(None),
    ctx=Depends(require_permission("documents.upload")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file.content_type}")

    # Read content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    sha256 = compute_sha256(content)
    doc_public_id = str(uuid.uuid4())

    # Build storage key — do NOT use user-supplied filename as path
    import re
    safe_name = re.sub(r"[^\w.\-]", "_", file.filename or "document")[:100]
    storage_key = make_storage_key(tenant.id, doc_public_id, safe_name)

    await storage.store(content, storage_key)

    doc = Document(
        public_id=doc_public_id,
        tenant_id=tenant.id,
        original_filename=file.filename or "document",
        stored_filename=safe_name,
        storage_key=storage_key,
        mime_type=file.content_type,
        file_size=len(content),
        sha256_hash=sha256,
        category=category,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        uploaded_by=user.id,
    )
    db.add(doc)

    await log_audit(
        db, "document.uploaded",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="document", entity_id=doc_public_id,
        new_value={"filename": file.filename, "size": len(content), "sha256": sha256},
        description=f"Document uploaded: {file.filename}"
    )
    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    ctx=Depends(require_permission("documents.view")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
):
    user, tenant = ctx
    offset = (page - 1) * page_size

    query = select(Document).where(
        Document.tenant_id == tenant.id,
        Document.status == "active",
    )
    if category:
        query = query.where(Document.category == category)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    )
    docs = result.scalars().all()
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{doc_public_id}", response_model=DocumentResponse)
async def get_document(
    doc_public_id: str,
    ctx=Depends(require_permission("documents.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Document).where(
            Document.public_id == doc_public_id,
            Document.tenant_id == tenant.id,  # TENANT ISOLATION
            Document.status == "active",
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_public_id}/download")
async def download_document(
    doc_public_id: str,
    ctx=Depends(require_permission("documents.view")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Document).where(
            Document.public_id == doc_public_id,
            Document.tenant_id == tenant.id,  # TENANT ISOLATION
            Document.status == "active",
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        content = await storage.retrieve(doc.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage")

    await log_audit(
        db, "document.downloaded",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="document", entity_id=doc_public_id,
    )
    await db.commit()

    return StreamingResponse(
        BytesIO(content),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete("/{doc_public_id}")
async def delete_document(
    doc_public_id: str,
    ctx=Depends(require_permission("documents.delete")),
    db: AsyncSession = Depends(get_db),
):
    user, tenant = ctx
    result = await db.execute(
        select(Document).where(
            Document.public_id == doc_public_id,
            Document.tenant_id == tenant.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "archived"  # Soft delete — no hard delete for financial documents
    await log_audit(
        db, "document.archived",
        tenant_id=tenant.id, user_id=user.id, user_email=user.email,
        entity_type="document", entity_id=doc_public_id,
        severity="warning",
    )
    await db.commit()
    return {"ok": True}
