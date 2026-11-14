import re
from alembic import context
from sqlalchemy import text
from app.config import Settings
from app.database import Base, make_engine
from app import models  # register model metadata

config = context.config
settings = Settings()
url = config.attributes.get("database_url") or settings.database_url
schema = config.attributes.get("database_schema", settings.database_schema)
if schema and (not re.fullmatch(r"[a-z_][a-z0-9_]*", schema) or not url.startswith("postgresql")):
    raise ValueError("DATABASE_SCHEMA requires PostgreSQL and a safe schema identifier")

if context.is_offline_mode():
    if schema:
        raise ValueError("Private-schema migrations require an online connection")
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    # Alembic does not apply ORM schema_translate_map to all migration operations.
    # Keep the search path local to this single migration transaction, without a
    # public fallback. A missing private schema must fail, never create in public.
    engine = make_engine(url)
    try:
        with engine.begin() as connection:
            default_schema = connection.dialect.default_schema_name
            try:
                if schema:
                    exists = connection.scalar(text("SELECT 1 FROM pg_namespace WHERE nspname=:name"), {"name": schema})
                    if not exists:
                        raise ValueError("Configured migration schema does not exist")
                    connection.execute(text("SELECT set_config('search_path', :schema, true)"), {"schema": schema})
                    connection.dialect.default_schema_name = schema
                context.configure(connection=connection, target_metadata=Base.metadata,
                    version_table_schema=schema, render_as_batch=url.startswith("sqlite"))
                with context.begin_transaction():
                    context.run_migrations()
            finally:
                connection.dialect.default_schema_name = default_schema
    finally:
        engine.dispose()
