import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

TOKENS = {"a" * 40: "synthetic-alex", "b" * 40: "synthetic-jordan"}


@pytest.fixture
def database_url(tmp_path):
    url = "sqlite:///" + (tmp_path / "test.db").as_posix()
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    return url


@pytest.fixture
def app(database_url):
    return create_app(Settings(_env_file=None, app_env="test", database_url=database_url, demo_auth_enabled=True, demo_tokens=TOKENS, ai_provider="approved_instructions"))


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth():
    return {"Authorization": "Bearer " + "a" * 40}


@pytest.fixture
def other():
    return {"Authorization": "Bearer " + "b" * 40}
