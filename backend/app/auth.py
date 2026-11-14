import secrets
import hashlib
import hmac
import time
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models import Patient

bearer = HTTPBearer(auto_error=False)


PUBLIC_SESSION_PREFIX = "public-demo"
PUBLIC_SESSION_SECONDS = 12 * 60 * 60


def public_demo_secret(settings):
    # Existing private secret material stays only on the backend; never return it.
    if settings.hosted_demo_code_hash:
        return settings.hosted_demo_code_hash.encode("ascii")
    if settings.demo_auth_enabled and settings.demo_tokens:
        return sorted(settings.demo_tokens)[0].encode("utf-8")
    return None


def public_demo_identity(settings, persona):
    if persona == "caregiver":
        return "synthetic-demo-caregiver"
    if settings.hosted_demo_code_hash:
        return "synthetic-demo-patient"
    return settings.demo_tokens[sorted(settings.demo_tokens)[0]]


def issue_public_demo_session(settings, persona):
    if not settings.public_demo_enabled or settings.app_env not in {"development", "test"}:
        raise HTTPException(404, "Public demo is unavailable")
    if persona not in {"patient", "caregiver"}:
        raise HTTPException(422, "Invalid demo role")
    secret = public_demo_secret(settings)
    if not secret:
        raise HTTPException(503, "Public demo not configured")
    issued = str(int(time.time()))
    body = f"{PUBLIC_SESSION_PREFIX}.{persona}.{issued}"
    digest = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    return body + "." + digest


def verify_public_demo_session(settings, token):
    if not settings.public_demo_enabled or settings.app_env not in {"development", "test"}:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != PUBLIC_SESSION_PREFIX or parts[1] not in {"patient", "caregiver"}:
        return None
    persona, issued, provided = parts[1:]
    if not issued.isdecimal() or len(issued) > 15 or len(provided) != 64:
        return None
    now = int(time.time())
    timestamp = int(issued)
    if timestamp > now + 60 or now - timestamp > PUBLIC_SESSION_SECONDS:
        return None
    secret = public_demo_secret(settings)
    if not secret:
        return None
    body = f"{PUBLIC_SESSION_PREFIX}.{persona}.{issued}"
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        return None
    return public_demo_identity(settings, persona)



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
    public_identity = verify_public_demo_session(settings, token)
    if public_identity is not None:
        return public_identity
    if settings.demo_auth_enabled:
        # In development only, role-suffixed demo credentials let the same
        # fictional access code open a separate caregiver identity.
        # Authorization to see another patient's records still requires an
        # accepted, patient-granted CaregiverRelationship with limited scopes.
        supplied, separator, persona = token.rpartition(":")
        if not separator or persona not in {"patient", "caregiver"}:
            supplied, persona = token, "patient"
        for secret, user in settings.demo_tokens.items():
            if secrets.compare_digest(supplied.encode(), secret.encode()):
                return "synthetic-demo-caregiver" if persona == "caregiver" else user
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
