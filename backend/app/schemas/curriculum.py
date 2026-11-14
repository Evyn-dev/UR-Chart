"""Educational checklists are caregiver-managed; never clinical orders."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

TaskStatus = Literal["pending", "completed", "archived"]

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    due_day: date | None = None
    position: int = Field(default=0, ge=0, le=10000)

class TaskEdit(BaseModel):
    expected_version: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000)
    due_day: date | None
    position: int = Field(ge=0, le=10000)
    status: TaskStatus

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    title: str
    description: str
    due_day: date | None
    position: int
    status: TaskStatus
    version: int
    created_at: datetime
    updated_at: datetime

class TaskAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    actor_user_id: str
    action: str
    before: dict
    after: dict
    created_at: datetime
