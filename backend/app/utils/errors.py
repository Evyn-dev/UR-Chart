from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def install_errors(app):
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc):
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": str(exc.status_code), "message": str(exc.detail)}}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc):
        # Exclude submitted values and exception contexts from errors.
        details = [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Invalid request", "details": details}})

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, exc):
        return JSONResponse(status_code=409, content={"error": {"code": "conflict", "message": "Record conflicts with existing data"}})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc):
        return JSONResponse(status_code=503, content={"error": {"code": "database_unavailable", "message": "Database unavailable"}})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc):
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Internal server error"}})
