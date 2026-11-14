"""Full no-email hosted demo flow with fictional data and isolated test DB."""
import hashlib

from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

DEMO_CODE = "URC-" + "A" * 36
PATIENT = {"Authorization": "Bearer " + DEMO_CODE + ":patient"}
CAREGIVER = {"Authorization": "Bearer " + DEMO_CODE + ":caregiver"}


def test_full_hosted_demo_flow(database_url):
    settings = Settings(
        _env_file=None, app_env="production",
        database_url=database_url, demo_auth_enabled=False,
        hosted_demo_code_hash=hashlib.sha256(DEMO_CODE.encode()).hexdigest(),
        ai_provider="approved_instructions",
    )
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        assert health.json()["data"]["authentication"] == "demo"

        assert client.get("/api/patients/me").status_code == 401
        assert client.get("/api/patients/me", headers={"Authorization":"Bearer wrong-code:patient"}).status_code == 401
        patient_response = client.get("/api/patients/me", headers=PATIENT)
        caregiver_response = client.get("/api/patients/me", headers=CAREGIVER)
        assert patient_response.status_code == 200, patient_response.text
        assert caregiver_response.status_code == 200, caregiver_response.text
        assert patient_response.json()["data"]["id"] != caregiver_response.json()["data"]["id"]

        medication = client.post("/api/medications", headers=PATIENT, json={
            "name": "Fictional test medication", "dosage": "Sample-only dosage",
            "schedule": "Daily in demo", "reminder_times": ["09:00"],
            "supply_remaining": 12, "refill_threshold": 3
        })
        assert medication.status_code == 201, medication.text
        summary = client.get("/api/medications/summary?start=2026-11-13&end=2026-11-14", headers=PATIENT)
        assert summary.status_code == 200, summary.text
        assert len(summary.json()["data"]["medications"]) == 1
        assert client.get("/api/medications", headers=CAREGIVER).json()["data"] == []

        checkin = client.post("/api/checkins", headers=PATIENT, json={
            "day": "2026-11-14", "wellbeing": 4, "pain_level": 1,
            "note": "Synthetic demo observation"
        })
        assert checkin.status_code == 201, checkin.text
        checkin_id = checkin.json()["data"]["id"]
        assert client.get("/api/checkins?start=2026-11-13&end=2026-11-14", headers=PATIENT).status_code == 200
        assert client.get("/api/checkins/trends?start=2026-11-13&end=2026-11-14", headers=PATIENT).status_code == 200
        assert client.get(f"/api/checkins/{checkin_id}/risk", headers=PATIENT).status_code == 200
        assert client.get("/api/alerts", headers=PATIENT).status_code == 200

        chat = client.post("/api/chat/message", headers=PATIENT, json={"message": "Show my demo instructions"})
        assert chat.status_code == 201, chat.text
        assert client.get("/api/chat/conversations", headers=PATIENT).status_code == 200

        invitation = client.post("/api/caregivers/invitations", headers=PATIENT, json={
            "caregiver_user_id":"synthetic-demo-caregiver",
            "permissions":["recovery_summary","checkin_summary"],
            "alert_severities":[]
        })
        assert invitation.status_code == 201, invitation.text
        relation = invitation.json()["data"]
        assert len(client.get("/api/caregiver/invitations", headers=CAREGIVER).json()["data"]) == 1
        accepted = client.post(f"/api/caregiver/invitations/{relation['id']}/respond", headers=CAREGIVER, json={
            "decision":"accept","expected_version":relation["version"]
        })
        assert accepted.status_code == 200, accepted.text
        shared = client.get(f"/api/caregiver/relationships/{relation['id']}/dashboard", headers=CAREGIVER)
        assert shared.status_code == 200, shared.text
        assert "recovery_summary" in shared.json()["data"]
        assert client.get(f"/api/caregiver/relationships/{relation['id']}/dashboard", headers=PATIENT).status_code == 404
