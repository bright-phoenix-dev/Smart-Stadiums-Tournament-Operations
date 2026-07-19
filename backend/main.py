"""
Smart Stadium Platform — FastAPI Application Entry Point
=========================================================
Initializes the FastAPI application with:
    - CORS middleware for frontend communication
    - Route registration (operations + fan endpoints)
    - Simulation engine lifecycle management
    - WebSocket endpoint for real-time dashboard updates
    - Health check endpoint
    - Auto-generated token endpoints for development
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.config import (
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    CORS_ORIGINS,
    IS_PRODUCTION,
    JWT_SECRET,
)
from backend.models.stadium import HealthResponse
from backend.routes.fan import router as fan_router
from backend.routes.operations import router as ops_router
from backend.simulation.engine import simulator
from backend.middleware.security import create_role_token

# Configure structured telemetry logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "module":"%(name)s", "msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    - Startup: Validate configuration, then start the stadium simulator.
    - Shutdown: Gracefully stop the simulator.
    """
    logger.info("Starting %s v%s", APP_TITLE, APP_VERSION)

    # --- JWT_SECRET validation ---
    # Import here to read the current module-level value (may be patched in tests).
    from backend import config as _cfg
    effective_secret = _cfg.JWT_SECRET
    if not effective_secret:
        if IS_PRODUCTION:
            raise RuntimeError(
                "JWT_SECRET environment variable is not set. "
                "The application cannot start in production without a signing secret."
            )
        else:
            # Development: auto-generate a random secret and warn loudly.
            import backend.config as _mutable_cfg  # noqa: F401
            generated = secrets.token_hex(32)
            os.environ["JWT_SECRET"] = generated
            # Patch the module-level constant so security.py picks it up on next import.
            # (conftest already sets JWT_SECRET for tests, so this branch is for bare dev runs.)
            import importlib
            import backend.config
            backend.config.JWT_SECRET = generated  # type: ignore[assignment]
            logger.warning(
                "JWT_SECRET is not set. A random secret has been generated for this "
                "session: %s\nSet JWT_SECRET in your environment to make it persistent.",
                generated,
            )

    await simulator.start()
    logger.info("Simulation engine started")

    yield  # Application runs here

    logger.info("Shutting down simulation engine...")
    await simulator.stop()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------------

app = fifa2026OpsAssistant = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

from backend.config import CORS_ORIGINS

# Security Middleware: Prevent cross-origin attacks and clickjacking
fifa2026OpsAssistant.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-Signature"],
)

# Efficiency Middleware: JSON Payload Compression for crowded stadium networks
fifa2026OpsAssistant.add_middleware(GZipMiddleware, minimum_size=1000)

@fifa2026OpsAssistant.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    [Alignment: Smart Stadium Operations] Inject strict security headers for production deployment.
    Safeguards the FIFA World Cup 2026 operations dashboard against XSS and clickjacking.
    """
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:;"
    return response

# Register route modules
fifa2026OpsAssistant.include_router(ops_router)
fifa2026OpsAssistant.include_router(fan_router)

@fifa2026OpsAssistant.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to prevent raw stack trace leakage.
    Returns a standardized 500 Internal Server Error JSON payload.
    """
    logger.error("Unhandled Exception at %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "code": 500, "message": "An unexpected system error occurred."},
    )


# ---------------------------------------------------------------------------
# Root & Health Endpoints
# ---------------------------------------------------------------------------

@fifa2026OpsAssistant.get("/", tags=["System"], summary="API root")
async def root() -> dict:
    """Return API information and available endpoints."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "docs": "/docs",
        "endpoints": {
            "operations_dashboard": "/api/ops/stadium-state",
            "fan_assistant": "/api/fan/assistant",
            "health": "/health",
            "websocket": "/ws/live",
        },
    }


@fifa2026OpsAssistant.get("/health", response_model=HealthResponse, tags=["System"], summary="Health check")
async def health_check() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        simulation_active=simulator.is_running,
    )


@fifa2026OpsAssistant.get("/static/{filename}", tags=["System"], summary="Serve static assets")
async def get_static_file(filename: str):
    """Serve a file from the static directory."""
    file_path = os.path.join(os.path.dirname(__file__), "static", filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Not Found"})
    return FileResponse(file_path, media_type="application/octet-stream")


# ---------------------------------------------------------------------------
# Development-Only Endpoints (blocked in production)
# ---------------------------------------------------------------------------

if not IS_PRODUCTION:
    @app.get("/dev/token/{role}", tags=["Development"], summary="Generate a dev auth token (dev only)")
    async def dev_get_token(role: str) -> dict:
        """
        Return a signed JWT for the given role — for local development and test
        clients only.  This endpoint is disabled when ENVIRONMENT=production.

        Args:
            role: 'staff' or 'fan'.

        Returns:
            Dict with 'role' and 'token', or 'error' for invalid roles.
        """
        try:
            token = create_role_token(role, subject="dev-user")
            return {"role": role, "token": token}
        except ValueError as exc:
            return {"error": str(exc)}


@fifa2026OpsAssistant.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stadium state updates.

    Clients connect and receive JSON state snapshots on every
    simulation tick (~5 seconds).  Connection is maintained
    until the client disconnects.
    """
    await websocket.accept()
    logger.info("WebSocket client connected: %s", websocket.client)

    # Subscribe to simulation updates
    queue = simulator.subscribe()

    try:
        while True:
            # Wait for next state update from simulator
            state = await queue.get()
            # Serialize and send
            state_json = state.model_dump(mode="json")
            await websocket.send_text(json.dumps(state_json, default=str))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: %s", websocket.client)
    except Exception:
        logger.exception("WebSocket error")
    finally:
        simulator.unsubscribe(queue)


# ---------------------------------------------------------------------------
# Run with Uvicorn (development)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:fifa2026OpsAssistant",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
