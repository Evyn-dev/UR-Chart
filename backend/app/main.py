from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Settings
from app.database import make_engine, session_factory
from app.api import patients, medications, checkins, alerts, chat, health, caregivers, corrections
from app.services.ai import build_provider
from app.utils.errors import install_errors
from app.schemas import ErrorResponse


def create_app(settings=None, engine=None, provider=None):
    settings = settings or Settings()
    engine = engine or make_engine(settings.database_url, database_schema=settings.database_schema)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="UR Chart Shared API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = session_factory(engine)
    app.state.ai = provider or build_provider(settings)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])
    install_errors(app)
    for module in (patients, medications, checkins, alerts, chat, health, caregivers, corrections):
        app.include_router(module.router, prefix="/api", responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)})
    return app


app = create_app()
