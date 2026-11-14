"""Audit and consent records are separate from patient feature data."""
from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models import Record, PatientRecord


class RecoveryAudit(PatientRecord, Base):
    __tablename__ = "recovery_audits"
    __table_args__ = (Index("ix_recovery_audit_resource", "patient_id", "resource_type", "resource_id", "created_at"),)
    resource_type: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[str] = mapped_column(String(36))
    actor_user_id: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(500))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)


class CaregiverRelationship(PatientRecord, Base):
    __tablename__ = "caregiver_relationships"
    __table_args__ = (
        UniqueConstraint("patient_id", "caregiver_user_id", name="uq_patient_caregiver"),
        Index("ix_caregiver_inbox", "caregiver_user_id", "status", "created_at", "id"),
    )
    caregiver_user_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    permissions: Mapped[list] = mapped_column(JSON)
    alert_severities: Mapped[list] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaregiverAudit(PatientRecord, Base):
    __tablename__ = "caregiver_audits"
    __table_args__ = (Index("ix_caregiver_audit_relationship", "relationship_id", "created_at", "id"),)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("caregiver_relationships.id"))
    actor_user_id: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
