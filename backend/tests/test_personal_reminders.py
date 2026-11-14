from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.database import make_engine
from app.services.reminders import next_due


def payload(**changes):
    return {"title": "Fictional personal task", "notes": "Demo note", "due_at": "2026-01-31T14:00:00Z",
            "timezone": "America/New_York", "repeat": "once", **changes}


def test_reminder_crud_ownership_and_stale_edits(client, auth, other):
    assert client.get("/api/reminders").status_code == 401
    created = client.post("/api/reminders", headers=auth, json=payload())
    assert created.status_code == 201, created.text
    reminder = created.json()["data"]
    path = f"/api/reminders/{reminder['id']}"
    assert client.get("/api/reminders", headers=other).json()["data"] == []
    assert client.patch(path, headers=other, json=payload(expected_version=1)).status_code == 404
    assert client.post(path+"/action", headers=other, json={"action": "complete", "expected_version": 1}).status_code == 404
    edited = client.patch(path, headers=auth, json=payload(title="Edited task", repeat="weekly", expected_version=1))
    assert edited.status_code == 200 and edited.json()["data"]["version"] == 2
    assert client.patch(path, headers=auth, json=payload(expected_version=1)).status_code == 409
    assert client.post(path+"/action", headers=auth, json={"action": "complete", "expected_version": 1}).status_code == 409
    assert client.get("/api/reminders", headers=auth).json()["data"][0]["title"] == "Edited task"
    deleted = client.post(path+"/action", headers=auth, json={"action": "delete", "expected_version": 2})
    assert deleted.status_code == 200 and deleted.json()["data"] is None
    assert client.get("/api/reminders", headers=auth).json()["data"] == []


@pytest.mark.parametrize("action", ["complete", "dismiss"])
def test_one_time_status_persists(client, auth, action):
    item = client.post("/api/reminders", headers=auth, json=payload()).json()["data"]
    path = f"/api/reminders/{item['id']}/action"
    result = client.post(path, headers=auth, json={"action": action, "expected_version": 1}).json()["data"]
    assert result["active"] is False and result["last_action"] == action
    assert result["last_action_at"].endswith("Z")
    assert client.get("/api/reminders?active=true", headers=auth).json()["data"] == []
    restored = client.post(path, headers=auth, json={"action": "toggle", "expected_version": 2}).json()["data"]
    assert restored["active"] and restored["version"] == 3


def test_recurring_completion_and_snooze_keep_original_anchor(client, auth, app):
    item = client.post("/api/reminders", headers=auth, json=payload(repeat="monthly")).json()["data"]
    path = f"/api/reminders/{item['id']}/action"
    snoozed = client.post(path, headers=auth, json={"action": "snooze", "expected_version": 1})
    assert snoozed.status_code == 200
    completed = client.post(path, headers=auth, json={"action": "complete", "expected_version": 2}).json()["data"]
    assert completed["active"] and completed["version"] == 3
    assert datetime.fromisoformat(completed["due_at"]) > datetime.now(timezone.utc)
    assert client.post(path, headers=auth, json={"action": "complete", "expected_version": 2}).status_code == 409
    from app.models.reminders import PersonalReminder
    with app.state.sessions() as db:
        record = db.get(PersonalReminder, item["id"])
        assert record.anchor_at.day == 31


@pytest.mark.parametrize("changes", [
    {"title": " "}, {"timezone": "invalid"}, {"due_at": "2026-01-01T09:00"},
    {"repeat": "hourly"}, {"patient_id": str(uuid4())}, {"title": "x"*121},
])
def test_invalid_reminders_are_rejected(client, auth, changes):
    assert client.post("/api/reminders", headers=auth, json=payload(**changes)).status_code == 422


@pytest.mark.parametrize("anchor,current,repeat,now,expected", [
    ("2026-01-31T14:00:00+00:00", "2026-02-28T14:00:00+00:00", "monthly", "2026-02-28T15:00:00+00:00", "2026-03-31T13:00:00+00:00"),
    ("2026-03-07T07:30:00+00:00", "2026-03-07T07:30:00+00:00", "daily", "2026-03-07T08:00:00+00:00", "2026-03-08T07:30:00+00:00"),
    ("2026-03-07T07:30:00+00:00", "2026-03-08T07:30:00+00:00", "daily", "2026-03-08T08:00:00+00:00", "2026-03-09T06:30:00+00:00"),
    ("2026-10-31T05:30:00+00:00", "2026-10-31T05:30:00+00:00", "daily", "2026-10-31T06:00:00+00:00", "2026-11-01T05:30:00+00:00"),
    ("2026-11-13T14:00:00+00:00", "2026-11-13T14:00:00+00:00", "weekdays", "2026-11-13T15:00:00+00:00", "2026-11-16T14:00:00+00:00"),
    ("2020-01-01T14:00:00+00:00", "2020-01-01T14:00:00+00:00", "weekly", "2026-11-14T15:00:00+00:00", "2026-11-18T14:00:00+00:00"),
])
def test_recurrence_preserves_wall_time_and_month_anchor(anchor, current, repeat, now, expected):
    item = SimpleNamespace(anchor_at=datetime.fromisoformat(anchor), due_at=datetime.fromisoformat(current), repeat=repeat, timezone="America/New_York")
    assert next_due(item, datetime.fromisoformat(now)) == datetime.fromisoformat(expected)


def test_populated_0005_upgrade_preserves_patient_data(tmp_path):
    url = "sqlite:///" + (tmp_path / "upgrade.db").as_posix()
    config = Config("alembic.ini");config.attributes["database_url"] = url
    command.upgrade(config, "0005")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO patients (id,user_id,display_name,timezone,created_at,updated_at) VALUES ('preserved','existing','Demo','UTC',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, "head");command.check(config)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT user_id FROM patients WHERE id='preserved'")) == "existing"
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006"
    engine.dispose()
