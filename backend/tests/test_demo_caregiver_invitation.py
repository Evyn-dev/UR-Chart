"""Fictional demo invitation must be active and share all allowed recovery sections."""
from sqlalchemy import select
from app.models import CaregiverRelationship, CaregiverAudit
from app.seed import seed


def test_preaccepted_demo_invitation_is_idempotent(app, client):
    settings = app.state.settings
    settings.demo_tokens = {"x" * 40: "synthetic-demo-patient"}
    seed(settings)
    seed(settings)
    patient_headers = {"Authorization": "Bearer " + "x" * 40 + ":patient"}
    caregiver_headers = {"Authorization": "Bearer " + "x" * 40 + ":caregiver"}

    patient = client.get("/api/patients/me", headers=patient_headers).json()["data"]
    outgoing = client.get("/api/caregivers", headers=patient_headers)
    assert outgoing.status_code == 200, outgoing.text
    relation = outgoing.json()["data"][0]
    assert relation["patient_id"] == patient["id"]
    assert relation["caregiver_user_id"] == "synthetic-demo-caregiver"
    assert relation["status"] == "active"
    assert set(relation["permissions"]) == {
        "recovery_summary", "checkin_summary", "medication_adherence", "alerts"
    }
    assert len(relation["alert_severities"]) == 4

    active = client.get("/api/caregiver/relationships", headers=caregiver_headers)
    assert active.status_code == 200, active.text
    assert [r["id"] for r in active.json()["data"]] == [relation["id"]]

    summary = client.get(
        f"/api/caregiver/relationships/{relation['id']}/dashboard",
        headers=caregiver_headers,
    )
    assert summary.status_code == 200, summary.text
    result = summary.json()["data"]
    assert "recovery_summary" in result
    assert "checkin_summary" in result
    assert "medication_adherence" in result
    assert "alerts" in result
    assert len(result["checkin_summary"]["recent"]) == 7

    with app.state.sessions() as db:
        matches = db.scalars(select(CaregiverRelationship).where(
            CaregiverRelationship.patient_id == patient["id"]
        )).all()
        assert len(matches) == 1
        audits = db.scalars(select(CaregiverAudit).where(
            CaregiverAudit.relationship_id == relation["id"]
        )).all()
        actions = [audit.action for audit in audits]
        assert actions.count("invitation_created") == 1
        assert actions.count("invitation_accepted") == 1


def test_seed_reactivates_outdated_demo_invitation_with_audit(app, client):
    settings = app.state.settings
    settings.demo_tokens = {"x" * 40: "synthetic-demo-patient"}
    seed(settings)
    with app.state.sessions() as db:
        relation = db.scalar(select(CaregiverRelationship))
        relation.status = "pending"
        relation.permissions = ["recovery_summary"]
        relation.alert_severities = []
        db.commit()
    seed(settings)
    with app.state.sessions() as db:
        relation = db.scalar(select(CaregiverRelationship))
        assert relation.status == "active"
        assert len(relation.permissions) == 4
        actions = [x.action for x in db.scalars(select(CaregiverAudit).where(
            CaregiverAudit.relationship_id == relation.id
        )).all()]
        assert actions.count("demo_access_restored") == 1
