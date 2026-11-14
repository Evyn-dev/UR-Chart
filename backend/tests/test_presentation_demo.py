"""Presentation fixture tests: fictional records, trends, caregiver, and Clara."""
from hashlib import sha256
from sqlalchemy import select
from app.config import Settings
from app.seed import seed
from app.presentation_demo import verify
from app.models import CaregiverRelationship


def test_hosted_presentation_demo_seed_and_check(database_url):
    settings = Settings(
        _env_file=None, app_env="production", database_url=database_url,
        hosted_demo_code_hash=sha256(b"fake-presentation-access-code").hexdigest(),
        demo_auth_enabled=False,
    )
    assert verify(settings) == ["Fictional presentation patient is not present"]
    seed(settings, presentation_demo=True)
    assert verify(settings) == []
    seed(settings, presentation_demo=True)
    assert verify(settings) == []


def test_presentation_check_reports_incomplete_permissions(database_url):
    settings = Settings(
        _env_file=None, app_env="test", database_url=database_url,
        hosted_demo_code_hash=sha256(b"fake-presentation-access-code").hexdigest(),
        demo_auth_enabled=False,
    )
    seed(settings)
    assert verify(settings) == []
    from app.database import make_engine, session_factory
    engine = make_engine(database_url)
    try:
        with session_factory(engine)() as db:
            rel = db.scalar(select(CaregiverRelationship).where(
                CaregiverRelationship.caregiver_user_id == "synthetic-demo-caregiver"
            ))
            rel.permissions = ["recovery_summary"]
            db.commit()
        assert any("permissions" in x for x in verify(settings))
        seed(settings)
        assert verify(settings) == []
    finally:
        engine.dispose()


def test_production_seed_still_requires_explicit_opt_in(database_url):
    import pytest
    settings = Settings(
        _env_file=None, app_env="production", database_url=database_url,
        hosted_demo_code_hash=sha256(b"fake-presentation-access-code").hexdigest(),
    )
    with pytest.raises(RuntimeError):
        seed(settings)
