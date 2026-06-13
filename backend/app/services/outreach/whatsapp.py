"""
WhatsApp sender (openWA) for T6 outreach.

Per playbook R7: openWA is the chosen WhatsApp gateway. We
already have cf-openwa-proxy in docker-compose (per T12).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("clientfinder.outreach.whatsapp")


async def send_whatsapp(
    *,
    to_phone: str,
    body: str,
) -> dict[str, Any]:
    """
    Send a WhatsApp message via openWA.

    openWA uses a session-based API. The session must be
    started/scanned-in once via the dashboard
    (http://openwa-dashboard-url). For v1 we just call
    /api/sendText.

    Returns: {ok, external_id, error}
    """
    if not settings.waha_base_url:
        return {"ok": False, "error": "WAHA_BASE_URL not set"}
    if not to_phone:
        return {"ok": False, "error": "Recipient phone empty"}

    # openWA chatId format: phone@c.us (for personal) or phone@g.us (for groups)
    # We assume personal.
    chat_id = to_phone.replace("+", "").replace(" ", "") + "@c.us"

    url = f"{settings.waha_base_url}/api/sendText"
    payload = {
        "session": settings.waha_session_name,
        "chatId": chat_id,
        "text": body,
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            return {
                "ok": False,
                "error": f"WAHA HTTP {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        return {
            "ok": True,
            "external_id": data.get("id") or data.get("messageId"),
            "transport": "waha",
            "raw": data,
        }
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"WAHA request failed: {e!s}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"WAHA unknown error: {e!s}"}
