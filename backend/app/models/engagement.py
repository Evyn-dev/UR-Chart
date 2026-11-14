"""Optional prototype engagement records. No real-time monitoring is implied."""
from datetime import datetime
from sqlalchemy import String, ForeignKey, Text, JSON, DateTime, Index, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models import Record, PatientRecord


class EmergencyContact(PatientRecord, Base):
    __tablename__ = "emergency_contacts"
    __table_args__ = (Index("ix_emergency_contact_priority", "patient_id", "priority"),)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("caregiver_relationships.id"), unique=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_name: Mapped[str] = mapped_column(String(100), default="Caregiver")
    phone: Mapped[str | None] = mapped_column(String(24))
    caregiver_opted_in: Mapped[bool] = mapped_column(Boolean, default=False)


class EmergencyEvent(PatientRecord, Base):
    __tablename__ = "emergency_events"
    __table_args__ = (Index("ix_emergency_event_patient", "patient_id", "created_at"),)
    status: Mapped[str] = mapped_column(String(25), default="created")
    location: Mapped[str | None] = mapped_column(String(140))
    share_location: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications: Mapped[list] = mapped_column(JSON, default=list)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaregiverNote(PatientRecord, Base):
    __tablename__ = "caregiver_notes"
    __table_args__ = (Index("ix_caregiver_note_patient", "patient_id", "created_at"),)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("caregiver_relationships.id"))
    author_user_id: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)


class PatientAppointment(PatientRecord, Base):
    __tablename__ = "patient_appointments"
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(150))
    place: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(String(500))
    __tablename__ = "patient_appointments"

class EmergencyMedicalCard(PatientRecord, Base):
    __tablename__ = "emergency_medical_cards"
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str | None] = mapped_column(String(700))
    __table_args__ = (Index("ix_emergency_card_unique_patient", "patient_id", unique=True),)
