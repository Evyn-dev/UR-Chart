"""Small fictional demo document attachments, stored in the same SQL database."""
from sqlalchemy import Boolean, ForeignKey, LargeBinary, String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models import PatientRecord


class SharedDocument(PatientRecord, Base):
    __tablename__ = "shared_documents"
    __table_args__ = (Index("ix_shared_document_patient_created", "patient_id", "created_at"),)
    name: Mapped[str] = mapped_column(String(180))
    content_type: Mapped[str] = mapped_column(String(80))
    byte_size: Mapped[int] = mapped_column(Integer)
    payload: Mapped[bytes] = mapped_column(LargeBinary)
    uploader_user_id: Mapped[str] = mapped_column(String(255))
    uploader_role: Mapped[str] = mapped_column(String(20))
    shared_with_caregivers: Mapped[bool] = mapped_column(Boolean, default=False)
    uploader_relationship_id: Mapped[str | None] = mapped_column(ForeignKey("caregiver_relationships.id"))
