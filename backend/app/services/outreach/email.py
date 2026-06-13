"""
Email sender (SMTP) for T6 outreach.

Per playbook R7 (pragmatic-legal): use real SMTP with TLS.
For v1, we use aiosmtplib for async sending. If SMTP not
configured, send is a no-op (logs the message).
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import settings

logger = logging.getLogger("clientfinder.outreach.email")


async def send_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """
    Send an email via SMTP.

    Returns: {ok, external_id, error}

    If SMTP isn't configured (empty user/password), this is a
    no-op and returns ok=False with a clear error message.
    This is the v1 behavior — production will use real SMTP
    per R7.
    """
    if not settings.smtp_user or not settings.smtp_password:
        return {
            "ok": False,
            "error": "SMTP not configured (SMTP_USER/SMTP_PASSWORD empty)",
        }
    if not settings.smtp_from_email:
        return {"ok": False, "error": "SMTP_FROM_EMAIL not set"}
    if not to_email:
        return {"ok": False, "error": "Recipient email empty"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # Run blocking smtplib in a thread to keep event loop non-blocking
    def _send():
        try:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=30
            ) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                rejected = server.send_message(msg)
                return {"ok": True, "rejected": rejected}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    result = await asyncio.get_event_loop().run_in_executor(None, _send)
    if result.get("ok"):
        return {
            "ok": True,
            "external_id": f"smtp-{to_email}-{hash(subject) % 100000}",
            "transport": "smtp",
        }
    return {"ok": False, "error": result.get("error", "unknown SMTP error")}


def render_email_body(body: str, prospect_name: str = "") -> str:
    """
    Convert a plain-text message body to a more friendly format.
    Adds a signature line and proper greeting.
    """
    if not body:
        return ""
    lines = [body.strip()]
    if prospect_name and not body.startswith("Halo") and not body.startswith("Hi"):
        lines.insert(0, f"Halo {prospect_name},")
        lines.append("")
    lines.append("")
    lines.append("Salam hangat,")
    lines.append("Tim ClientFinder")
    return "\n".join(lines)
