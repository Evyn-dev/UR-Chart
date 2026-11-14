"""Validated JSON contracts for arbitrary reminder tasks."""
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import AwareDatetime, Field, field_validator
from app.schemas import Input, RecordOut

Repeat = Literal["once", "daily", "weekdays", "weekly", "monthly"]


class ReminderCreate(Input):
    title: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=500)
    due_at: AwareDatetime
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    repeat: Repeat = "once"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Use a valid IANA timezone") from exc
        return value


class ReminderUpdate(ReminderCreate):
    expected_version: int = Field(ge=1)


class ReminderAction(Input):
    expected_version: int = Field(ge=1)
    action: Literal["complete", "dismiss", "snooze", "toggle", "delete"]


class ReminderOut(RecordOut):
    title: str
    notes: str
    due_at: datetime
    timezone: str
    repeat: Repeat
    active: bool
    version: int
    last_action: str | None
    last_action_at: datetime | None

    @field_validator("due_at", "last_action_at")
    @classmethod
    def utc(cls, value):
        if value is None:
            return value
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc))
