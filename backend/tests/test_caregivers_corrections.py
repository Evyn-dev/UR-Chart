"""Synthetic patients only. Consent, corrections, and bounded-query regressions."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, event, text
from app.models import MedicationSchedule, Patient, MedicationLog, RiskEvaluation, Alert
from app.services import summaries


@pytest.fixture
def third(app):
    app.state.settings.demo_tokens = {**app.state.settings.demo_tokens, "c" * 40: "synthetic-taylor"}
    return {"Authorization": "Bearer " + "c" * 40}


def med_and_log(client, app, auth):
    medication = client.post("/api/medications", headers=auth, json={"name": "Synthetic", "dosage": "Demo", "schedule": "Demo daily", "reminder_times": ["08:00"], "supply_remaining": 10, "refill_threshold": 8}).json()["data"]
    with app.state.sessions() as db:
        schedule = db.scalar(select(MedicationSchedule).where(MedicationSchedule.medication_id == medication["id"]))
        schedule.effective_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        db.commit()
        schedule_id = schedule.id
    log = client.post(f'/api/medications/{medication["id"]}/log', headers=auth, json={"status": "taken", "recorded_at": "2026-01-02T08:00:00Z", "scheduled_for": "2026-01-02T08:00:00Z", "schedule_id": schedule_id, "units_used": 2})
    assert log.status_code == 201, log.text
    return medication["id"], log.json()["data"]


def invite(client, auth, permissions=None, severities=None):
    response = client.post("/api/caregivers/invitations", headers=auth, json={"caregiver_user_id": "synthetic-jordan", "permissions": permissions or ["recovery_summary"], "alert_severities": severities or []})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def accept(client, other, relationship):
    response = client.post(f'/api/caregiver/invitations/{relationship["id"]}/respond', headers=other, json={"decision": "accept", "expected_version": relationship["version"]})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_log_correction_reversal_audit_and_duplicate_slot(client, app, auth, other):
    med, log = med_and_log(client, app, auth)
    path = f'/api/medications/{med}/logs/{log["id"]}'
    body = {"expected_version": 1, "status": "voided", "reason": "Synthetic accidental tap"}
    assert client.patch(path, headers=other, json=body).status_code == 404
    response = client.patch(path, headers=auth, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["version"] == 2
    assert client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]["actual_supply"] == 10
    assert client.patch(path, headers=auth, json=body).status_code == 409
    audit = client.get(path + "/audit", headers=auth).json()["data"]
    assert len(audit) == 1 and audit[0]["before"]["status"] == "taken" and audit[0]["after"]["status"] == "voided"
    assert client.get(path + "/audit", headers=other).status_code == 404
    data = client.get(f"/api/medications/{med}/adherence?start=2026-01-02&end=2026-01-02", headers=auth).json()["data"]
    assert data["unrecorded"] == 1 and data["overdue_unrecorded"] == 1 and data["scheduled_taken"] == 0
    assert client.patch(path, headers=auth, json={"expected_version": 2, "status": "taken", "units_used": 1, "reason": "Correct entry"}).status_code == 200
    assert client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]["actual_supply"] == 9


def test_inventory_reconciliation_and_negative_prevention(client, app, auth):
    med, log = med_and_log(client, app, auth)
    path = f'/api/medications/{med}/logs/{log["id"]}'
    body = {"expected_version": 1, "status": "taken", "units_used": 50, "reason": "Wrong units"}
    assert client.patch(path, headers=auth, json=body).status_code == 409
    assert client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]["actual_supply"] == 8
    client.patch(f"/api/medications/{med}", headers=auth, json={"supply_remaining": 20})
    body = {"expected_version": 1, "status": "voided", "reason": "Reconciled count includes correction"}
    assert client.patch(path, headers=auth, json=body).status_code == 409
    assert client.patch(path, headers=auth, json={**body, "inventory_action": "already_reconciled"}).status_code == 200
    assert client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]["actual_supply"] == 20


def test_checkin_correction_audit_trends_and_emergency_preservation(client, auth, other):
    checkin = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "pain_level": 2}).json()["data"]
    path = f'/api/checkins/{checkin["id"]}'
    body = {"expected_version": 1, "reason": "Add omitted symptom", "observation": {"day": "2026-01-01", "pain_level": 3, "symptom_reports": [{"code": "chest_pain"}]}}
    assert client.patch(path, headers=other, json=body).status_code == 404
    response = client.patch(path, headers=auth, json=body)
    assert response.status_code == 200, response.text
    assert client.patch(path, headers=auth, json=body).status_code == 409
    alerts = client.get(path + "/risk", headers=auth).json()["data"]["alerts"]
    assert len(alerts) == 1 and alerts[0]["severity"] == "emergency" and alerts[0]["checkin_version"] == 2
    body.update(expected_version=2, observation={"day": "2026-01-01", "pain_level": 1}, reason="Correct synthetic symptom")
    assert client.patch(path, headers=auth, json=body).status_code == 200
    revised_risk = client.get(path + "/risk", headers=auth).json()["data"]
    assert revised_risk["alerts"] == []
    assert len(revised_risk["historical_alerts"]) == 1
    assert revised_risk["historical_alerts"][0]["checkin_version"] == 2
    assert len(client.get(path + "/audit", headers=auth).json()["data"]) == 2
    assert client.get(path + "/audit", headers=other).status_code == 404
    trend = client.get("/api/checkins/trends?start=2026-01-01&end=2026-01-02", headers=auth).json()["data"]
    assert trend["averages"]["pain_level"] == 1 and trend["consistency_percent"] == 50 and trend["missing_days"] == 1
    for _ in range(2):
        assert client.post(path + "/evaluate", headers=auth).status_code == 200
    repeated_risk = client.get(path + "/risk", headers=auth).json()["data"]
    assert repeated_risk["alerts"] == []
    assert len(repeated_risk["historical_alerts"]) == 1


def test_alert_actions_emergency_confirmation_and_audit(client, auth, other):
    record = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "symptom_reports": [{"code": "chest_pain"}]}).json()["data"]
    alert = client.get(f'/api/checkins/{record["id"]}/risk', headers=auth).json()["data"]["alerts"][0]
    path = f'/api/alerts/{alert["id"]}'
    body = {"expected_version": 1, "action": "acknowledge", "reason": "Read guidance"}
    assert client.post(path + "/actions", headers=other, json=body).status_code == 404
    result = client.post(path + "/actions", headers=auth, json=body).json()["data"]
    assert result["acknowledged_by"] == "synthetic-alex" and result["acknowledged_at"].endswith("Z")
    body.update(expected_version=2, action="resolve")
    assert client.post(path + "/actions", headers=auth, json=body).status_code == 422
    response = client.post(path + "/actions", headers=auth, json={**body, "emergency_guidance_seen": True})
    assert response.status_code == 200 and response.json()["data"]["resolved_by"] == "synthetic-alex"
    assert "911" in response.json()["data"]["message"]
    assert len(client.get(path + "/audit", headers=auth).json()["data"]) == 2
    assert client.get("/api/alerts", headers=auth).json()["data"][0]["status"] == "resolved"


def test_invite_accept_scopes_revoke_and_audit(client, auth, other, third):
    relationship = invite(client, auth)
    path = f'/api/caregiver/relationships/{relationship["id"]}/dashboard'
    assert client.get(path, headers=other).status_code == 404
    assert client.post(f'/api/caregiver/invitations/{relationship["id"]}/respond', headers=third, json={"decision": "accept", "expected_version": 1}).status_code == 404
    assert len(client.get("/api/caregiver/invitations", headers=other).json()["data"]) == 1
    assert client.get("/api/caregiver/invitations", headers=third).json()["data"] == []
    active = accept(client, other, relationship)
    response = client.get(path, headers=other)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    data = response.json()["data"]
    assert "recovery_summary" in data and "checkin_summary" not in data and "medication_adherence" not in data and "alerts" not in data
    assert data["notification_status"] == "not_sent"
    assert client.get(path, headers=third).status_code == 404
    assert client.post(f'/api/caregivers/{active["id"]}/revoke', headers=other, json={"expected_version": 2}).status_code == 404
    assert client.post(f'/api/caregivers/{active["id"]}/revoke', headers=auth, json={"expected_version": 2}).status_code == 200
    assert client.get(path, headers=other).status_code == 404
    assert client.get("/api/caregiver/relationships", headers=other).json()["data"] == []
    events = client.get(f'/api/caregivers/{active["id"]}/audit', headers=auth).json()["data"]
    assert {e["action"] for e in events} >= {"invitation_created", "invitation_accepted", "access_granted", "dashboard_viewed", "access_revoked"}
    assert client.get(f'/api/caregivers/{active["id"]}/audit', headers=other).status_code == 404
    assert "Bearer" not in str(events)


def test_decline_reinvite_and_pending_revoke(client, auth, other):
    relationship = invite(client, auth)
    response = client.post(f'/api/caregiver/invitations/{relationship["id"]}/respond', headers=other, json={"decision": "decline", "expected_version": 1})
    assert response.json()["data"]["status"] == "declined"
    relationship = invite(client, auth)
    assert relationship["version"] == 3
    assert client.post(f'/api/caregivers/{relationship["id"]}/revoke', headers=auth, json={"expected_version": 3}).status_code == 200
    assert client.post(f'/api/caregiver/invitations/{relationship["id"]}/respond', headers=other, json={"decision": "accept", "expected_version": 4}).status_code == 409


def test_permission_changes_minimize_data_and_hide_unselected_alerts(client, auth, other):
    today = datetime.now(timezone.utc).date().isoformat()
    client.post("/api/checkins", headers=auth, json={"day": today, "pain_level": 2, "note": "PRIVATE NOTE", "symptom_reports": [{"code": "chest_pain"}, {"code": "demo_routine"}]})
    relationship = accept(client, other, invite(client, auth, ["alerts"], ["emergency"]))
    path = f'/api/caregiver/relationships/{relationship["id"]}/dashboard'
    response = client.get(path, headers=other)
    data = response.json()["data"]
    assert len(data["alerts"]) == 1 and data["alerts"][0]["severity"] == "emergency"
    assert "PRIVATE NOTE" not in response.text and "evidence" not in response.text and "chest_pain" not in response.text
    body = {"expected_version": 2, "permissions": ["checkin_summary"], "alert_severities": []}
    assert client.patch(f'/api/caregivers/{relationship["id"]}/permissions', headers=auth, json=body).status_code == 200
    data = client.get(path, headers=other).json()["data"]
    assert "alerts" not in data and data["checkin_summary"]["recent"][0]["pain_level"] == 2
    assert client.patch(f'/api/caregivers/{relationship["id"]}/permissions', headers=auth, json=body).status_code == 409
    assert client.patch(f'/api/caregivers/{relationship["id"]}/permissions', headers=auth, json={"expected_version": 3, "permissions": [], "alert_severities": []}).status_code == 200
    assert client.get(path, headers=other).status_code == 403


@pytest.mark.parametrize("body", [
    {"caregiver_user_id": "synthetic-alex", "permissions": ["recovery_summary"]},
    {"caregiver_user_id": "unknown", "permissions": ["recovery_summary"]},
    {"caregiver_user_id": "synthetic-jordan", "permissions": ["chat"]},
    {"caregiver_user_id": "synthetic-jordan", "permissions": ["alerts"]},
    {"caregiver_user_id": "synthetic-jordan", "permissions": [], "alert_severities": ["emergency"]},
])
def test_invalid_invitations(client, auth, body):
    assert client.post("/api/caregivers/invitations", headers=auth, json=body).status_code == 422


def test_caregiver_cannot_use_patient_write_endpoints(client, app, auth, other):
    med, log = med_and_log(client, app, auth)
    accept(client, other, invite(client, auth, ["medication_adherence"]))
    assert client.patch(f'/api/medications/{med}', headers=other, json={"active": False}).status_code == 404
    assert client.patch(f'/api/medications/{med}/logs/{log["id"]}', headers=other, json={"expected_version": 1, "status": "voided", "reason": "Unauthorized"}).status_code == 404
    dashboard = client.get("/api/caregiver/relationships", headers=other).json()["data"][0]
    data = client.get(f'/api/caregiver/relationships/{dashboard["id"]}/dashboard', headers=other).json()["data"]
    assert "medication_adherence" in data and "Synthetic" in str(data["medication_adherence"])


def test_summary_queries_are_batched_and_refill_is_not_estimated_inventory(client, app, auth):
    med, log = med_and_log(client, app, auth)
    counts = []
    def measure():
        with app.state.sessions() as db:
            patient = db.scalar(select(Patient))
            statements = []
            def track(conn, cursor, statement, params, context, many):
                if statement.startswith("SELECT"):
                    statements.append(statement)
            event.listen(db.bind, "before_cursor_execute", track)
            try:
                result = summaries.medication_summary(db, patient)
                counts.append(len(statements))
            finally:
                event.remove(db.bind, "before_cursor_execute", track)
            return result
    measure()
    for i in range(4):
        client.post("/api/medications", headers=auth, json={"name": f"Demo {i}", "dosage": "Demo", "schedule": "Demo", "reminder_times": ["08:00"]})
    result = measure()
    assert counts == [4, 4]
    assert len(result["medications"]) == 5
    response = client.get("/api/medications/summary?limit=2", headers=auth)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["has_more"]
    refill = client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]
    assert refill["actual_supply"] == 8 and refill["estimated_supply"] is None and refill["status"] == "refill_warning"


def test_authenticated_routes_and_invalid_limits(client, auth):
    for path in ("/api/caregivers", "/api/caregiver/invitations", "/api/caregiver/relationships", "/api/medications/summary"):
        assert client.get(path).status_code == 401
        assert client.get(path + "?limit=0", headers=auth).status_code == 422


def test_invitation_duplicates_and_permissions_do_not_cross_patients(client, auth, other, third):
    first = invite(client, auth)
    assert client.post("/api/caregivers/invitations", headers=auth, json={"caregiver_user_id": "synthetic-jordan", "permissions": ["alerts"], "alert_severities": ["emergency"]}).status_code == 409
    second = invite(client, third, ["checkin_summary"])
    first, second = accept(client, other, first), accept(client, other, second)
    data = client.get(f'/api/caregiver/relationships/{first["id"]}/dashboard', headers=other).json()["data"]
    assert "checkin_summary" not in data
    data = client.get(f'/api/caregiver/relationships/{second["id"]}/dashboard', headers=other).json()["data"]
    assert "recovery_summary" not in data
    assert client.patch(f'/api/caregivers/{first["id"]}/permissions', headers=third, json={"expected_version": 2, "permissions": ["checkin_summary"]}).status_code == 404


def test_stale_log_edit_rolls_back_inventory_and_audit(client, app, auth):
    med, log = med_and_log(client, app, auth)
    path = f'/api/medications/{med}/logs/{log["id"]}'
    assert client.patch(path, headers=auth, json={"expected_version": 1, "status": "taken", "units_used": 1, "reason": "First correction"}).status_code == 200
    assert client.patch(path, headers=auth, json={"expected_version": 1, "status": "voided", "reason": "Stale correction"}).status_code == 409
    assert client.get(f"/api/medications/{med}/refill", headers=auth).json()["data"]["actual_supply"] == 9
    assert len(client.get(path + "/audit", headers=auth).json()["data"]) == 1


def test_checkin_cannot_change_day_or_omit_all_observations(client, auth):
    record = client.post("/api/checkins", headers=auth, json={"day": "2026-01-01", "pain_level": 2}).json()["data"]
    for observation in ({"day": "2026-01-02", "pain_level": 2}, {"day": "2026-01-01"}):
        assert client.patch(f'/api/checkins/{record["id"]}', headers=auth, json={"expected_version": 1, "reason": "Demo", "observation": observation}).status_code == 422
    assert client.get(f'/api/checkins/{record["id"]}', headers=auth).json()["data"]["version"] == 1


def test_correction_can_trigger_same_rule_again_without_duplicate_processing(client, app, auth):
    observation = {"day": "2026-01-01", "symptom_reports": [{"code": "chest_pain"}]}
    record = client.post("/api/checkins", headers=auth, json=observation).json()["data"]
    path = f'/api/checkins/{record["id"]}'
    response = client.patch(path, headers=auth, json={"expected_version": 1, "reason": "Added pain score", "observation": {**observation, "pain_level": 3}})
    assert response.status_code == 200
    client.post(path + "/evaluate", headers=auth)
    risk_result = client.get(path + "/risk", headers=auth).json()["data"]
    assert len(risk_result["alerts"]) == 1
    assert risk_result["alerts"][0]["checkin_version"] == 2
    assert len(risk_result["historical_alerts"]) == 1
    assert risk_result["historical_alerts"][0]["checkin_version"] == 1


def test_supply_forecast_uses_only_confirmed_units(client, app, auth):
    from app.models import Medication
    from app.services.summaries import refill
    med, log = med_and_log(client, app, auth)
    with app.state.sessions() as db:
        medication = db.get(Medication, med)
        result = refill(db, medication, datetime(2026, 1, 3, tzinfo=timezone.utc))
        assert result["actual_supply"] == 8
        assert result["estimated_days_remaining"] == 56
    client.patch(f'/api/medications/{med}/logs/{log["id"]}', headers=auth, json={"expected_version": 1, "status": "skipped", "reason": "Wrong status"})
    with app.state.sessions() as db:
        result = refill(db, db.get(Medication, med), datetime(2026, 1, 3, tzinfo=timezone.utc))
        assert result["actual_supply"] == 10 and result["estimated_days_remaining"] is None


def test_populated_0004_upgrade_preserves_existing_alerts_and_logs(tmp_path):
    from alembic import command
    from alembic.config import Config
    from app.database import make_engine
    config = Config("alembic.ini")
    url = "sqlite:///" + (tmp_path / "upgrade.db").as_posix()
    config.attributes["database_url"] = url
    command.upgrade(config, "0004")
    engine = make_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO patients VALUES ('legacy','Synthetic','UTC','p',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO medications (id,patient_id,name,dosage,schedule,active,reminder_times,created_at,updated_at) VALUES ('m','p','Demo','Demo','Demo',1,'[]',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO medication_logs (id,medication_id,status,recorded_at,created_at,updated_at) VALUES ('l','m','taken',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO checkins (id,patient_id,day,wellbeing,created_at,updated_at) VALUES ('c','p','2026-01-01',3,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO alerts (id,patient_id,category,message,status,checkin_id,rule_id,rule_version,created_at,updated_at) VALUES ('a','p','recovery_safety','Demo','open','c','demo','1',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO risk_evaluations (id,checkin_id,ruleset_hash,status,details,created_at,updated_at) VALUES ('r','c','test','prototype_evaluated','{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, "head")
    command.check(config)
    with engine.connect() as db:
        assert db.execute(text("SELECT version FROM medication_logs")).scalar() == 1
        assert db.execute(text("SELECT checkin_version FROM alerts")).scalar() == 1
        assert db.execute(text("SELECT checkin_version FROM risk_evaluations")).scalar() == 1
        assert not db.execute(text("PRAGMA foreign_key_check")).all()
    engine.dispose()
