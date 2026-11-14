"""Idempotent, explicitly fictional UR Chart demo-patient records.

Use python -m app.seed after migrations. Never seed production or real patients.
All logins mapped to the same demo identity see the same database records.
"""
from datetime import date, timedelta
from sqlalchemy import select

from app.config import Settings
from app.database import make_engine, session_factory
from app.models import Patient, RecoveryPlan, Medication, Checkin
from app.services.medications import replace_schedule

PLACEHOLDER_PLAN = "This is fictional demonstration content. Your care team provides your recovery instructions."
PLAN_TITLE = "Fictional demo plan"
DEMO_HISTORY = """FICTIONAL TRAINING RECORD — NOT A REAL MEDICAL RECORD OR PRESCRIPTION.
Patient: Jordan Ellis (fictional adult, age 57). Example procedure: coronary artery bypass grafting (CABG) on 2026-10-29 at a fictional hospital. Example history: coronary artery disease, high blood pressure, and high cholesterol. Allergies: none documented IN THIS DEMO; this does not establish that a real person has no allergies.
The sample care team recorded uncomplicated hospital discharge on 2026-11-04. The patient reports help at home from a family member and a planned fictional follow-up visit for 2026-11-20.
FICTIONAL DISCHARGE INSTRUCTIONS (DEMO ONLY):
- Follow the written instructions from your own care team and the medication list in this demo record; do not copy these fictional treatments into real life.
- Log daily pain, energy, activity, and any symptoms in UR Chart.
- Use short, easy walks and rest breaks only as allowed by the individual's care team. Do not attempt strenuous activity or lifting until cleared by the care team.
- Keep the surgical incision clean and dry according to the discharge paperwork. Report increasing redness, drainage, fever, or worsening pain to the care team promptly.
- Bring the medication list and recorded symptoms to follow-up. Never change the dose or stop a medicine based on Clara's advice.
- For severe chest pain, major difficulty breathing, fainting/collapse, or stroke warning signs, call emergency services immediately (911 in the US).
All dates, diagnoses, instructions, medications, and symptoms above are INVENTED for product testing. There is no real treating clinician or approval. When summarizing, explicitly say the records are fictional."""

# Training examples only; these are not suggested regimens or prescriptions.
DEMO_MEDICATIONS = (
    {"name": "Aspirin (fictional demo entry)", "dosage": "81 mg — sample entry, not a prescription", "schedule": "Once daily at 09:00 (fictional discharge list)", "reminder_times": ["09:00"]},
    {"name": "Metoprolol tartrate (fictional demo entry)", "dosage": "25 mg — sample entry, not a prescription", "schedule": "Twice daily at 09:00 and 21:00 (fictional discharge list)", "reminder_times": ["09:00", "21:00"]},
    {"name": "Atorvastatin (fictional demo entry)", "dosage": "40 mg — sample entry, not a prescription", "schedule": "Once daily at 21:00 (fictional discharge list)", "reminder_times": ["21:00"]},
)
DEMO_CHECKINS = (
    {"wellbeing": 3, "pain_level": 4, "activity_minutes": 8, "activity_type": "gentle walking", "symptoms": ["fatigue"], "note": "FICTIONAL: Tired after a short walk; rested afterward."},
    {"wellbeing": 4, "pain_level": 3, "activity_minutes": 10, "activity_type": "gentle walking", "symptoms": ["fatigue"], "note": "FICTIONAL: Energy slightly improved; tracking regular rest breaks."},
    {"wellbeing": 4, "pain_level": 3, "activity_minutes": 12, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Completed a short walk without new symptoms."},
    {"wellbeing": 5, "pain_level": 2, "activity_minutes": 12, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Slept better and remembered to record symptoms."},
    {"wellbeing": 5, "pain_level": 2, "activity_minutes": 15, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Preparing questions for the example follow-up visit."},
)


def seed(settings):
    if settings.app_env not in {"development", "test"} or not (settings.demo_auth_enabled or settings.hosted_demo_code_hash):
        raise RuntimeError("Seeding requires development/test mode with demo authentication")
    # The hosted shared code authenticates as this single patient identity.
    # Local DEMO_TOKENS map their tokens to a patient identity; seed each of those too.
    identities = set(settings.demo_tokens.values()) if settings.demo_auth_enabled else set()
    if settings.hosted_demo_code_hash:
        identities.add("synthetic-demo-patient")
    if not identities:
        raise RuntimeError("No demo patient identities are configured")

    engine = make_engine(settings.database_url)
    try:
        with session_factory(engine)() as db:
            for identity in identities:
                patient = db.scalar(select(Patient).where(Patient.user_id == identity))
                if patient is None:
                    patient = Patient(user_id=identity, display_name="Jordan Ellis (fictional)", timezone="America/New_York")
                    db.add(patient)
                    db.flush()
                # Leave existing custom patient names/timezones untouched.
                plan = db.scalar(select(RecoveryPlan).where(
                    RecoveryPlan.patient_id == patient.id, RecoveryPlan.title == PLAN_TITLE
                ))
                if plan is None:
                    db.add(RecoveryPlan(
                        patient_id=patient.id, title=PLAN_TITLE,
                        approved_by="synthetic-demo-author", approved_instructions=DEMO_HISTORY,
                    ))
                elif plan.approved_instructions == PLACEHOLDER_PLAN:
                    # Upgrade only the original seed's placeholder, never a customized plan.
                    plan.approved_instructions = DEMO_HISTORY

                for entry in DEMO_MEDICATIONS:
                    exists = db.scalar(select(Medication).where(
                        Medication.patient_id == patient.id, Medication.name == entry["name"]
                    ))
                    if exists is None:
                        med = Medication(
                            patient_id=patient.id, name=entry["name"],
                            dosage=entry["dosage"], schedule=entry["schedule"],
                            active=True, reminder_times=entry["reminder_times"],
                            supply_remaining=None, refill_threshold=None,
                        )
                        db.add(med)
                        db.flush()
                        replace_schedule(db, med, patient.timezone)

                # Add sample check-ins over the five days ending today.
                # Skip days already entered by the user instead of overwriting them.
                for offset, entry in enumerate(DEMO_CHECKINS):
                    day = date.today() - timedelta(days=4 - offset)
                    exists = db.scalar(select(Checkin).where(
                        Checkin.patient_id == patient.id, Checkin.day == day
                    ))
                    if exists is None:
                        db.add(Checkin(
                            patient_id=patient.id, day=day,
                            wellbeing=entry["wellbeing"], pain_level=entry["pain_level"],
                            activity_minutes=entry["activity_minutes"], activity_type=entry["activity_type"],
                            symptoms=entry["symptoms"], symptom_reports=[], note=entry["note"],
                        ))
            db.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed(Settings())
    print("Shared fictional demo patients, sample medications, check-ins, and recovery history are ready.")
