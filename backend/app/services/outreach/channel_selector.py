"""
Channel auto-pick — T6 / Sprint 3A multi-channel outreach.

Per the brief and R9/D116:
- Email is the primary outreach channel for businesses with
  known email
- WhatsApp is the fallback (and primary for F&B / retail /
  klinik in Indonesia — response rates are higher)
- Threads DM: TODO (T6.2)

Per R9: never send a "we got your email/phone from public
sources" message — both channels must be normalized. This
module just picks the channel; the message body is
responsibility of the template_factory.

Strategy (in order of preference):
  1. WhatsApp — if the prospect has a phone number. Preferred
     for high-engagement industries (F&B, retail, klinik, salon)
  2. Email — if the prospect has an email
  3. None — skip the prospect; log a warning

The "preferred_channel" override lets a sequence force a
specific channel. The selector still returns None if the
required contact field is missing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.models.prospect import Prospect

logger = logging.getLogger("clientfinder.outreach.channel_selector")


# Industries where WhatsApp outperforms email response-wise
WA_PREFERRED_INDUSTRIES = {"fnb", "retail", "klinik", "salon"}


@dataclass
class ChannelPick:
    channel: str | None     # "email" | "whatsapp" | None
    recipient: str | None   # the email or phone
    reason: str             # why this channel was chosen

    def __bool__(self) -> bool:
        return self.channel is not None


def _normalize_phone(phone: str | None) -> str | None:
    """Phone must be in international format for WAHA.
    Convert 08xx → +62xxx (Indonesia)."""
    if not phone:
        return None
    p = phone.strip().replace(" ", "").replace("-", "")
    if not p:
        return None
    if p.startswith("+"):
        return p
    if p.startswith("00"):
        return "+" + p[2:]
    if p.startswith("0"):
        return "+62" + p[1:]
    if p.startswith("62"):
        return "+" + p
    # fallback: assume already international without +
    return "+" + p


def pick_channel(
    prospect: Prospect,
    *,
    preferred_channel: str | None = None,
    industry_canonical: str | None = None,
) -> ChannelPick:
    """Decide which channel to use for a given prospect.

    Args:
      prospect: the Prospect model instance
      preferred_channel: optional override ('email' | 'whatsapp')
      industry_canonical: one of INDUSTRIES from template_factory
        (used to bias toward WhatsApp for F&B/retail/etc.)

    Returns: ChannelPick with channel/recipient/reason. If both
      contact fields are missing, returns ChannelPick(None, None, reason).
    """
    email = (prospect.email or "").strip()
    phone = _normalize_phone(prospect.phone)

    # Override path: honor preferred_channel strictly
    if preferred_channel == "email":
        if email:
            return ChannelPick("email", email, "preferred:email with contact")
        return ChannelPick(None, None, "preferred:email but no email contact")
    if preferred_channel == "whatsapp":
        if phone:
            return ChannelPick("whatsapp", phone, "preferred:whatsapp with contact")
        return ChannelPick(None, None, "preferred:whatsapp but no phone contact")

    # Auto-pick: industry-aware
    has_email = bool(email)
    has_phone = bool(phone)
    if not has_email and not has_phone:
        return ChannelPick(None, None, "no email and no phone on prospect")

    if has_phone and industry_canonical in WA_PREFERRED_INDUSTRIES:
        return ChannelPick("whatsapp", phone, f"industry:{industry_canonical} WA-first")
    if has_email and not has_phone:
        return ChannelPick("email", email, "phone missing, email present")
    if has_phone and not has_email:
        return ChannelPick("whatsapp", phone, "email missing, phone present")
    # Both present, industry not WA-preferred → email first (less intrusive)
    return ChannelPick("email", email, "both contacts, default email-first")
