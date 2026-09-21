import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        default=lambda: str(uuid.uuid4()), index=True
    )
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    # storage_key = relative path within storage backend

    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(50))
    # fatura | irsaliye | sozlesme | arac_belgesi | personel_belgesi | cek | diger

    # Polymorphic relation (optional)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(36))

    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # OCR readiness fields
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | processing | completed | failed | skipped
    ocr_raw_text: Mapped[Optional[str]] = mapped_column(Text)
    ocr_extracted_fields: Mapped[Optional[dict]] = mapped_column(JSON)
    ocr_confidence: Mapped[Optional[float]] = mapped_column()
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Status (soft delete policy)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # active | archived | cancelled

    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])
    verifier: Mapped[Optional["User"]] = relationship(foreign_keys=[verified_by])
    document_links: Mapped[List["DocumentLink"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        Index("ix_documents_tenant_category", "tenant_id", "category"),
        Index("ix_documents_hash", "sha256_hash"),
    )


class DocumentLink(Base):
    __tablename__ = "document_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship(back_populates="document_links")

    __table_args__ = (
        Index("ix_doc_links_entity", "entity_type", "entity_id"),
    )
