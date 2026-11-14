from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import text, select
from app.models import Patient
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from app.auth import get_db
from app.schemas import Data
from pathlib import Path
from typing import Literal
from alembic.script import ScriptDirectory

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    authentication: str
    login_mode: Literal["demo_token", "demo_code", "supabase", "unconfigured"]
    ai_provider: str


@router.get("/health", response_model=Data[Health])
def health(request: Request, db=Depends(get_db)):
    try:
        settings = request.app.state.settings
        version_table = (
            f"{settings.database_schema}.alembic_version"
            if settings.database_schema else "alembic_version"
        )
        revisions = set(db.execute(text(f"SELECT version_num FROM {version_table}")).scalars())
        heads = set(ScriptDirectory(str(Path(__file__).resolve().parents[2] / "migrations")).get_heads())
        if revisions != heads:
            raise HTTPException(503, "Database migrations required")
        # The migration table uses qualified raw SQL. Also exercise the actual
        # SQLAlchemy schema translation used by all authenticated feature routes.
        db.execute(select(Patient.id).limit(1)).first()
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migrations required") from None
    settings = request.app.state.settings
    # Match the authentication provider precedence in authenticated_identity.
    login_mode = (
        "demo_token" if settings.demo_auth_enabled else
        "demo_code" if settings.hosted_demo_code_hash else
        "supabase" if settings.supabase_url and settings.supabase_publishable_key else
        "unconfigured"
    )
    authentication = "demo" if login_mode in {"demo_token", "demo_code"} else login_mode
    return {"data": {"status": "ok", "authentication": authentication,
                     "login_mode": login_mode, "ai_provider": settings.ai_provider}}
