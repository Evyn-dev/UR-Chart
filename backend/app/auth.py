import secrets
import hashlib
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models import Patient

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.sessions() as session:
        yield session


def authenticated_identity(settings, credentials):
    """Verify bearer tokens server-side, never from unverified JWT claims."""
    if not (settings.demo_auth_enabled or settings.hosted_demo_code_hash or (settings.supabase_url and settings.supabase_publishable_key)):
        raise HTTPException(503, "Authentication provider not configured")
    if not credentials:
        raise HTTPException(401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    if settings.demo_auth_enabled:
        for secret, user in settings.demo_tokens.items():
            if secrets.compare_digest(token.encode(), secret.encode()):
                return user
        raise HTTPException(401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"})

    if settings.hosted_demo_code_hash:
        # One shared, fictional demo patient. Never accept real medical data.
        supplied_code, separator, persona = token.rpartition(":")
        if not separator or persona not in {"patient", "caregiver"}:
            supplied_code, persona = token, "patient"
        digest = hashlib.sha256(supplied_code.encode("utf-8")).hexdigest()
        if secrets.compare_digest(digest, settings.hosted_demo_code_hash):
            return "synthetic-demo-caregiver" if persona == "caregiver" else "synthetic-demo-patient"
        raise HTTPException(401, "Invalid demo access code", headers={"WWW-Authenticate": "Bearer"})

    if settings.supabase_url and settings.supabase_publishable_key:
        try:
            response = httpx.get(
                settings.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": "Bearer " + token,
                },
                timeout=8,
            )
        except httpx.RequestError:
            raise HTTPException(503, "Authentication service unavailable") from None
        if response.status_code in (401, 403):
            raise HTTPException(401, "Your session has expired. Please sign in again.") from None
        if response.status_code != 200:
            raise HTTPException(503, "Authentication service unavailable")
        try:
            user_id = str(UUID(response.json()["id"]))
        except (ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(503, "Unexpected authentication response") from None
        return "supabase:" + user_id
    raise HTTPException(503, "Authentication provider not configured")


def current_patient(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    identity = authenticated_identity(request.app.state.settings, credentials)
    patient = db.scalar(select(Patient).where(Patient.user_id == identity))
    if patient is None:
        patient = Patient(user_id=identity, display_name="Synthetic patient")
        db.add(patient)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            patient = db.scalar(select(Patient).where(Patient.user_id == identity))
            if patient is None:
                raise
    return patient
