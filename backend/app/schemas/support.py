from datetime import datetime, date
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator, BaseModel, field_validator
from app.schemas import Input, RecordOut, CheckinCreate

Permission = Literal["recovery_summary", "medication_adherence", "checkin_summary", "alerts"]
Severity = Literal["routine", "needs_clinical_review", "urgent", "emergency"]


class Versioned(Input):
    expected_version: int = Field(ge=1, strict=True)


class LogCorrection(Versioned):
    status: Literal["taken", "skipped", "missed", "voided"]
    units_used: int | None = Field(default=None, ge=1, le=100000, strict=True)
    reason: str = Field(min_length=1, max_length=500)
    inventory_action: Literal["adjust", "already_reconciled"] = "adjust"

    @model_validator(mode="after")
    def units(self):
        if self.status != "taken" and self.units_used is not None:
            raise ValueError("Only taken doses consume units")
        return self


class CheckinCorrection(Versioned):
    reason: str = Field(min_length=1, max_length=500)
    observation: CheckinCreate


class AlertAction(Versioned):
    action: Literal["acknowledge", "resolve", "reopen"]
    reason: str = Field(min_length=1, max_length=500)
    emergency_guidance_seen: bool = False


class AuditOut(RecordOut):
    resource_type: str
    resource_id: str
    actor_user_id: str
    action: str
    reason: str
    before: dict
    after: dict


class CaregiverPermissions(Input):
    permissions: list[Permission] = Field(max_length=4)
    alert_severities: list[Severity] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def unique_permissions(self):
        if len(set(self.permissions)) != len(self.permissions) or len(set(self.alert_severities)) != len(self.alert_severities):
            raise ValueError("Permissions and severities must be unique")
        if bool(self.alert_severities) != ("alerts" in self.permissions):
            raise ValueError("Alert permission requires explicit nonempty alert severities")
        return self


class CaregiverInvite(CaregiverPermissions):
    caregiver_user_id: str = Field(min_length=1, max_length=255)


class CaregiverChange(CaregiverPermissions, Versioned):
    pass


class InvitationResponse(Versioned):
    decision: Literal["accept", "decline"]


class RelationshipOut(RecordOut):
    patient_id: UUID
    caregiver_user_id: str
    status: str
    permissions: list[Permission]
    alert_severities: list[Severity]
    version: int
    responded_at: datetime | None
    revoked_at: datetime | None

    @field_validator("responded_at", "revoked_at")
    @classmethod
    def utc_time(cls, value):
        from app.services.medications import utc
        return utc(value) if value else None


class CaregiverAuditOut(RecordOut):
    actor_user_id: str
    action: str
    details: dict


class CaregiverDashboard(BaseModel):
    relationship_id: UUID
    patient_display_name: str
    permissions: list[Permission]
    recovery_summary: dict | None = None
    medication_adherence: dict | None = None
    checkin_summary: dict | None = None
    alerts: list[dict] | None = None
    outstanding_tasks: list[dict] | None = None
    alerts_has_more: bool = False
    alert_visibility: str
    notification_status: str = "not_sent"


from app.schemas import MedicationOut, LogOut, MedicationAdherence, RefillStatus
from app.schemas.recovery import Dose


class SummaryDose(Dose):
    medication_id: UUID


class MedicationSummary(BaseModel):
    medications: list[MedicationOut]
    today: date
    today_doses: list[SummaryDose]
    completed_records: list[LogOut]
    unrecorded_doses: list[SummaryDose]
    refill_warnings: list[RefillStatus]
    adherence: dict[str, MedicationAdherence]
    limit: int
    offset: int
    has_more: bool
    start: date
    end: date
