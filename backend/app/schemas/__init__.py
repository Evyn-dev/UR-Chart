from datetime import date, datetime, timezone
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
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


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


class MedicationCreate(Input):
    name: str = Field(min_length=1, max_length=200)
    dosage: str = Field(min_length=1, max_length=200)
    schedule: str = Field(min_length=1, max_length=300)
    active: bool = True


class MedicationPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    dosage: str | None = Field(default=None, min_length=1, max_length=200)
    schedule: str | None = Field(default=None, min_length=1, max_length=300)
    active: bool | None = None

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Patch fields cannot be null")
        return self


class MedicationOut(RecordOut):
    name: str
    dosage: str
    schedule: str
    active: bool


class LogCreate(Input):
    status: Literal["taken", "skipped"]
    recorded_at: AwareDatetime
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("recorded_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(timezone.utc)


class LogOut(RecordOut):
    medication_id: UUID
    status: str
    recorded_at: datetime
    note: str | None

    @field_validator("recorded_at")
    @classmethod
    def utc_recorded_at(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class CheckinCreate(Input):
    day: date
    wellbeing: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)


class CheckinOut(RecordOut):
    day: date
    wellbeing: int
    note: str | None


class AlertCreate(Input):
    category: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class AlertOut(RecordOut):
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
