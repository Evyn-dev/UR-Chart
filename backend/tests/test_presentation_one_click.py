"""One-click fictional presentation access requires an explicit nonproduction opt-in."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.config import Settings
from app.main import create_app
from app.models import CaregiverRelationship
from app.seed import seed


def test_presentation_entry_and_fictional_data(database_url):
    settings = Settings(
        _env_file=None, app_env="test", database_url=database_url,
        demo_auth_enabled=False, demo_tokens={}, hosted_demo_code_hash="",
        presentation_demo_enabled=True, ai_provider="approved_instructions"
    )
    seed(settings)
    seed(settings)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/demo/access").json()["data"]["enabled"] is True
        patient_header = {"Authorization": "Bearer urchart-presentation:patient"}
        caregiver_header = {"Authorization": "Bearer urchart-presentation:caregiver"}
        patient = client.get("/api/patients/me", headers=patient_header)
        caregiver = client.get("/api/patients/me", headers=caregiver_header)
        assert patient.status_code == 200
        assert caregiver.status_code == 200
        assert patient.json()["data"]["id"] != caregiver.json()["data"]["id"]
        assert patient.json()["data"]["display_name"] == "Jordan Ellis (fictional)"
        with client.app.state.sessions() as db:
            relations = db.scalars(select(CaregiverRelationship)).all()
            assert len(relations) == 1
            assert relations[0].status == "active"
            assert set(relations[0].permissions) == {
                "recovery_summary", "checkin_summary", "medication_adherence", "alerts"
            }
        active = client.get("/api/caregiver/relationships", headers=caregiver_header)
        assert active.status_code == 200
        assert len(active.json()["data"]) == 1
        relationship_id = active.json()["data"][0]["id"]
        dashboard = client.get(
            f"/api/caregiver/relationships/{relationship_id}/dashboard",
            headers=caregiver_header,
        )
        assert dashboard.status_code == 200
        data = dashboard.json()["data"]
        assert len(data["checkin_summary"]["recent"]) == 7
        assert data["medication_adherence"]["medications_included"] == 3
        assert data["alerts"]
        assert client.get(
            f"/api/caregiver/relationships/{relationship_id}/dashboard",
            headers=patient_header,
        ).status_code == 404


def test_presentation_entry_is_disabled_without_opt_in(database_url):
    settings = Settings(_env_file=None, app_env="test", database_url=database_url,
                        demo_auth_enabled=False, presentation_demo_enabled=False)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/demo/access").json()["data"]["enabled"] is False
        assert client.get("/api/patients/me", headers={
            "Authorization": "Bearer urchart-presentation:patient"
        }).status_code == 503


def test_public_presentation_access_cannot_run_with_production_or_supabase():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", presentation_demo_enabled=True)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="development",
                 presentation_demo_enabled=True,
                 supabase_url="https://example.supabase.co",
                 supabase_publishable_key="test-key")
