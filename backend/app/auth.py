import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models import Patient

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.sessions() as session:
        yield session


def current_patient(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    settings = request.app.state.settings
    if not settings.demo_auth_enabled:
        raise HTTPException(503, "Authentication provider not configured")
    identity = None
    if credentials:
        for token, user in settings.demo_tokens.items():
            if secrets.compare_digest(credentials.credentials.encode(), token.encode()):
                identity = user
    if identity is None:
        raise HTTPException(401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"})
    patient = db.scalar(select(Patient).where(Patient.user_id == identity))
    if patient is None:
        patient = Patient(user_id=identity)
        db.add(patient)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            patient = db.scalar(select(Patient).where(Patient.user_id == identity))
            if patient is None:
                raise
    return patient
