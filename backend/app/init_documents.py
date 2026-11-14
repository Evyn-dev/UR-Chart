"""Create only the small-file attachment table for an isolated fictional demo.

Use this explicit one-off command on a hosted demo DB before deploying routes.
This is not a substitute for migration review, encryption, storage policies,
antivirus scanning, auditing, or clinical-data compliance in a real app.
"""
from app.config import Settings
from app.database import Base, make_engine
from app.models import SharedDocument


def main():
    settings = Settings()
    if settings.app_env not in {"development", "test"} and not settings.hosted_demo_code_hash:
        raise RuntimeError("Only initialize documents for an isolated fictional demo database")
    engine = make_engine(settings.database_url, database_schema=settings.database_schema)
    try:
        Base.metadata.create_all(engine, tables=[SharedDocument.__table__], checkfirst=True)
        print("Shared fictional document table is ready.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
