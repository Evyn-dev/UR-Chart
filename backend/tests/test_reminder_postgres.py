"""Real PostgreSQL upgrade + API coverage, confined to disposable CI schemas."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.config import Settings
from app.database import make_engine
from app.main import create_app


def test_private_schema_migration_preserves_records_and_reminder_api():
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg:") or make_url(url).host not in {"localhost", "127.0.0.1"}:
        pytest.skip("Requires the isolated PostgreSQL CI service")
    schema = "ci_reminders_" + uuid4().hex
    engine = make_engine(url)
    config = Config("alembic.ini")
    config.attributes.update(database_url=url, database_schema=schema)
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            public_revision = connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        command.upgrade(config, "0005")
        with engine.begin() as connection:
            connection.execute(text(f"INSERT INTO {schema}.patients (id,user_id,display_name,timezone,created_at,updated_at) VALUES ('preserved','existing','Demo','UTC',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        command.upgrade(config, "head");command.check(config)
        with engine.connect() as connection:
            assert connection.scalar(text(f"SELECT user_id FROM {schema}.patients WHERE id='preserved'")) == "existing"
            assert connection.scalar(text(f"SELECT version_num FROM {schema}.alembic_version")) == "0006"
            assert connection.scalar(text("SELECT version_num FROM public.alembic_version")) == public_revision
        settings = Settings(_env_file=None, app_env="test", database_url=url, database_schema=schema,
            demo_auth_enabled=True, demo_tokens={"a"*40: "patient", "b"*40: "other"})
        auth={"Authorization": "Bearer "+"a"*40};other={"Authorization": "Bearer "+"b"*40}
        body={"title":"Postgres reminder","due_at":"2026-01-01T10:00:00Z","repeat":"daily"}
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/health").status_code == 200
            posted = client.post("/api/reminders", headers=auth, json=body)
            assert posted.status_code == 201, posted.text
            item=posted.json()["data"];path=f"/api/reminders/{item['id']}"
            assert client.get("/api/reminders", headers=other).json()["data"] == []
            assert client.patch(path, headers=other, json={**body,"expected_version":1}).status_code == 404
            assert client.patch(path, headers=auth, json={**body,"title":"Edited","expected_version":1}).status_code == 200
            completed=client.post(path+"/action", headers=auth, json={"action":"complete","expected_version":2})
            assert completed.status_code == 200 and completed.json()["data"]["last_action"] == "complete"
            assert client.post(path+"/action", headers=auth, json={"action":"complete","expected_version":2}).status_code == 409
            assert client.get("/api/reminders", headers=auth).json()["data"][0]["version"] == 3
        with pytest.raises(RuntimeError, match="populated personal reminders"):
            command.downgrade(config, "0005")
        missing=Config("alembic.ini");missing.attributes.update(database_url=url,database_schema=schema+"_missing")
        with pytest.raises(ValueError, match="does not exist"):
            command.upgrade(missing, "head")
    finally:
        # Only this test's random schema is removed; public/hosted schemas are untouched.
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
