"""
Template factory — T6 / Sprint 3A multi-channel outreach.

Per the brief, the platform should send personalized outreach
across email + WhatsApp with per-industry tone. Templates are
content-shaped; the factory picks the right one, fills variables,
and returns a renderable body.

Templates are stored in the DB (Template model). On first run
this module seeds a baseline library:

  Channel × Category × Industry
  - 2 channels (email, whatsapp) × 3 categories (first_touch,
    follow_up, breakup) × 5 industries (fnb, retail, klinik,
    salon, jasa) = 30 templates

For unspecialised industries, the factory falls back to a
generic "umum" library.

Variables: {company_name}, {owner_name}, {industry},
{location}, {pain_summary}, {sender_name}.

Per R10 (human-in-the-loop): rendered bodies are not auto-sent.
The drip runner (drip_runner.py) persists the Message with
status='pending_approval'; an operator must approve before
send_message_now() dispatches.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach import Template

logger = logging.getLogger("clientfinder.outreach.template_factory")

# --- Industry canonical names (kept in sync with brief) ---

INDUSTRY_FNB = "fnb"            # food & beverage / restoran / kafe
INDUSTRY_RETAIL = "retail"      # toko / minimarket / online shop
INDUSTRY_KLINIK = "klinik"      # klinik / apotek / healthcare
INDUSTRY_SALON = "salon"        # salon / spa / fitness / beauty
INDUSTRY_JASA = "jasa"          # konsultan / B2B service / agency
INDUSTRY_UMUM = "umum"          # fallback for unknown industries

INDUSTRIES = [INDUSTRY_FNB, INDUSTRY_RETAIL, INDUSTRY_KLINIK,
              INDUSTRY_SALON, INDUSTRY_JASA, INDUSTRY_UMUM]

# Map raw industry strings (from prospect) to canonical names
INDUSTRY_ALIASES: dict[str, str] = {
    "restoran": INDUSTRY_FNB, "kafe": INDUSTRY_FNB, "fnb": INDUSTRY_FNB,
    "warung": INDUSTRY_FNB, "rumah makan": INDUSTRY_FNB,
    "toko": INDUSTRY_RETAIL, "minimarket": INDUSTRY_RETAIL,
    "retail": INDUSTRY_RETAIL, "online": INDUSTRY_RETAIL,
    "klinik": INDUSTRY_KLINIK, "apotek": INDUSTRY_KLINIK,
    "dokter": INDUSTRY_KLINIK, "rumah sakit": INDUSTRY_KLINIK,
    "salon": INDUSTRY_SALON, "spa": INDUSTRY_SALON,
    "fitness": INDUSTRY_SALON, "gym": INDUSTRY_SALON, "barbershop": INDUSTRY_SALON,
    "konsultan": INDUSTRY_JASA, "jasa": INDUSTRY_JASA,
    "agency": INDUSTRY_JASA, "agensi": INDUSTRY_JASA, "b2b": INDUSTRY_JASA,
    "service": INDUSTRY_JASA,
    "umum": INDUSTRY_UMUM, "other": INDUSTRY_UMUM, "lain": INDUSTRY_UMUM,
}


def canonicalize_industry(raw: str | None) -> str:
    """Map a raw industry string to one of INDUSTRIES. Returns
    INDUSTRY_UMUM if no match.

    Matching strategy (in order):
      1. Exact match against INDUSTRY_ALIASES keys
      2. Substring match on alphanumeric-stripped form
         (e.g. "FN B" → "fnb" via "fnb" in "fnb";
               "Klinik Gigi" → "klinik" via "klinik" in "klinikgigi";
               "agensi" → "jasa" via "agensi" in "agensi" wait — agent
               not in aliases. We add "agensi" alias.)
      3. Fallback: INDUSTRY_UMUM
    """
    if not raw:
        return INDUSTRY_UMUM
    r = raw.strip().lower()
    # 1. Exact match
    if r in INDUSTRY_ALIASES:
        return INDUSTRY_ALIASES[r]
    # 2. Substring match (alphanumeric-stripped, longer alias first)
    r_clean = "".join(c for c in r if c.isalnum())
    for alias in sorted(INDUSTRY_ALIASES.keys(), key=len, reverse=True):
        alias_clean = "".join(c for c in alias if c.isalnum())
        if alias_clean and (
            alias_clean in r_clean or r_clean in alias_clean
        ):
            return INDUSTRY_ALIASES[alias]
    return INDUSTRY_UMUM


# --- Categories ---

CATEGORY_FIRST_TOUCH = "first_touch"
CATEGORY_FOLLOW_UP = "follow_up"
CATEGORY_BREAKUP = "breakup"

CATEGORIES = [CATEGORY_FIRST_TOUCH, CATEGORY_FOLLOW_UP, CATEGORY_BREAKUP]


# --- Variable substitution ---

# Default values for missing variables (graceful degradation)
VAR_DEFAULTS: dict[str, str] = {
    "company_name": "Bapak/Ibu",
    "owner_name": "Bapak/Ibu",
    "industry": "tidak diketahui",
    "location": "Indonesia",
    "pain_summary": "beberapa area yang bisa kami bantu",
    "sender_name": "Tim ClientFinder",
}

# Whitelist of allowed variable names (prevents template injection)
ALLOWED_VARS = set(VAR_DEFAULTS.keys()) | {"company_name"}


def render_template(
    body: str,
    variables: dict[str, str],
) -> str:
    """Substitute {var} placeholders. Unknown vars get VAR_DEFAULTS."""
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in variables and variables[key]:
            return str(variables[key])
        return VAR_DEFAULTS.get(key, m.group(0))
    return re.sub(r"\{([a-z_][a-z_0-9]*)\}", repl, body)


# --- Seed library (per industry × category × channel) ---

# Body templates use {{double-brace}} for f-string safety, then
# converted to {single} for the variable substitution.
def _seed_library() -> list[dict[str, Any]]:
    """Return the full template library for first-run seeding."""
    out: list[dict[str, Any]] = []

    # F&B / restoran
    out += [
        _tmpl(INDUSTRY_FNB, "email", CATEGORY_FIRST_TOUCH,
              "Halo {owner_name} — automate pesanan {company_name}?",
              "Halo {owner_name},\n\nSaya perhatikan {company_name} di {location} ramai pengunjung. "
              "Apakah saat ini pesanan masih dicatat manual atau sudah pakai sistem POS? "
              "Banyak restoran F&B di area {location} sudah pakai sistem pemesanan otomatis — "
              "lebih hemat waktu dan mengurangi salah catat.\n\n"
              "Boleh kami kirim info singkat 5 menit? Gratis, tidak ada komitmen.\n\n"
              "{sender_name}"),
        _tmpl(INDUSTRY_FNB, "whatsapp", CATEGORY_FIRST_TOUCH,
              None,  # WA has no subject
              "Halo {owner_name} 👋 Saya dari ClientFinder. "
              "Saya lihat {company_name} ({location}) — boleh tanya singkat, "
              "sekarang pesanan masih manual di buku atau sudah ada sistem? 🙏"),
        _tmpl(INDUSTRY_FNB, "email", CATEGORY_FOLLOW_UP,
              "Re: {company_name} — case study F&B",
              "Halo {owner_name},\n\nMau follow up pesan sebelumnya. "
              "Saya attach studi kasus restoran F&B di {location} yang sudah hemat 12 jam/minggu "
              "setelah pakai sistem pemesanan otomatis.\n\n"
              "Boleh saya tunjukkan? 10 menit saja.\n\n{sender_name}"),
        _tmpl(INDUSTRY_FNB, "whatsapp", CATEGORY_FOLLOW_UP,
              None,
              "Halo {owner_name}, mau follow up singkat soal {company_name} 🙏 "
              "Kirim studi kasus F&B (10 menit), boleh?"),
        _tmpl(INDUSTRY_FNB, "email", CATEGORY_BREAKUP,
              "Salam perpisahan — {company_name}",
              "Halo {owner_name},\n\nSaya coba hubungi beberapa kali. "
              "Mungkin sekarang bukan waktu yang tepat — tidak apa-apa. "
              "Kalau di kemudian hari {company_name} butuh bantuan otomasi, "
              "jangan sungkan hubungi kami.\n\nSemoga lancar selalu! 🙏\n\n{sender_name}"),
    ]
    # Retail
    out += [
        _tmpl(INDUSTRY_RETAIL, "email", CATEGORY_FIRST_TOUCH,
              "{company_name} — inventaris online?",
              "Halo {owner_name},\n\nUntuk toko retail di {location}, "
              "sistem inventaris online biasanya hemat 8-10 jam/minggu "
              "dan kurangi stock-out.\n\n{company_name} pakai sistem apa sekarang? "
              "Boleh saya tunjukkan demo 5 menit?\n\n{sender_name}"),
        _tmpl(INDUSTRY_RETAIL, "whatsapp", CATEGORY_FIRST_TOUCH,
              None,
              "Halo {owner_name} 👋 Lihat {company_name} ({location}) — "
              "stok barang masih di buku besar atau sudah pakai sistem? 🙏"),
        _tmpl(INDUSTRY_RETAIL, "email", CATEGORY_FOLLOW_UP,
              "Re: inventaris {company_name}",
              "Halo {owner_name},\n\nMau follow up soal inventaris {company_name}. "
              "Saya attach contoh dashboard sederhana yang biasa kami tunjukkan — "
              "15 menit demo, tidak ada komitmen.\n\nBoleh dicoba?\n\n{sender_name}"),
        _tmpl(INDUSTRY_RETAIL, "email", CATEGORY_BREAKUP,
              "Penutup — {company_name}",
              "Halo {owner_name},\n\nBeberapa kali coba kontak, tidak ada respons. "
              "Tidak masalah — semoga {company_name} makin sukses. "
              "Kalau suatu saat butuh, kami siap bantu.\n\n{sender_name}"),
    ]
    # Klinik
    out += [
        _tmpl(INDUSTRY_KLINIK, "email", CATEGORY_FIRST_TOUCH,
              "Antrian pasien {company_name} — bisa di-booking online?",
              "Halo {owner_name},\n\nUntuk klinik di {location}, sistem booking online "
              "mengurangi no-show 30-50% dan hemat waktu resepsionis.\n\n"
              "{company_name} sudah pakai sistem antrian online? "
              "Boleh kirim demo singkat?\n\n{sender_name}"),
        _tmpl(INDUSTRY_KLINIK, "whatsapp", CATEGORY_FIRST_TOUCH,
              None,
              "Halo {owner_name} 🙏 {company_name} ({location}) — antrian pasien "
              "masih manual atau sudah ada sistem booking online?"),
        _tmpl(INDUSTRY_KLINIK, "email", CATEGORY_FOLLOW_UP,
              "Re: booking online {company_name}",
              "Halo {owner_name},\n\nFollow up soal booking online {company_name}. "
              "Saya bisa tunjukkan bagaimana klinik di {location} kurangi no-show 35% "
              "dengan sistem WhatsApp-based. 10 menit demo, gratis.\n\nBoleh?\n\n{sender_name}"),
        _tmpl(INDUSTRY_KLINIK, "email", CATEGORY_BREAKUP,
              "Salam — {company_name}",
              "Halo {owner_name},\n\nTidak ada respons dari beberapa email. "
              "Semoga {company_name} lancar. Bila di kemudian hari butuh "
              "solusi digital untuk klinik, kami siap.\n\n{sender_name}"),
    ]
    # Salon
    out += [
        _tmpl(INDUSTRY_SALON, "whatsapp", CATEGORY_FIRST_TOUCH,
              None,
              "Halo {owner_name} 👋 {company_name} ({location}) — booking顾客 masih "
              "lewat telepon / walk-in? Boleh tanya 1 menit soal sistem booking online 🙏"),
        _tmpl(INDUSTRY_SALON, "email", CATEGORY_FOLLOW_UP,
              "Re: booking system {company_name}",
              "Halo {owner_name},\n\nFollow up soal sistem booking {company_name}. "
              "Salon yang pakai sistem online biasanya lihat 20-30% lebih banyak repeat customer. "
              "Boleh kirim demo singkat?\n\n{sender_name}"),
        _tmpl(INDUSTRY_SALON, "whatsapp", CATEGORY_BREAKUP,
              None,
              "Halo {owner_name}, tidak apa-apa kalau bukan sekarang. "
              "Semoga {company_name} makin rame 🙏"),
    ]
    # Jasa / konsultan
    out += [
        _tmpl(INDUSTRY_JASA, "email", CATEGORY_FIRST_TOUCH,
              "{company_name} — sistem follow-up klien?",
              "Halo {owner_name},\n\nUntuk konsultan / agensi di {location}, "
              "sistem follow-up klien otomatis biasanya hemat 5-8 jam/minggu.\n\n"
              "{company_name} sudah ada sistem CRM / follow-up klien? "
              "Boleh kirim info singkat?\n\n{sender_name}"),
        _tmpl(INDUSTRY_JASA, "email", CATEGORY_FOLLOW_UP,
              "Re: CRM {company_name}",
              "Halo {owner_name},\n\nMau follow up soal CRM {company_name}. "
              "Saya bisa tunjukkan template follow-up yang biasa dipakai konsultan — "
              "10 menit demo, tidak ada komitmen.\n\n{sender_name}"),
        _tmpl(INDUSTRY_JASA, "whatsapp", CATEGORY_BREAKUP,
              None,
              "Halo {owner_name}, sudah coba beberapa kali — tidak apa-apa 🙏 "
              "Semoga {company_name} makin sukses."),
    ]
    # Umum (fallback)
    out += [
        _tmpl(INDUSTRY_UMUM, "email", CATEGORY_FIRST_TOUCH,
              "Halo {owner_name} dari {company_name}",
              "Halo {owner_name},\n\nSaya perhatikan {company_name} di {location}. "
              "Boleh tanya singkat — {pain_summary}?\n\n"
              "Kami bisa bantu dengan otomasi sederhana. Boleh saya kirim info 5 menit?\n\n{sender_name}"),
        _tmpl(INDUSTRY_UMUM, "whatsapp", CATEGORY_FIRST_TOUCH,
              None,
              "Halo {owner_name} 👋 Lihat {company_name} ({location}) — "
              "boleh tanya 1 menit soal {pain_summary}? 🙏"),
        _tmpl(INDUSTRY_UMUM, "email", CATEGORY_FOLLOW_UP,
              "Re: {company_name}",
              "Halo {owner_name},\n\nFollow up singkat — boleh saya kirim studi kasus "
              "yang relevan untuk {industry}? 10 menit demo, tidak ada komitmen.\n\n{sender_name}"),
        _tmpl(INDUSTRY_UMUM, "whatsapp", CATEGORY_BREAKUP,
              None,
              "Halo {owner_name}, tidak apa-apa kalau bukan sekarang 🙏"),
    ]
    return out


def _tmpl(
    industry: str,
    channel: str,
    category: str,
    subject: str | None,
    body: str,
) -> dict[str, Any]:
    """Helper to build a template dict for the seed library."""
    return {
        "name": f"{industry}_{channel}_{category}",
        "channel": channel,
        "category": category,
        "industry": industry,  # stored in variables
        "subject": subject,
        "body": body,
        "variables": ["company_name", "owner_name", "industry",
                      "location", "pain_summary", "sender_name"],
        "is_active": True,
    }


async def seed_template_library(db: AsyncSession) -> int:
    """Seed the template library on first run. Idempotent: only
    inserts templates whose name doesn't already exist.

    Returns the count of newly inserted templates.
    """
    existing_names = set(
        (await db.execute(select(Template.name))).scalars().all()
    )
    seeded = 0
    for tmpl in _seed_library():
        if tmpl["name"] in existing_names:
            continue
        # Industry goes into the variables list (used by the factory)
        # but we don't have an industry column on the model. Encode
        # the industry in the variables JSON: a special key
        # "_industry": tmpl["industry"]. That keeps the factory
        # logic clean.
        variables = list(tmpl["variables"]) + [f"_industry:{tmpl['industry']}"]
        db.add(
            Template(
                name=tmpl["name"],
                channel=tmpl["channel"],
                category=tmpl["category"],
                subject=tmpl["subject"],
                body=tmpl["body"],
                variables=variables,
                is_active=tmpl["is_active"],
            )
        )
        seeded += 1
    if seeded:
        await db.commit()
        logger.info("Seeded %d new templates", seeded)
    return seeded


# --- Template picker ---

async def pick_template(
    db: AsyncSession,
    *,
    channel: str,
    category: str,
    industry: str | None,
) -> Template | None:
    """Pick the best template for (channel, category, industry).

    Strategy:
      1. Try (channel, category, canonical_industry)
      2. Fall back to (channel, category, INDUSTRY_UMUM)
      3. Fall back to ANY (channel, category)

    Returns the first match or None.
    """
    canon = canonicalize_industry(industry)

    # Strategy 1: industry-specific
    t = await _find_template(db, channel, category, industry_match=canon)
    if t:
        return t

    # Strategy 2: industry-umum
    t = await _find_template(db, channel, category, industry_match=INDUSTRY_UMUM)
    if t:
        return t

    # Strategy 3: any template for (channel, category)
    t = await _find_template(db, channel, category, industry_match=None)
    return t


async def _find_template(
    db: AsyncSession,
    channel: str,
    category: str,
    industry_match: str | None,
) -> Template | None:
    """Helper: find a template matching the criteria. Industry is
    stored as a special '_industry:NAME' entry in the variables
    JSONB column."""
    candidates = (
        await db.execute(
            select(Template).where(
                Template.channel == channel,
                Template.category == category,
                Template.is_active == True,  # noqa: E712
            )
        )
    ).scalars().all()
    for t in candidates:
        vars_ = t.variables or []
        for v in vars_:
            if isinstance(v, str) and v.startswith("_industry:"):
                ind = v.split(":", 1)[1]
                if industry_match is None or ind == industry_match:
                    return t
    return None


async def render_for_prospect(
    db: AsyncSession,
    *,
    channel: str,
    category: str,
    industry: str | None,
    variables: dict[str, str],
) -> dict[str, str | None]:
    """High-level helper: pick a template + render it. Returns
    {subject, body, template_id}. subject may be None (e.g. WhatsApp).
    """
    tmpl = await pick_template(
        db, channel=channel, category=category, industry=industry,
    )
    if not tmpl:
        logger.warning(
            "No template for channel=%s category=%s industry=%s",
            channel, category, industry,
        )
        return {"subject": None, "body": "", "template_id": None}
    body = render_template(tmpl.body, variables)
    subject = render_template(tmpl.subject, variables) if tmpl.subject else None
    return {
        "subject": subject,
        "body": body,
        "template_id": str(tmpl.id),
    }
