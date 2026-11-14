"""Focused tests for recovery tracking additions. All test records are synthetic."""
from datetime import date


def test_medication_reminders_refill_and_adherence(client, auth, other):
    payload = {
        "name": "Fictional medication",
        "dosage": "Demo only",
        "schedule": "Per fictional discharge plan",
        "reminder_times": ["08:00:00", "20:00:00"],
        "supply_remaining": 4,
        "refill_threshold": 5,
    }
    res = client.post("/api/medications", headers=auth, json=payload)
    assert res.status_code == 201, res.text
    med = res.json()["data"]
    assert med["reminder_times"] == ["08:00:00", "20:00:00"]
    med_id = med["id"]
    refill = client.get(f"/api/medications/{med_id}/refill", headers=auth)
    assert refill.status_code == 200
    assert refill.json()["data"]["refill_needed"] is True
    assert client.get(f"/api/medications/{med_id}/refill", headers=other).status_code == 404
    for status in ("taken", "skipped", "taken"):
        response = client.post(
            f"/api/medications/{med_id}/log",
            headers=auth,
            json={"status": status, "recorded_at": "2026-11-13T12:00:00Z"},
        )
        assert response.status_code == 201, response.text
    summary = client.get(f"/api/medications/{med_id}/adherence", headers=auth)
    assert summary.status_code == 200
    assert summary.json()["data"]["taken"] == 2
    assert summary.json()["data"]["skipped"] == 1
    assert summary.json()["data"]["adherence_percent"] == 66.7
    assert len(client.get(f"/api/medications/{med_id}/logs", headers=auth).json()["data"]) == 3
    assert client.get(f"/api/medications/{med_id}/logs", headers=other).status_code == 404


def test_structured_checkin_and_patient_isolation(client, auth, other):
    body = {
        "day": "2026-11-13",
        "wellbeing": 3,
        "pain_level": 4,
        "symptoms": ["mild fatigue", "poor sleep"],
        "activity_minutes": 12,
        "note": "Synthetic test record",
    }
    res = client.post("/api/checkins", headers=auth, json=body)
    assert res.status_code == 201, res.text
    assert res.json()["data"]["symptoms"] == body["symptoms"]
    assert res.json()["data"]["pain_level"] == 4
    assert client.get("/api/checkins", headers=other).json()["data"] == []
    assert client.post("/api/checkins", headers=auth, json={**body, "day": "2026-11-14", "pain_level": 11}).status_code == 422
    assert client.post("/api/checkins", headers=auth, json={**body, "day": "2026-11-14", "symptoms": [" "]}).status_code == 422
