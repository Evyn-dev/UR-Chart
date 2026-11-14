"""Idempotently add fictional profiles and nonclinical demo instructions."""
from sqlalchemy import select
from app.config import Settings
from app.database import make_engine, session_factory
from app.models import Patient, RecoveryPlan


def seed(settings):
    if settings.app_env not in {"development", "test"} or not settings.demo_auth_enabled:
        raise RuntimeError("Seeding requires development/test mode and demo authentication")
    engine = make_engine(settings.database_url)
    try:
        with session_factory(engine)() as db:
            for identity in set(settings.demo_tokens.values()):
                patient = db.scalar(select(Patient).where(Patient.user_id == identity))
                if patient is None:
                    patient = Patient(user_id=identity, display_name="Synthetic " + identity[:80])
                    db.add(patient)
                    db.flush()
                plan = db.scalar(select(RecoveryPlan).where(RecoveryPlan.patient_id == patient.id, RecoveryPlan.title == "Fictional demo plan"))
                if plan is None:
                    db.add(RecoveryPlan(patient_id=patient.id, title="Fictional demo plan", approved_by="synthetic-demo-author", approved_instructions="This is fictional demonstration content. Your care team provides your recovery instructions."))
            db.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed(Settings())
    print("Synthetic profiles and demo plans ready.")
