"""Patient-owned, general-purpose personal reminders."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models import Record


class PersonalReminder(Record, Base):
    __tablename__ = "personal_reminders"
    __table_args__ = (Index("ix_personal_reminders_patient_due", "patient_id", "active", "due_at"),)

    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(String(500), default="")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    repeat: Mapped[str] = mapped_column(String(20), default="once")
    active: Mapped[bool] = mapped_column(default=True)
