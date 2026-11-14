"""Idempotent, explicitly fictional UR Chart demo-patient records.

Use python -m app.seed after migrations. Never seed production or real patients.
All logins mapped to the same demo identity see the same database records.
"""
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.config import Settings
from app.database import make_engine, session_factory
from app.models import Patient, RecoveryPlan, Medication, MedicationLog, MedicationSchedule, Checkin, Alert, PatientAppointment, EmergencyMedicalCard
from app.services.medications import replace_schedule, occurrences, utc

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
    {"wellbeing": 2, "pain_level": 5, "activity_minutes": 5, "activity_type": "slow walking", "symptoms": ["mild fatigue"], "note": "FICTIONAL: Recovering at home, took a short indoor walk and rested. No new alarming symptoms."},
    {"wellbeing": 3, "pain_level": 4, "activity_minutes": 7, "activity_type": "gentle walking", "symptoms": ["mild fatigue"], "note": "FICTIONAL: Felt tired after a short walk, used rest breaks and logged medications."},
    {"wellbeing": 3, "pain_level": 4, "activity_minutes": 8, "activity_type": "gentle walking", "symptoms": ["fatigue"], "note": "FICTIONAL: Tired after a short walk; rested afterward."},
    {"wellbeing": 4, "pain_level": 3, "activity_minutes": 10, "activity_type": "gentle walking", "symptoms": ["fatigue"], "note": "FICTIONAL: Energy slightly improved; tracking regular rest breaks."},
    {"wellbeing": 4, "pain_level": 3, "activity_minutes": 12, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Completed a short walk without new symptoms."},
    {"wellbeing": 5, "pain_level": 2, "activity_minutes": 12, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Slept better and remembered to record symptoms."},
    {"wellbeing": 5, "pain_level": 2, "activity_minutes": 15, "activity_type": "gentle walking", "symptoms": [], "note": "FICTIONAL: Preparing questions for the example follow-up visit."},
)
WEEK_PLAN_TITLE = "Fictional week-long progress and follow-up (demo)"
WEEK_PLAN = """FICTIONAL TRAINING DATA ONLY. This is a seven-day sample record, not medical instructions from a real care team.
Jordan Ellis's demo recovery week includes daily symptom, pain, energy and activity check-ins; a sample medication schedule and dose log; and a simulated safety-center follow-up notice.
The fictional caregiver at home can be invited via Caregiver access, but sharing is NOT automatic. A caregiver must accept a patient-issued invitation before viewing selected summaries.
Example follow-up: patient plans to discuss sleep, fatigue, comfortable walking, surgical-site care, and medicine questions at a fictional 2026-11-20 visit. There is no real appointment scheduling feature connected to the demo.
Example care-team messaging is not connected; any appointment date or communication mentioned here is part of the fictional narrative only.
No live medical monitoring, automatic outreach, or clinician review occurs. If real symptoms are concerning, follow the person's actual discharge paperwork and contact their care team. For life-threatening symptoms call emergency services (911 in the USA).
Everything in this entry is synthetic; do not use it to make real treatment decisions."""


def backfill_schedule(db, medication, patient, first_day):
    """Add only the missing historical interval for this explicitly seeded medication."""
    schedules = db.scalars(select(MedicationSchedule).where(
        MedicationSchedule.medication_id == medication.id
    ).order_by(MedicationSchedule.effective_from)).all()
    start = datetime.combine(first_day, time.min, ZoneInfo(patient.timezone)).astimezone(timezone.utc)
    if not schedules:
        # Normally created by replace_schedule, but handle a partially seeded demo.
        replace_schedule(db, medication, patient.timezone)
        schedules = db.scalars(select(MedicationSchedule).where(
            MedicationSchedule.medication_id == medication.id
        ).order_by(MedicationSchedule.effective_from)).all()
    earliest = schedules[0]
    if utc(earliest.effective_from) > start:
        db.add(MedicationSchedule(
            medication_id=medication.id, timezone=patient.timezone,
            reminder_times=list(medication.reminder_times),
            effective_from=start, effective_until=utc(earliest.effective_from),
        ))
        db.flush()
    return db.scalars(select(MedicationSchedule).where(
        MedicationSchedule.medication_id == medication.id
    )).all()


def seed_dose_history(db, medication, patient, first_day, today, current_time):
    # Check-in and dose data are synthetic. Do not edit existing logs, supply, or schedules.
    schedules = backfill_schedule(db, medication, patient, first_day)
    prior = set(db.scalars(select(MedicationLog.scheduled_for).where(
        MedicationLog.medication_id == medication.id,
        MedicationLog.scheduled_for.is_not(None),
    )).all())
    prior = {utc(t) for t in prior}
    for schedule in schedules:
        for item in occurrences(schedule, first_day, today):
            if "issue" in item:
                continue
            due = item["scheduled_for"]
            if due in prior or due > current_time:
                continue
            day_index = (item["local_day"] - first_day).days
            # Show realistic variation without implying an unrecorded dose was missed.
            # Every scheduled occurrence before now gets an explicit fictional status.
            if day_index == 1 and item["local_time"] == "21:00" and medication.name.startswith("Metoprolol"):
                status = "skipped"
            elif day_index == 3 and item["local_time"] == "09:00" and medication.name.startswith("Aspirin"):
                status = "missed"
            else:
                status = "taken"
            recorded = min(due + timedelta(minutes=12), current_time)
            db.add(MedicationLog(
                medication_id=medication.id,
                status=status, scheduled_for=due, schedule_id=item["schedule_id"],
                recorded_at=recorded, units_used=None,
                note="FICTIONAL demo dose record; never interpret as evidence of actual adherence.",
                inventory_revision=medication.inventory_revision,
            ))
            prior.add(due)


def seed_sample_alert(db, patient, day):
    """One visibly non-clinical safety-center example, not an emergency trigger."""
    rule_id = "synthetic-demo-followup-week"
    existing = db.scalar(select(Alert).where(
        Alert.patient_id == patient.id, Alert.rule_id == rule_id
    ))
    if existing is None:
        db.add(Alert(
            patient_id=patient.id, category="recovery_safety",
            severity="needs_clinical_review", status="open", prototype_only=True,
            rule_id=rule_id, rule_version="1",
            message="FICTIONAL DEMO ONLY: Review the patient's recorded fatigue and questions at the sample follow-up. This is not a clinical assessment or a real notification.",
            evidence={"source":"synthetic_seed","sample_day":day.isoformat()},
            notification_status="not_sent",
        ))


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
                week_plan = db.scalar(select(RecoveryPlan).where(
                    RecoveryPlan.patient_id == patient.id, RecoveryPlan.title == WEEK_PLAN_TITLE
                ))
                if week_plan is None:
                    db.add(RecoveryPlan(patient_id=patient.id, title=WEEK_PLAN_TITLE,
                        approved_by="synthetic-demo-author", approved_instructions=WEEK_PLAN))
                now_local = datetime.now(ZoneInfo(patient.timezone))
                today = now_local.date()
                first_day = today - timedelta(days=6)
                current_time = datetime.now(timezone.utc)

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
                    else:
                        med = exists
                    # Backfill the last week of dose events, including existing demo medications.
                    if med.active and med.reminder_times:
                        seed_dose_history(db, med, patient, first_day, today, current_time)

                # Fill seven days ending today, without overwriting user-entered check-ins.
                for offset, entry in enumerate(DEMO_CHECKINS):
                    day = first_day + timedelta(days=offset)
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
                seed_sample_alert(db, patient, today)
                demo_card = db.scalar(select(EmergencyMedicalCard).where(
                    EmergencyMedicalCard.patient_id == patient.id))
                if demo_card is None:
                    db.add(EmergencyMedicalCard(patient_id=patient.id,
                        allergies=["Not documented in this fictional record"],
                        conditions=["Coronary artery disease (fictional)", "High blood pressure (fictional)",
                                    "High cholesterol (fictional)", "CABG surgery 2026-10-29 (fictional)"],
                        note="Entirely fictional demonstration data. Confirm all actual allergies and conditions with the treating care team."))
                # Add one future fictional visit in the new appointments view when applicable.
                planned_visit = datetime(2026, 11, 20, 10, 0, tzinfo=ZoneInfo(patient.timezone)).astimezone(timezone.utc)
                if planned_visit > current_time:
                    existing_visit = db.scalar(select(PatientAppointment).where(
                        PatientAppointment.patient_id == patient.id,
                        PatientAppointment.title == "Fictional post-discharge follow-up",
                    ))
                    if existing_visit is None:
                        db.add(PatientAppointment(
                            patient_id=patient.id, date_time=planned_visit,
                            title="Fictional post-discharge follow-up",
                            place="Example cardiology clinic (not a real booking)",
                            notes="DEMO ONLY: Bring recorded symptoms, medication list, and questions.",
                        ))
            db.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed(Settings())
    print("Shared fictional demo patients: seven days of check-ins and medication logs, recovery plans and sample alert ready.")
