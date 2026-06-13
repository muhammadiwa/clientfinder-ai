"""
Outreach tasks — Celery tasks for T6 (Outreach module)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.outreach import Message
from app.services.outreach import (
    approve_message,
    send_message_now,
    submit_for_approval,
)

logger = logging.getLogger("clientfinder.tasks.outreach")


# --- Sync wrappers (called from API endpoints) ---

async def submit_for_approval_async(message_id: str) -> dict[str, Any]:
    return await submit_for_approval(UUID(message_id))


async def approve_message_async(
    message_id: str,
    approver_id: str,
    approve: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    return await approve_message(
        UUID(message_id),
        approver_id=UUID(approver_id),
        approve=approve,
        reason=reason,
    )


async def send_message_async(message_id: str) -> dict[str, Any]:
    return await send_message_now(UUID(message_id))


# --- Celery tasks ---

@celery_app.task(name="app.tasks.outreach.send_message", bind=True, max_retries=2)
def send_message_task(self, message_id: str) -> dict[str, Any]:
    """Celery task: send an approved message."""
    logger.info("Celery task start: send_message=%s", message_id)
    try:
        return asyncio.run(send_message_async(message_id))
    except Exception as e:  # noqa: BLE001
        logger.exception("Send task failed: %s", e)
        return {"ok": False, "error": f"task_crashed: {e!s}"}


@celery_app.task(name="app.tasks.outreach.send_scheduled", bind=True)
def send_scheduled_task(self) -> int:
    """Periodic task: find scheduled messages whose time has come
    and enqueue them for sending.

    Wired to celery-beat (in T8). For now this is a stub.
    """
    logger.info("send_scheduled_task: scanning...")
    return 0
