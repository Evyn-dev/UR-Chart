"""Regression coverage for caregiver educational editing, identity, audit, and Clara context."""
from app.models import CurriculumTask


def _relationship(client, auth, other):
    invite = client.post("/api/caregivers/invitations", headers=auth, json={
        "caregiver_user_id": "synthetic-jordan",
        "permissions": ["recovery_summary", "checkin_summary"],
        "alert_severities": [],
    })
    assert invite.status_code == 201, invite.text
    rel = invite.json()["data"]
    accepted = client.post(f"/api/caregiver/invitations/{rel['id']}/respond", headers=other,
                           json={"decision": "accept", "expected_version": rel["version"]})
    assert accepted.status_code == 200, accepted.text
    return accepted.json()["data"]


def test_caregiver_can_create_edit_archive_and_audit(client, auth, other):
    rel = _relationship(client, auth, other)
    base = f"/api/caregiver/relationships/{rel['id']}/curriculum"
    item = client.post(base, headers=other, json={
        "title": "Prepare questions", "description": "For clinician follow-up",
        "due_day": "2026-11-20", "position": 2,
    })
    assert item.status_code == 201, item.text
    task = item.json()["data"]
    assert task["version"] == 1
    assert len(client.get("/api/curriculum", headers=auth).json()["data"]) == 1
    assert client.get(base, headers=other).json()["data"][0]["id"] == task["id"]
    update = {
        "expected_version": 1, "title": "Review questions", "description": "Bring list to appointment",
        "due_day": None, "position": 1, "status": "completed",
    }
    changed = client.patch(f"{base}/{task['id']}", headers=other, json=update)
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["version"] == 2
    assert client.patch(f"{base}/{task['id']}", headers=other, json=update).status_code == 409
    history = client.get("/api/curriculum/audit", headers=auth).json()["data"]
    assert len(history) == 2
    assert history[0]["actor_user_id"] == "synthetic-jordan"
    assert history[0]["before"]["title"] == "Prepare questions"
    assert history[0]["after"]["status"] == "completed"
    assert history[1]["action"] == "created"
    assert client.get(base+"/audit", headers=other).status_code == 200
    assert client.post(base, headers=auth, json={"title":"Blocked"}).status_code == 404

    revoked = client.post(f"/api/caregivers/{rel['id']}/revoke", headers=auth,
                          json={"expected_version": rel["version"]})
    assert revoked.status_code == 200, revoked.text
    assert client.post(base, headers=other, json={"title":"Unauthorized"}).status_code == 404
    assert client.get(base, headers=other).status_code == 404
    assert client.get("/api/curriculum", headers=auth).json()["data"][0]["title"] == "Review questions"


def test_invalid_caregiver_relationship_and_cross_patient_access(client, auth, other):
    bad = "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12
    assert client.post(f"/api/caregiver/relationships/{bad}/curriculum",
                       headers=other, json={"title": "No consent"}).status_code == 404
    assert client.post("/api/caregiver/relationships/not-a-uuid/curriculum",
                       headers=other, json={"title": "No consent"}).status_code == 422


def test_clara_context_contains_patient_tasks_only(client, auth, other, app):
    rel = _relationship(client, auth, other)
    base = f"/api/caregiver/relationships/{rel['id']}/curriculum"
    created = client.post(base, headers=other, json={"title": "Discuss fatigue", "description": "Ask clinician",
                                                       "position": 0})
    assert created.status_code == 201, created.text
    class Capture:
        snapshot = None
        def respond(self, prompt, context, history):
            self.snapshot = context.patient_snapshot
            return "Fictional demo response"
    capture = Capture()
    app.state.ai = capture
    response = client.post("/api/chat/message", headers=auth, json={"message":"What is my checklist?"})
    assert response.status_code == 201, response.text
    assert "Discuss fatigue" in capture.snapshot
    assert "caregiver_managed_educational_tasks_not_clinical_orders" in capture.snapshot
    assert "Discuss fatigue" not in (client.get("/api/curriculum", headers=other).text)
