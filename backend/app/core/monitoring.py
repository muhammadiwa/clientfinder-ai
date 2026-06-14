"""
Monitoring + observability (T8 Group 2).

Provides:
  - MetricsMiddleware: per-request Prometheus metrics
    (count, latency, in-progress, errors by status)
  - /healthz: deep health check (db + redis)
  - /metrics: Prometheus scrape endpoint
  - Structured JSON request logger
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import engine
from app.core.redis_client import get_redis

logger = logging.getLogger("clientfinder.monitoring")

# --- Prometheus metrics (use a dedicated registry to avoid globals) ---

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "cf_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "cf_http_request_duration_seconds",
    "HTTP request latency",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

REQUEST_IN_PROGRESS = Gauge(
    "cf_http_requests_in_progress",
    "HTTP requests currently in progress",
    labelnames=("method",),
    registry=REGISTRY,
)

RATE_LIMIT_HITS = Counter(
    "cf_rate_limit_hits_total",
    "Total rate limit hits (429 responses)",
    labelnames=("path",),
    registry=REGISTRY,
)

DB_HEALTH = Gauge(
    "cf_db_up",
    "Database reachable (1=up, 0=down)",
    registry=REGISTRY,
)

REDIS_HEALTH = Gauge(
    "cf_redis_up",
    "Redis reachable (1=up, 0=down)",
    registry=REGISTRY,
)


# --- Middleware ---

# Path normalization for high-cardinality protection: /prospects/{id}
# collapses to /prospects/:id
def _normalize_path(path: str) -> str:
    """Replace UUIDs and IDs in path with :id placeholder for metrics."""
    import re

    if re.match(r"^/api/v1/prospects/[a-f0-9-]{36}$", path):
        return "/api/v1/prospects/:id"
    if re.match(r"^/api/v1/prospects/[a-f0-9-]{36}/detail$", path):
        return "/api/v1/prospects/:id/detail"
    if re.match(r"^/api/v1/prospects/[a-f0-9-]{36}/enrich$", path):
        return "/api/v1/prospects/:id/enrich"
    if re.match(r"^/api/v1/outreach/messages/[a-f0-9-]{36}(/.*)?$", path):
        return "/api/v1/outreach/messages/:id"
    if re.match(r"^/api/v1/ai/hooks/[a-f0-9-]{36}$", path):
        return "/api/v1/ai/hooks/:id"
    if re.match(r"^/api/v1/ai/complete$", path):
        return path
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records Prometheus metrics + structured JSON log per request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/metrics":
            # Don't record metrics for the metrics endpoint itself
            return await call_next(request)

        method = request.method
        path = _normalize_path(request.url.path)
        REQUEST_IN_PROGRESS.labels(method=method).inc()
        start = time.monotonic()
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            elapsed = time.monotonic() - start
            REQUEST_COUNT.labels(
                method=method, path=path, status=status
            ).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
            REQUEST_IN_PROGRESS.labels(method=method).dec()
            if status == "429":
                RATE_LIMIT_HITS.labels(path=path).inc()
            # Structured JSON log line
            logger.info(
                json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "method": method,
                    "path": path,
                    "status": int(status) if status.isdigit() else 500,
                    "duration_ms": round(elapsed * 1000, 1),
                    "client": request.client.host if request.client else None,
                    "ua": request.headers.get("user-agent", "")[:80],
                })
            )
        return response


# --- Endpoints ---

async def healthz_endpoint() -> dict:
    """Deep health check — verifies DB + Redis reachable.

    Use for docker healthcheck / k8s liveness probe.
    """
    db_ok = False
    redis_ok = False
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:  # noqa: BLE001
        logger.warning("DB health check failed: %s", e)
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis health check failed: %s", e)
    DB_HEALTH.set(1 if db_ok else 0)
    REDIS_HEALTH.set(1 if redis_ok else 0)
    overall = db_ok and redis_ok
    return {
        "status": "healthy" if overall else "degraded",
        "db": db_ok,
        "redis": redis_ok,
    }


def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


def register_monitoring(app: FastAPI) -> None:
    """Add the metrics middleware + endpoints to the app."""
    app.add_middleware(MetricsMiddleware)
    # Endpoints (added directly because they're app-level, not v1 API)
    app.add_api_route(
        "/healthz",
        healthz_endpoint,
        methods=["GET"],
        tags=["monitoring"],
        summary="Deep health check (db + redis)",
    )
    app.add_api_route(
        "/metrics",
        metrics_endpoint,
        methods=["GET"],
        tags=["monitoring"],
        summary="Prometheus metrics",
        include_in_schema=False,
    )
