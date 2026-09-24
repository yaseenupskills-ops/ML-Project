"""FastAPI app entrypoint: uvicorn app.api.main:app (PRD §3.1, §14)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routers import alerts, auth, devices, events, feedback, subjects, system, users
from app.config.settings import get_settings
from app.monitoring.logging import configure_logging

configure_logging()

settings = get_settings()

app = FastAPI(title="FallGuard API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

register_error_handlers(app)

app.include_router(system.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(subjects.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
