from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from app.auth import get_db
from app.schemas import Data

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    authentication: str
    ai_provider: str


@router.get("/health", response_model=Data[Health])
def health(request: Request, db=Depends(get_db)):
    try:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != "0001":
            raise HTTPException(503, "Database migrations required")
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migrations required") from None
    settings = request.app.state.settings
    return {"data": {"status": "ok", "authentication": "demo" if settings.demo_auth_enabled else "unconfigured", "ai_provider": settings.ai_provider}}
