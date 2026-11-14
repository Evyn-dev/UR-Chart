"""Vercel's FastAPI entrypoint. The shared app and its API remain in app/main.py."""
from app.main import app

__all__ = ["app"]
