"""Validate or populate ONLY the fictional UR Chart presentation patient.

Run after Alembic upgrade:
    python -m app.presentation_demo --seed
    python -m app.presentation_demo --check

Never handles real medical records, prints access codes, or changes Cloudflare.
"""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from app.config import Settings
from app.database import make_engine, session_factory
from app.models import (
    Patient, RecoveryPlan, Medication, MedicationLog, Checkin,
    Alert, CaregiverRelationship, CurriculumTask,
)
from app.seed import seed

PATIENT_IDENTITY = "synthetic-demo-patient"
CAREGIVER_IDENTITY = "synthetic-demo-caregiver"
SCOPES = {"recovery_summary", "checkin_summary", "medication_adherence", "alerts"}
SEVERITIES = {"routine", "needs_clinical_review", "urgent", "emergency"}


def verify(settings):
    problems = []
    engine = make_engine(settings.database_url, database_schema=settings.database_schema)
    try:
        with session_factory(engine)() as db:
            patient = db.scalar(select(Patient).where(Patient.user_id == PATIENT_IDENTITY))
            if patient is None:
                return ["Fictional presentation patient is not present"]
            today = datetime.now(ZoneInfo(patient.timezone)).date()
            days = {today - timedelta(days=n) for n in range(7)}
            rows = db.scalars(select(Checkin).where(
                Checkin.patient_id == patient.id, Checkin.day.in_(days)
            )).all()
            if {r.day for r in rows} != days:
                problems.append(f"Seven-day recovery graph incomplete ({len(rows)}/7 check-ins)")
            if not all(row.pain_level is not None and row.wellbeing is not None and
                       row.activity_minutes is not None for row in rows):
                problems.append("Some recovery graph values are missing")
            medications = db.scalars(select(Medication).where(
                Medication.patient_id == patient.id,
                Medication.active.is_(True)
            )).all()
            if len(medications) < 3:
                problems.append(f"Not enough fictional medication records ({len(medications)}/3)")
            if medications:
                dose_count = db.scalar(select(func.count()).select_from(MedicationLog).where(
                    MedicationLog.medication_id.in_([m.id for m in medications])
                ))
                if not dose_count:
                    problems.append("Fictional dose history is empty")
            if not db.scalar(select(RecoveryPlan).where(RecoveryPlan.patient_id == patient.id)):
                problems.append("Fictional discharge instructions are missing")
            alerts = db.scalars(select(Alert).where(Alert.patient_id == patient.id,
                Alert.category == "recovery_safety")).all()
            if not alerts:
                problems.append("Fictional alert example is missing")
            rel = db.scalar(select(CaregiverRelationship).where(
                CaregiverRelationship.patient_id == patient.id,
                CaregiverRelationship.caregiver_user_id == CAREGIVER_IDENTITY,
            ))
            if rel is None or rel.status != "active":
                problems.append("Accepted demo caregiver invitation is missing")
            elif set(rel.permissions) != SCOPES or set(rel.alert_severities) != SEVERITIES:
                problems.append("Demo caregiver lacks complete sharing permissions")
            tasks = db.scalars(select(CurriculumTask).where(
                CurriculumTask.patient_id == patient.id, CurriculumTask.status != "archived"
            )).all()
            if len(tasks) < 3:
                problems.append(f"Recovery checklist incomplete ({len(tasks)}/3 tasks)")
    finally:
        engine.dispose()
    return problems


def main():
    parser = argparse.ArgumentParser(description="Fictional presentation data only")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seed", action="store_true", help="Fill missing fictional records, then verify")
    mode.add_argument("--check", action="store_true", help="Only verify fictional records; no writes")
    args = parser.parse_args()
    settings = Settings()
    if not settings.hosted_demo_code_hash:
        raise SystemExit("This command requires HOSTED_DEMO_CODE_HASH (hashed shared demo login).")
    if args.seed:
        if settings.app_env not in {"development", "test", "production"}:
            raise SystemExit("Unsupported application environment.")
        # Only add missing fictional records; never overwrite patient-entered check-ins.
        seed(settings, presentation_demo=True)
    problems = verify(settings)
    if problems:
        for problem in problems:
            print("NOT READY:", problem)
        raise SystemExit(1)
    print("READY: fictional Jordan Ellis patient, 7-day trends, medications, dose logs,")
    print("       alerts, accepted caregiver with all sharing categories, checklist and Clara context.")
    print("This verifies the database only. Use caregiver login to confirm the browser display.")


if __name__ == "__main__":
    main()
