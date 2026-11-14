"""Synthetic integration cases; no rule or fixture is clinical validation."""
from datetime import datetime, date, timezone
import json
import pytest
from sqlalchemy import select, func, text
from alembic import command
from alembic.config import Config
from app.models import MedicationSchedule, RiskEvaluation, Alert, Checkin
from app.services.medications import occurrences


def medication(client, app, auth, times=None, zone="UTC"):
    client.patch("/api/patients/me", headers=auth, json={"timezone": zone})
    response = client.post("/api/medications", headers=auth, json={"name": "Synthetic medicine", "dosage": "Entered by fictional patient", "schedule": "Daily explicit demo schedule", "reminder_times": times or ["08:00", "20:00"], "supply_remaining": 5, "refill_threshold": 3})
    assert response.status_code == 201, response.text
    med = response.json()["data"]
    with app.state.sessions() as db:
        schedule = db.scalar(select(MedicationSchedule).where(MedicationSchedule.medication_id == med["id"]))
        schedule.effective_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        db.commit()
        med["schedule_id"] = schedule.id
    return med


def test_expected_doses_inventory_and_duplicate_rollback(client, app, auth, other):
    med = medication(client, app, auth)
    path = f'/api/medications/{med["id"]}'
    doses = client.get(path + "/doses?start=2026-01-02&end=2026-01-03", headers=auth).json()["data"]["doses"]
    assert len(doses) == 4
    for dose, status in zip(doses, ("taken", "skipped", "missed")):
        payload = {"schedule_id": dose["schedule_id"], "scheduled_for": dose["scheduled_for"], "status": status, "recorded_at": "2026-01-04T00:00:00Z"}
        if status == "taken":
            payload["units_used"] = 2
        response = client.post(path + "/log", headers=auth, json=payload)
        assert response.status_code == 201, response.text
        assert client.post(path + "/log", headers=auth, json=payload).status_code == 409
    summary = client.get(path + "/adherence?start=2026-01-02&end=2026-01-03", headers=auth).json()["data"]
    assert (summary["expected_due"], summary["scheduled_taken"], summary["scheduled_skipped"], summary["confirmed_missed"], summary["unrecorded"]) == (4, 1, 1, 1, 1)
    assert summary["scheduled_adherence_percent"] == 25
    refill = client.get(path + "/refill", headers=auth).json()["data"]
    assert refill["supply_remaining"] == 3 and refill["refill_needed"]
    for endpoint in ("doses?start=2026-01-02&end=2026-01-03", "adherence", "schedules", "logs", "refill"):
        assert client.get(path + "/" + endpoint, headers=other).status_code == 404


def test_schedule_changes_preserve_history_and_timezone(client, app, auth):
    med = medication(client, app, auth, zone="America/New_York")
    path = f'/api/medications/{med["id"]}'
    query = "/doses?start=2026-01-02&end=2026-01-02"
    before = client.get(path + query, headers=auth).json()["data"]
    assert before["doses"][0]["scheduled_for"] == "2026-01-02T13:00:00Z"
    client.patch(path, headers=auth, json={"reminder_times": ["09:00"]})
    client.patch("/api/patients/me", headers=auth, json={"timezone": "America/Chicago"})
    schedules = client.get(path + "/schedules", headers=auth).json()["data"]
    assert len(schedules) == 3 and schedules[-1]["timezone"] == "America/Chicago"
    assert client.get(path + query, headers=auth).json()["data"] == before
    assert client.patch(path, headers=auth, json={"active": False}).status_code == 200
    assert client.get(path + "/doses?start=2030-01-01&end=2030-01-01", headers=auth).json()["data"]["doses"] == []
    assert client.get(path + query, headers=auth).json()["data"] == before


@pytest.mark.parametrize("times", [["08:00", "08:00"], ["08:00+03:00"], ["08:00:01"], ["25:00"]])
def test_reminder_validation(client, auth, times):
    assert client.post("/api/medications", headers=auth, json={"name": "Demo", "dosage": "Demo", "schedule": "Demo", "reminder_times": times}).status_code == 422


def test_dst_is_not_silently_rescheduled():
    schedule = MedicationSchedule(id="demo", timezone="America/New_York", reminder_times=["02:30:00"], effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert list(occurrences(schedule, date(2026, 3, 8), date(2026, 3, 8)))[0]["issue"] == "nonexistent_local_time"
    schedule.reminder_times = ["01:30:00"]
    assert list(occurrences(schedule, date(2026, 11, 1), date(2026, 11, 1)))[0]["issue"] == "ambiguous_local_time"


def test_log_rejects_wrong_schedule_future_and_insufficient_supply(client, app, auth, other):
    med = medication(client, app, auth)
    other_med = medication(client, app, other)
    path = f'/api/medications/{med["id"]}'
    body = {"status": "taken", "recorded_at": "2026-01-02T08:00:00Z", "scheduled_for": "2026-01-02T08:00:00Z", "schedule_id": other_med["schedule_id"]}
    assert client.post(path + "/log", headers=auth, json=body).status_code == 404
    body["schedule_id"] = med["schedule_id"]
    assert client.post(path + "/log", headers=auth, json={**body, "units_used": 6}).status_code == 409
    assert client.post(path + "/log", headers=auth, json={**body, "scheduled_for": "2026-01-02T09:00:00Z"}).status_code == 422
    assert client.post(path + "/log", headers=auth, json={**body, "recorded_at": "2099-01-01T00:00:00Z"}).status_code == 422
    assert client.patch(path, headers=auth, json={"supply_remaining": None}).status_code == 200
    assert client.get(path + "/refill", headers=auth).json()["data"]["refill_needed"] is None


def test_partial_checkins_history_trends_and_isolation(client, auth, other):
    bodies = [{"day": "2026-01-01", "pain_level": 2}, {"day": "2026-01-02", "wellbeing": 3, "pain_level": 4, "activity_minutes": 10, "activity_type": "walking"}]
    for body in bodies:
        res = client.post("/api/checkins", headers=auth, json=body)
        assert res.status_code == 201, res.text
    id = res.json()["data"]["id"]
    trend = client.get("/api/checkins/trends?start=2026-01-01&end=2026-01-02", headers=auth).json()["data"]
    assert trend["averages"]["pain_level"] == 3
    assert trend["metric_counts"]["wellbeing"] == 1
    assert trend["first_to_last_change"]["pain_level"] == 2
    assert trend["first_to_last_change"]["wellbeing"] is None
    assert len(client.get("/api/checkins?start=2026-01-02&end=2026-01-02", headers=auth).json()["data"]) == 1
    for suffix in ("", "/risk"):
        assert client.get(f"/api/checkins/{id}{suffix}", headers=other).status_code == 404
    assert client.post(f"/api/checkins/{id}/evaluate", headers=other).status_code == 404
    assert client.get("/api/checkins/trends?start=2026-01-01&end=2026-01-02", headers=other).json()["data"]["days_recorded"] == 0


@pytest.mark.parametrize("body", [{"day": "2026-01-01"}, {"day": "2026-01-01", "pain_level": -1}, {"day": "2026-01-01", "activity_minutes": 1441}, {"day": "2026-01-01", "symptom_reports": [{"code": "a"}, {"code": "a"}]}, {"day": "2026-01-01", "symptom_reports": [{"code": "chest_pain", "severity": "unknown"}]}])
def test_checkin_validation(client, auth, body):
    assert client.post("/api/checkins", headers=auth, json=body).status_code == 422


def test_emergency_even_after_normal_checkin_and_dedup(client, app, auth, other):
    client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "wellbeing": 5})
    response = client.post("/api/checkins", headers=auth, json={"day": "2026-01-02", "wellbeing": 5, "symptom_reports": [{"code": "chest_pain"}]})
    assert response.status_code == 201, response.text
    id = response.json()["data"]["id"]
    for _ in range(3):
        response = client.post(f"/api/checkins/{id}/evaluate", headers=auth)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert len(data["alerts"]) == 1
        alert = data["alerts"][0]
        assert alert["severity"] == "emergency"
        assert "911" in alert["message"] and "not clinically validated" in alert["message"]
        assert alert["notification_status"] == "not_sent"
        assert alert["evidence"]["observations"]["symptom"]["code"] == "chest_pain"
    assert client.get("/api/alerts", headers=other).json()["data"] == []
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(RiskEvaluation).where(RiskEvaluation.checkin_id == id)) == 1


@pytest.mark.parametrize("code,expected", [("demo_routine", "routine"), ("demo_review", "needs_clinical_review"), ("demo_urgent", "urgent"), ("shortness_of_breath", "emergency"), ("unknown_symptom", "needs_clinical_review")])
def test_alert_levels_and_unknown_symptoms(client, auth, code, expected):
    res = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "symptom_reports": [{"code": code}]})
    id = res.json()["data"]["id"]
    data = client.get(f"/api/checkins/{id}/risk", headers=auth).json()["data"]
    assert data["alerts"][0]["severity"] == expected
    assert "not been clinically assessed" in data["guidance"]


def test_missing_rules_fallback_and_negative_symptom(client, app, auth, tmp_path):
    res = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "symptom_reports": [{"code": "chest_pain", "present": False}]})
    assert client.get(f'/api/checkins/{res.json()["data"]["id"]}/risk', headers=auth).json()["data"]["alerts"] == []
    app.state.settings.risk_rules_file = str(tmp_path / "missing.json")
    res = client.post("/api/checkins", headers=auth, json={"day": "2026-01-02", "symptoms": ["concerning symptom"]})
    assert res.status_code == 201
    data = client.get(f'/api/checkins/{res.json()["data"]["id"]}/risk', headers=auth).json()["data"]
    assert data["status"] == "unavailable"
    assert data["alerts"][0]["severity"] == "needs_clinical_review"
    assert "911" in data["guidance"]


def test_reviewed_trend_rule_requires_metadata_and_uses_patient_history(client, app, auth, other, tmp_path):
    from app.services.risk import Rule
    # Arbitrary synthetic numbers exercise mechanics, not a clinical rule.
    rule = {"id": "synthetic_increase", "version": "test", "prototype_only": False, "kind": "increase", "field": "pain_level", "minimum_increase": 3, "lookback_days": 2, "severity": "needs_clinical_review", "guidance": "Synthetic test rule only"}
    with pytest.raises(ValueError):
        Rule.model_validate(rule)
    rule.update(reviewed_by="synthetic-test-reviewer", review_reference="test-fixture-not-clinical-validation")
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"rules": [rule]}))
    app.state.settings.risk_rules_file = str(path)
    client.post("/api/checkins", headers=other, json={"day": "2026-01-01", "pain_level": 0})
    client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "pain_level": 2})
    res = client.post("/api/checkins", headers=auth, json={"day": "2026-01-02", "pain_level": 5})
    data = client.get(f'/api/checkins/{res.json()["data"]["id"]}/risk', headers=auth).json()["data"]
    assert data["alerts"][0]["evidence"]["observations"]["previous_value"] == 2


def test_populated_upgrade_preserves_records(tmp_path):
    from app.database import make_engine
    url = "sqlite:///" + (tmp_path / "legacy.db").as_posix()
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, "0002")
    engine = make_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO patients VALUES ('legacy-user', 'Synthetic', 'UTC', 'p', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO medications (id, patient_id, name, dosage, schedule, active, reminder_times, supply_remaining, created_at, updated_at) VALUES ('m','p','Demo','Demo','Demo',1,'[\"08:00:00\"]',5,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO checkins (id,patient_id,day,wellbeing,created_at,updated_at) VALUES ('c','p','2026-01-01',3,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO alerts (id,patient_id,category,message,status,created_at,updated_at) VALUES ('a','p','demo','demo','open',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO medication_logs (id,medication_id,status,recorded_at,created_at,updated_at) VALUES ('l','m','taken',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, "head")
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM medication_schedules")).scalar() == 1
        assert db.execute(text("SELECT wellbeing FROM checkins")).scalar() == 3
        assert db.execute(text("SELECT severity FROM alerts")).scalar() == "routine"
        assert db.execute(text("SELECT status FROM medication_logs")).scalar() == "taken"
    engine.dispose()


@pytest.mark.parametrize("contents", ['not json', '{"rules": []}', '{"rules": [{"id":"bad"}]}'])
def test_invalid_or_empty_rules_never_report_safe(client, app, auth, tmp_path, contents):
    path = tmp_path / "rules.json"
    path.write_text(contents)
    app.state.settings.risk_rules_file = str(path)
    response = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "symptom_reports": [{"code": "chest_pain"}]})
    assert response.status_code == 201
    result = client.get(f'/api/checkins/{response.json()["data"]["id"]}/risk', headers=auth).json()["data"]
    assert result["status"] == "unavailable"
    assert "911" in result["guidance"]
    assert result["alerts"][0]["notification_status"] == "not_sent"


def test_prototype_rules_forbidden_in_production():
    from app.config import Settings
    from app.services.risk import load_rules
    with pytest.raises(ValueError):
        load_rules(Settings(_env_file=None, app_env="production"))


def test_no_schedule_no_assumed_doses(client, auth):
    res = client.post("/api/medications", headers=auth, json={"name": "Demo", "dosage": "Demo", "schedule": "Twice daily text is never parsed"})
    data = client.get(f'/api/medications/{res.json()["data"]["id"]}/adherence', headers=auth).json()["data"]
    assert data["expected_due"] == 0
    assert data["scheduled_adherence_percent"] is None


def test_dst_summary_reports_incomplete_denominator(client, app, auth):
    med = medication(client, app, auth, times=["02:30"], zone="America/New_York")
    data = client.get(f'/api/medications/{med["id"]}/adherence?start=2026-03-08&end=2026-03-08', headers=auth).json()["data"]
    assert data["scheduled_adherence_percent"] is None
    assert data["schedule_issues"][0]["issue"] == "nonexistent_local_time"


def test_oversized_date_window_rejected(client, app, auth):
    med = medication(client, app, auth)
    assert client.get(f'/api/medications/{med["id"]}/doses?start=2026-01-01&end=2027-01-01', headers=auth).status_code == 422
    assert client.get('/api/checkins/trends?start=2026-01-02&end=2026-01-01', headers=auth).status_code == 422
