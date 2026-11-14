from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.schemas import RecordOut, AlertOut


class Dose(BaseModel):
    schedule_id: UUID
    scheduled_for: datetime
    local_day: date
    local_time: str
    timezone: str
    status: Literal["taken", "skipped", "missed", "unrecorded"]
    overdue: bool
    due: bool
    log_id: UUID | None


class DoseHistory(BaseModel):
    doses: list[Dose]
    schedule_issues: list[dict]


class ScheduleOut(RecordOut):
    timezone: str
    reminder_times: list[str]
    effective_from: datetime
    effective_until: datetime | None

    @field_validator("effective_from", "effective_until")
    @classmethod
    def as_utc(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class TrendSummary(BaseModel):
    expected_days: int = 0
    missing_days: int = 0
    consistency_percent: float | None = None
    latest_comparison: dict = {}

    days_recorded: int
    metric_counts: dict[str, int]
    averages: dict[str, float | None]
    first_to_last_change: dict[str, float | None]
    note: str = "Descriptive patient-reported data only; no clinical interpretation or imputation."


class RiskResult(BaseModel):
    status: str
    prototype_only: bool
    alerts: list[AlertOut]
    historical_alerts: list[AlertOut] = []
    guidance: str
