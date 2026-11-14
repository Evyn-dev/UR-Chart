from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from app.auth import get_db
from app.schemas import Data
from pathlib import Path
from alembic.script import ScriptDirectory

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    authentication: str
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
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migrations required") from None
    settings = request.app.state.settings
    return {"data": {"status": "ok", "authentication": "demo" if settings.demo_auth_enabled else "supabase" if settings.supabase_url and settings.supabase_publishable_key else "unconfigured", "ai_provider": settings.ai_provider}}
