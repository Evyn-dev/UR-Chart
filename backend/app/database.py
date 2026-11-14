from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


def make_engine(url, database_schema=None):
    """Use an isolated schema without relying on connection search_path state."""
    is_sqlite = url.startswith("sqlite")
    is_psycopg = url.startswith("postgresql+psycopg:")
    connect_args = {"check_same_thread": False} if is_sqlite else (
        {"prepare_threshold": None} if is_psycopg else {}
    )
    options = {"connect_args": connect_args, "pool_pre_ping": True}
    if not is_sqlite:
        options["poolclass"] = NullPool
    engine = create_engine(url, **options)
    if database_schema and not is_sqlite:
        engine = engine.execution_options(schema_translate_map={None: database_schema})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_options(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
    return engine


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
