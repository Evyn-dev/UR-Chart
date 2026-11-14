"""Integration tests: shared auth, patient isolation, safety flow and recurrence."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.models.reminders import PersonalReminder
from app.services.reminders import advance_local


def test_personal_reminder_scope_and_actions(client, auth, other):
    due = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    posted = client.post("/api/reminders", headers=auth, json={
        "title": "Custom demo task", "notes": "Fictional", "due_at": due,
        "timezone": "America/New_York", "repeat": "daily"
    })
    assert posted.status_code == 201, posted.text
    item = posted.json()["data"]
    reminder_id = item["id"]
    assert item["title"] == "Custom demo task"
    assert len(client.get("/api/reminders", headers=other).json()["data"]) == 0
    not_owned = client.post(f"/api/reminders/{reminder_id}/action",
                            headers=other, json={"action": "delete"})
    assert not_owned.status_code == 404
    completed = client.post(f"/api/reminders/{reminder_id}/action",
                            headers=auth, json={"action": "complete"})
    assert completed.status_code == 200
    assert completed.json()["data"]["active"]
    assert completed.json()["data"]["due_at"] != item["due_at"]
    deleted = client.post(f"/api/reminders/{reminder_id}/action",
                          headers=auth, json={"action": "delete"})
    assert deleted.status_code == 200
    assert deleted.json()["data"] is None


def test_invalid_and_unauthorized_reminders(client, auth):
    assert client.get("/api/reminders").status_code == 401
    assert client.post("/api/reminders", headers=auth, json={
        "title": "Wrong timezone", "due_at": datetime.now(timezone.utc).isoformat(),
        "timezone": "NotAZone"
    }).status_code == 422
    assert client.post(f"/api/reminders/{uuid4()}/action",
                       headers=auth, json={"action":"complete"}).status_code == 404


def test_assistant_triage_and_separation(client, auth, other):
    assert client.post("/api/assistant/triage",
                       json={"message": "severe chest pain"}).status_code == 401
    emergency = client.post("/api/assistant/triage", headers=auth,
                            json={"message": "I have severe chest pain"}).json()["data"]
    assert emergency["emergency_mode"] is True
    assert emergency["prototype_only"] is True
    assert "911" in emergency["guidance"]
    routine = client.post("/api/assistant/triage", headers=other,
                          json={"message": "I have a question"}).json()["data"]
    assert routine["category"] == "not_classified"
    assert "does not establish" in routine["guidance"]


def test_weekday_recurrence():
    friday = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)
    monday = advance_local(friday, "weekdays")
    assert monday.weekday() == 0


def test_existing_team_chat_and_health_still_work(client, auth):
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/chat/message", headers=auth,
                       json={"message":"Show approved instructions"}).status_code == 201
