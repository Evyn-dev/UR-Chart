"""Opt-in public fictional demo sessions: no reusable code disclosed to visitors."""
from typing import Literal
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.auth import issue_public_demo_session

router = APIRouter(prefix="/demo", tags=["public fictional demo"])


class SessionRequest(BaseModel):
    role: Literal["patient", "caregiver"]


@router.post("/session")
def session(body: SessionRequest, request: Request):
    token = issue_public_demo_session(request.app.state.settings, body.role)
    return {"data": {"token": token, "role": body.role, "expires_in_seconds": 43200}}
