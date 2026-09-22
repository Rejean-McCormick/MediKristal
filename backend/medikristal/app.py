from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, ORJSONResponse
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import load_settings
from .contracts import openapi_schema
from .db import Base, engine
from .errors import DomainError, error_response

settings = load_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="MediKristal",
    version="0.2.0",
    docs_url="/developer/docs",
    redoc_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Correlation-ID")
    try:
        corr = str(uuid.UUID(incoming)) if incoming else str(uuid.uuid4())
    except ValueError:
        corr = str(uuid.uuid4())
    request.state.correlation_id = corr
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    return error_response(request, exc)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    field_errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        path = ".".join(str(part) for part in loc) or "$"
        field_errors.append({"path": path, "code": str(error.get("type", "invalid"))})
    return error_response(request, DomainError(
        "invalid_request", 422, "La requête ne respecte pas le contrat de transport.",
        field_errors=field_errors,
    ))


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
def readyz():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(router)

if settings.frontend_dir.exists():
    assets = settings.frontend_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(settings.frontend_dir / "index.html")

    @app.get("/app.js", include_in_schema=False)
    def frontend_js():
        return FileResponse(settings.frontend_dir / "app.js", media_type="application/javascript")

    @app.get("/styles.css", include_in_schema=False)
    def frontend_css():
        return FileResponse(settings.frontend_dir / "styles.css", media_type="text/css")


_original_openapi = openapi_schema()
def custom_openapi():
    # Serve the checked-in contract as authority. The runtime routes are mounted under /api/v1,
    # matching the contract server base URL.
    return _original_openapi
app.openapi = custom_openapi

