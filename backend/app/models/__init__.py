from datetime import datetime, timezone, date
from uuid import uuid4
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def now():
    return datetime.now(timezone.utc)


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Patient(Record, Base):
    __tablename__ = "patients"
    user_id: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Synthetic patient")
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    recovery_plans: Mapped[list["RecoveryPlan"]] = relationship(back_populates="patient")
    medications: Mapped[list["Medication"]] = relationship(back_populates="patient")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="patient")


class PatientRecord(Record):
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)


class RecoveryPlan(PatientRecord, Base):
    __tablename__ = "recovery_plans"
    title: Mapped[str] = mapped_column(String(200))
    approved_instructions: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    patient: Mapped[Patient] = relationship(back_populates="recovery_plans")


class Medication(PatientRecord, Base):
    __tablename__ = "medications"
    __table_args__ = (Index("ix_medication_patient_active_created", "patient_id", "active", "created_at", "id"),)
    name: Mapped[str] = mapped_column(String(200))
    dosage: Mapped[str] = mapped_column(String(200))
    schedule: Mapped[str] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(default=True)
    reminder_times: Mapped[list] = mapped_column(JSON, default=list)
    supply_remaining: Mapped[int | None] = mapped_column(nullable=True)
    refill_threshold: Mapped[int | None] = mapped_column(nullable=True)
    inventory_revision: Mapped[int] = mapped_column(default=1)
    patient: Mapped[Patient] = relationship(back_populates="medications")
    logs: Mapped[list["MedicationLog"]] = relationship(back_populates="medication")


class MedicationLog(Record, Base):
    __tablename__ = "medication_logs"
    __table_args__ = (UniqueConstraint("medication_id", "scheduled_for", name="uq_medication_scheduled_dose"), Index("ix_log_medication_recorded", "medication_id", "recorded_at", "id"))
    medication_id: Mapped[str] = mapped_column(ForeignKey("medications.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(1000))
    schedule_id: Mapped[str | None] = mapped_column(ForeignKey("medication_schedules.id"))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    units_used: Mapped[int | None]
    version: Mapped[int] = mapped_column(default=1)
    inventory_revision: Mapped[int] = mapped_column(default=1)
    medication: Mapped[Medication] = relationship(back_populates="logs")


class Checkin(PatientRecord, Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("patient_id", "day", name="uq_checkin_patient_day"),)
    day: Mapped[date]
    version: Mapped[int] = mapped_column(default=1)
    wellbeing: Mapped[int | None]
    note: Mapped[str | None] = mapped_column(String(2000))
    pain_level: Mapped[int | None] = mapped_column(nullable=True)
    symptoms: Mapped[list] = mapped_column(JSON, default=list)
    activity_minutes: Mapped[int | None] = mapped_column(nullable=True)
    symptom_reports: Mapped[list] = mapped_column(JSON, default=list)
    activity_type: Mapped[str | None] = mapped_column(String(100))


class Conversation(PatientRecord, Base):
    __tablename__ = "conversations"
    title: Mapped[str] = mapped_column(String(100))
    patient: Mapped[Patient] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at, Message.id")


class Message(Record, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Alert(PatientRecord, Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("checkin_id", "rule_id", "rule_version", "checkin_version", name="uq_alert_checkin_rule_revision"), Index("ix_alert_patient_created", "patient_id", "created_at", "id"))
    category: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="open")
    severity: Mapped[str] = mapped_column(String(30), default="routine")
    checkin_id: Mapped[str | None] = mapped_column(ForeignKey("checkins.id"), index=True)
    rule_id: Mapped[str | None] = mapped_column(String(100))
    rule_version: Mapped[str | None] = mapped_column(String(100))
    prototype_only: Mapped[bool] = mapped_column(default=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    notification_status: Mapped[str] = mapped_column(String(30), default="not_sent")
    checkin_version: Mapped[int] = mapped_column(default=1)
    version: Mapped[int] = mapped_column(default=1)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CareTeamConnection(PatientRecord, Base):
    __tablename__ = "care_team_connections"
    __table_args__ = (UniqueConstraint("patient_id", "member_user_id", name="uq_care_team_member"),)
    member_user_id: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(100))


class MedicationSchedule(Record, Base):
    """Immutable daily schedule snapshots; edits only close the effective interval."""
    __tablename__ = "medication_schedules"
    __table_args__ = (Index("ix_schedule_medication_effective", "medication_id", "effective_from"),)
    medication_id: Mapped[str] = mapped_column(ForeignKey("medications.id"), index=True)
    timezone: Mapped[str] = mapped_column(String(100))
    reminder_times: Mapped[list] = mapped_column(JSON)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskEvaluation(Record, Base):
    __tablename__ = "risk_evaluations"
    __table_args__ = (UniqueConstraint("checkin_id", "ruleset_hash", "checkin_version", name="uq_checkin_ruleset_revision"),)
    checkin_id: Mapped[str] = mapped_column(ForeignKey("checkins.id"), index=True)
    checkin_version: Mapped[int] = mapped_column(default=1)
    ruleset_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    details: Mapped[dict] = mapped_column(JSON)


from app.models.support import RecoveryAudit, CaregiverRelationship, CaregiverAudit
