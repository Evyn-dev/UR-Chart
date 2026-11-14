"""Regression coverage for demo login discovery and narrative screening."""
import hashlib

import pytest

from app.services import risk


@pytest.mark.parametrize("mode", ["demo_token", "demo_code", "supabase", "unconfigured"])
def test_health_reports_login_mode(client, app, mode):
    settings = app.state.settings
    settings.demo_auth_enabled = mode == "demo_token"
    settings.hosted_demo_code_hash = hashlib.sha256(b"test-code").hexdigest() if mode == "demo_code" else ""
    settings.supabase_url = "https://example.supabase.co" if mode == "supabase" else ""
    settings.supabase_publishable_key = "test-key" if mode == "supabase" else ""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data"]["login_mode"] == mode
    assert response.json()["data"]["authentication"] == ("demo" if mode.startswith("demo_") else mode)


@pytest.mark.parametrize("note,reported", [
    ("No fever but chest pain", True),
    ("No chest pain earlier. I now have chest pain.", True),
    ("No chest pain earlier and now I am experiencing chest pain", True),
    ("No fever; chest pain", True),
    ("No fever\nchest pain", True),
    ("Denies fever, however chest pain persists", True),
    ("No chest pain", False),
    ("No chest pain yet", False),
    ("Not yet experiencing chest pain", False),
    ("Denies chest pain. No chest pain now either.", False),
    ("No chest pain but no fever either", False),
    ("No fever but not chest pain either", False),
    ("I have chest pain", True),
    ("chest painting", False),
])
def test_phrase_negation_is_scoped_to_each_occurrence(note, reported):
    assert risk._phrase_is_reported(note, "chest pain") is reported


@pytest.mark.parametrize("note", [
    "No fever but chest pain",
    "No chest pain earlier. I now have chest pain.",
])
def test_affirmative_note_creates_emergency_alert(client, auth, note):
    response = client.post("/api/checkins", headers=auth, json={"day": "2026-11-14", "note": note})
    assert response.status_code == 201
    assessment = client.get(f"/api/checkins/{response.json()['data']['id']}/risk", headers=auth).json()["data"]
    assert any(alert["severity"] == "emergency" for alert in assessment["alerts"])


def test_new_screening_version_reevaluates_existing_checkin(client, auth, monkeypatch):
    matcher = risk._phrase_is_reported
    with monkeypatch.context() as old_engine:
        old_engine.setattr(risk, "SCREENING_ENGINE_VERSION", "2")
        old_engine.setattr(risk, "_phrase_is_reported", lambda *_: False)
        response = client.post("/api/checkins", headers=auth, json={
            "day": "2026-11-14", "note": "No fever but chest pain",
        })
    assert response.status_code == 201
    assert risk._phrase_is_reported is matcher
    assessment = client.get(f"/api/checkins/{response.json()['data']['id']}/risk", headers=auth).json()["data"]
    assert any(alert["severity"] == "emergency" for alert in assessment["alerts"])
