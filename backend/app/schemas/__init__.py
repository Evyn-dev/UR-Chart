from datetime import date, datetime, timezone, time
from typing import Generic, TypeVar, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator, model_validator

T = TypeVar("T")


class Data(BaseModel, Generic[T]):
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_timestamps(cls, value):
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)) if value else None


class PatientPatch(Input):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError:
                raise ValueError("Use an IANA timezone name")
        return value

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Patch fields cannot be null")
        return self


class PatientOut(RecordOut):
    display_name: str
    timezone: str


class ReminderInput(Input):
    @field_validator("reminder_times", check_fields=False)
    @classmethod
    def valid_reminders(cls, value):
        if value is None:
            return value
        if any(t.tzinfo is not None or t.second or t.microsecond for t in value):
            raise ValueError("Use local HH:MM times without offsets or fractional seconds")
        if len(set(value)) != len(value):
            raise ValueError("Reminder times must be unique")
        return sorted(value)


class MedicationCreate(ReminderInput):
    name: str = Field(min_length=1, max_length=200)
    dosage: str = Field(min_length=1, max_length=200)
    schedule: str = Field(min_length=1, max_length=300)
    active: bool = True
    reminder_times: list[time] = Field(default_factory=list, max_length=12)
    supply_remaining: int | None = Field(default=None, ge=0)
    refill_threshold: int | None = Field(default=None, ge=0)


class MedicationPatch(ReminderInput):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    dosage: str | None = Field(default=None, min_length=1, max_length=200)
    schedule: str | None = Field(default=None, min_length=1, max_length=300)
    active: bool | None = None
    reminder_times: list[time] | None = Field(default=None, max_length=12)
    supply_remaining: int | None = Field(default=None, ge=0)
    refill_threshold: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set - {"supply_remaining", "refill_threshold"}):
            raise ValueError("Patch fields cannot be null")
        return self


class MedicationOut(RecordOut):
    name: str
    dosage: str
    schedule: str
    active: bool
    reminder_times: list[time]
    supply_remaining: int | None
    refill_threshold: int | None


class LogCreate(Input):
    status: Literal["taken", "skipped", "missed"]
    recorded_at: AwareDatetime
    schedule_id: UUID | None = None
    scheduled_for: AwareDatetime | None = None
    units_used: int | None = Field(default=None, ge=1, le=100000, strict=True)

    @model_validator(mode="after")
    def validate_dose(self):
        if (self.schedule_id is None) != (self.scheduled_for is None):
            raise ValueError("schedule_id and scheduled_for must be provided together")
        if self.units_used is not None and self.status != "taken":
            raise ValueError("Only taken doses can consume supply")
        return self
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("recorded_at", "scheduled_for")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(timezone.utc) if value else None


class LogOut(RecordOut):
    version: int
    medication_id: UUID
    status: str
    recorded_at: datetime
    schedule_id: UUID | None
    scheduled_for: datetime | None
    units_used: int | None
    note: str | None

    @field_validator("recorded_at", "scheduled_for")
    @classmethod
    def utc_recorded_at(cls, value):
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)) if value else None


class SymptomReport(Input):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    present: bool = True
    severity: Literal["mild", "moderate", "severe"] | None = None
    description: str | None = Field(default=None, max_length=300)


class CheckinCreate(Input):
    day: date
    wellbeing: int | None = Field(default=None, ge=1, le=5, strict=True)
    note: str | None = Field(default=None, max_length=2000)
    pain_level: int | None = Field(default=None, ge=0, le=10, strict=True)
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    activity_minutes: int | None = Field(default=None, ge=0, le=1440, strict=True)
    activity_type: str | None = Field(default=None, min_length=1, max_length=100)
    symptom_reports: list[SymptomReport] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_partial(self):
        if not any(getattr(self, k) is not None for k in ("wellbeing", "pain_level", "activity_minutes", "note")) and not (self.symptoms or self.symptom_reports):
            raise ValueError("Provide at least one observation")
        codes = [s.code for s in self.symptom_reports]
        if len(codes) != len(set(codes)):
            raise ValueError("Symptom codes must be unique")
        return self


    @field_validator("symptoms")
    @classmethod
    def validate_symptoms(cls, value):
        if any(not symptom.strip() or len(symptom) > 120 for symptom in value):
            raise ValueError("Each symptom must contain 1–120 characters")
        return value


class CheckinOut(RecordOut):
    version: int
    day: date
    wellbeing: int | None
    note: str | None
    pain_level: int | None
    symptoms: list[str]
    activity_minutes: int | None
    activity_type: str | None
    symptom_reports: list[SymptomReport]


class AlertCreate(Input):
    category: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class AlertOut(RecordOut):
    version: int
    checkin_version: int
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    resolved_by: str | None
    resolved_at: datetime | None

    @field_validator("acknowledged_at", "resolved_at")
    @classmethod
    def lifecycle_utc(cls, value):
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)) if value else None

    severity: Literal["routine", "needs_clinical_review", "urgent", "emergency"]
    checkin_id: UUID | None
    rule_id: str | None
    rule_version: str | None
    prototype_only: bool
    evidence: dict
    notification_status: str
    category: str
    message: str
    status: str


class ChatCreate(Input):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class MessageOut(RecordOut):
    role: str
    content: str


class ConversationOut(RecordOut):
    title: str


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ChatOut(BaseModel):
    conversation_id: UUID
    user_message: MessageOut
    assistant_message: MessageOut


class MedicationAdherence(BaseModel):
    taken: int
    skipped: int
    total_logged: int
    adherence_percent: float | None
    overdue_unrecorded: int
    expected_due: int
    scheduled_taken: int
    scheduled_skipped: int
    confirmed_missed: int
    unrecorded: int
    scheduled_adherence_percent: float | None
    schedule_issues: list[dict]
    note: str = "adherence_percent is the legacy logged-event ratio. scheduled_adherence_percent uses due scheduled doses; unrecorded is unknown, not confirmed missed."


class RefillStatus(BaseModel):
    actual_supply: int | None = None
    estimated_supply: int | None = None
    estimated_days_remaining: float | None = None
    status: str = "unknown"
    message: str = "Supply information unavailable"

    medication_id: UUID
    supply_remaining: int | None
    refill_threshold: int | None
    refill_needed: bool | None
    note: str = "Supply is entered manually; this is not a pharmacy refill request."
