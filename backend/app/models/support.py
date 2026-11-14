"""Audit and consent records are separate from patient feature data."""
from datetime import datetime, date
from sqlalchemy import ForeignKey, String, DateTime, JSON, UniqueConstraint, Index, Integer
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


class CurriculumTask(PatientRecord, Base):
    """Caregiver-maintained educational task; never a prescription."""
    __tablename__ = "curriculum_tasks"
    __table_args__ = (Index("ix_curriculum_patient_order", "patient_id", "position", "created_at"),)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    due_day: Mapped[date | None]
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)


class CurriculumAudit(PatientRecord, Base):
    """Append-only record of each educational task edit."""
    __tablename__ = "curriculum_audits"
    __table_args__ = (Index("ix_curriculum_audit_task_time", "patient_id", "task_id", "created_at"),)
    task_id: Mapped[str] = mapped_column(ForeignKey("curriculum_tasks.id"))
    actor_user_id: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(30))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
