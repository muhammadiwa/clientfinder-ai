"""
ClientFinder AI Agent — Backend Entry Point (T1 placeholder)
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

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
    yield
    logger.info("Shutting down ClientFinder AI Agent backend...")


app = FastAPI(
    title="ClientFinder AI Agent",
    version="0.1.0",
    description="AI-powered lead generation for freelance software developers",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS (open in T1, locked in T2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """Root endpoint — sanity check."""
    return {
        "service": "ClientFinder AI Agent",
        "version": "0.1.0",
        "status": "running",
        "phase": "T1",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    """Health check — used by docker healthcheck and load balancers."""
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/api/v1/info")
async def info() -> dict:
    """App info endpoint."""
    return {
        "name": "ClientFinder",
        "version": "0.1.0",
        "phase": "T1 - Infrastructure Foundation",
        "next_milestone": "T2 - Backend Core (DB, Auth, Models)",
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
    )
