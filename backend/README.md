# UR Chart backend

FastAPI, SQLAlchemy, and Alembic. Follow the [root setup guide](../README.md#local-setup).

- [API integration reference](../BACKEND_GUIDE.md)
- [Recovery and caregiver API contracts](RECOVERY_TRACKING.md)
- Live local Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

Routes live in `app/api`, business logic in `app/services`, authentication in `app/auth.py`, and database setup in `app/database.py`. Keep patient ownership checks on the server. Preserve all applied migrations; add new ones for schema changes.
