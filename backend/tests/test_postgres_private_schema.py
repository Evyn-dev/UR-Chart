"""Validate SQLAlchemy's private-schema translation against real PostgreSQL in CI."""
import os
import pytest
from sqlalchemy import select, text

from app.database import make_engine
from app.models import Patient


def test_private_schema_translation_on_postgres():
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg:"):
        pytest.skip("Only runs inside PostgreSQL migration compatibility CI")
    root = make_engine(url)
    try:
        with root.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS ci_private_urchart"))
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS ci_private_urchart.patients "
                "(LIKE public.patients INCLUDING ALL)"
            ))
        private = make_engine(url, database_schema="ci_private_urchart")
        try:
            with private.connect() as connection:
                rows = connection.execute(select(Patient.id).limit(1)).all()
                assert rows == []
        finally:
            private.dispose()
    finally:
        root.dispose()
