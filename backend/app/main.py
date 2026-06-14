"""
ClientFinder AI Agent — Backend Entry Point (T8 production-hardened)
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.v1 import (
    ai,
    analytics,
    auth,
    outreach,
    prospects,
    scraping,
    sequences,
    templates,
)
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.monitoring import register_monitoring
from app.core.security import (
    SecurityHeadersMiddleware,
    configure_rate_limiter,
    validate_secrets_at_startup,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("clientfinder")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    logger.info("Starting ClientFinder AI Agent backend...")
    logger.info(f"  app_env:   {settings.app_env}")
    logger.info(f"  app_debug: {settings.app_debug}")
    logger.info(f"  cors:      {settings.cors_origins_list}")
    # Validate secrets at boot — fail fast in non-local envs
    validate_secrets_at_startup()
    yield
    logger.info("Shutting down ClientFinder AI Agent backend...")
    await close_db()


# --- App init ---
app = FastAPI(
    title="ClientFinder AI Agent",
    version="0.1.0",
    description="AI-powered lead generation for freelance software developers",
    # docs_url and redoc_url are overridden below to use locally-vendored
    # assets (per R4: minimize external dependencies). The vendored copies
    # live at backend/app/static/swagger-ui/ — see that directory for the
    # script that refreshes them.
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Serve vendored Swagger UI / Redoc assets from /static.
# Files: backend/app/static/swagger-ui/{swagger-ui.css, swagger-ui-bundle.js,
# redoc.standalone.js}. Keeps the docs UI working behind firewalls /
# air-gapped networks where the default jsdelivr CDN is unreachable.
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Swagger UI with locally-vendored CSS+JS (no CDN)."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon.png",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc UI with locally-vendored JS (no CDN)."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/swagger-ui/redoc.standalone.js",
        redoc_favicon_url="/static/swagger-ui/favicon.png",
        with_google_fonts=False,
    )

# --- Middleware (order matters: outermost = first added) ---
# 1. Security headers (outermost, so applies to ALL responses)
app.add_middleware(SecurityHeadersMiddleware)
# 2. Metrics (request-level instrumentation)
register_monitoring(app)
# 3. CORS (T8: locked-down to specific origins)
#    Note: CORS middleware adds the CORS headers BEFORE the
#    response goes through other middlewares.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
    max_age=600,  # preflight cache
)
# 4. Rate limiting (T8: per-user or per-IP throttling)
configure_rate_limiter(app)

# --- Routers (v1 API) ---
app.include_router(auth.router, prefix="/api/v1")
app.include_router(prospects.router, prefix="/api/v1")
app.include_router(scraping.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(outreach.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(sequences.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


# --- Legacy / health (T1) ---
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "ClientFinder AI Agent",
        "version": "0.1.0",
        "status": "running",
        "phase": "T8 - Production hardening",
        "docs": "/docs",
    }


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "backend",
    }


# --- Error handlers ---

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    logger.warning("Rate limit hit on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Slow down.",
            },
        },
        headers={"Retry-After": "60"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
        },
    )
