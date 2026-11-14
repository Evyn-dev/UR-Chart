"""Integration tests for fictional, consent-gated recovery engagement endpoints."""
from datetime import datetime, timedelta, timezone


def test_emergency_and_medical_card_are_patient_scoped(client, auth, other):
    record = client.post("/api/engagement/medical-card", headers=auth, json={
        "allergies": ["Example allergy"], "conditions": ["Example condition"], "note": "DEMO",
    })
    assert record.status_code == 200, record.text
    assert client.get("/api/engagement/medical-card", headers=auth).json()["data"]["allergies"] == ["Example allergy"]
    assert client.get("/api/engagement/medical-card", headers=other).json()["data"]["allergies"] == []

    event = client.post("/api/engagement/emergencies", headers=auth, json={
        "share_location": False, "location": "Should not be stored",
    })
    assert event.status_code == 200, event.text
    data = event.json()["data"]
    assert data["location"] is None
    assert data["notifications"][0]["sms"] == "not_configured"
    assert client.get("/api/engagement/emergencies", headers=other).json()["data"] == []
    assert client.post("/api/engagement/emergencies", headers=auth, json={}).status_code == 429


def test_accepted_caregiver_can_acknowledge_but_cannot_view_other_records(client, auth, other):
    invite = client.post("/api/caregivers/invitations", headers=auth, json={
        "caregiver_user_id": "synthetic-jordan",
        "permissions": ["alerts"],
        "alert_severities": ["emergency"],
    })
    assert invite.status_code == 201, invite.text
    rel = invite.json()["data"]
    accepted = client.post(f"/api/caregiver/invitations/{rel['id']}/respond", headers=other,
        json={"expected_version": rel["version"], "decision": "accept"})
    assert accepted.status_code == 200, accepted.text

    contact = client.post("/api/engagement/contacts", headers=auth, json={
        "relationship_id": rel["id"], "priority": 1,
        "enabled": True, "contact_name": "Fictional caregiver",
    })
    assert contact.status_code == 200, contact.text
    consent = client.post("/api/engagement/contacts/opt-in", headers=other, json={
        "relationship_id": rel["id"], "phone": "+15555550123", "consent": True,
    })
    assert consent.status_code == 200, consent.text
    emergency = client.post("/api/engagement/emergencies", headers=auth, json={})
    assert emergency.status_code == 200, emergency.text
    event = emergency.json()["data"]
    assert event["notifications"][0]["sms"] == "demo_only_not_sent"
    assert event["notifications"][0]["call"] == "demo_only_not_sent"

    caregiver_events = client.get("/api/engagement/caregiver/emergencies", headers=other)
    assert caregiver_events.status_code == 200
    assert caregiver_events.json()["data"][0]["id"] == event["id"]
    ack = client.post(f"/api/engagement/caregiver/emergencies/{event['id']}/acknowledge", headers=other)
    assert ack.status_code == 200, ack.text
    assert ack.json()["data"]["status"] == "acknowledged"
    assert client.get("/api/engagement/medical-card", headers=other).json()["data"]["allergies"] == []


def test_daily_briefing_and_visit_prep_use_saved_appointments(client, auth):
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    created = client.post("/api/engagement/appointments", headers=auth, json={
        "date_time": future, "title": "Fictional follow-up", "place": "Test clinic",
    })
    assert created.status_code == 200, created.text
    briefing = client.get("/api/engagement/daily-briefing", headers=auth)
    assert briefing.status_code == 200, briefing.text
    assert briefing.json()["data"]["upcoming_appointments"][0]["title"] == "Fictional follow-up"
    prep = client.get("/api/engagement/visit-prep", headers=auth)
    assert prep.status_code == 200, prep.text
    assert "dose_log_counts" in prep.json()["data"]
