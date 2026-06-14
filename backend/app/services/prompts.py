"""
Backend prompt builder — generates the prompts the LLM sees.

This is the BACKEND version (used to construct actual prompts sent
to the LLM). The frontend has a `prompt-builder.ts` with the same
templates for client-side preview/debug.
"""
from __future__ import annotations

from typing import Any


# --- Hook generation ---

HOOK_GENERATION_SYSTEM = (
    "Anda adalah sales copywriter senior yang ahli dalam Bahasa Indonesia. "
    "Anda membantu UMKM owner untuk menulis pesan outreach yang personal, "
    "ringkas, dan value-driven. Selalu rujuk ke pain point spesifik dan "
    "industri bisnis. Output HARUS JSON valid."
)

HOOK_GENERATION_USER_TEMPLATE = """\
# KONTEKS BISNIS

**Nama**: {company_name}
**Industri**: {industry}
**Lokasi**: {location}
**Website**: {website}

# PAIN POINTS TERDETEKSI

{pains_block}

# TECH STACK / DIGITAL PRESENCE

{tech_block}

# TUGAS

Buat 3 sudut outreach (hooks) yang highly personalized berdasarkan data di atas.
Setiap hook adalah opening line untuk pesan email/WA pertama, dengan struktur:
- "audit_finding": Masalah spesifik yang diobservasi (1 kalimat)
- "hook_text": Opening line (max 280 karakter, casual tapi profesional)
- "recommended_service": Layanan kami yang paling cocok (1-3 kata)
- "confidence": 0.0-1.0, seberapa yakin hook ini akan resonansi

# OUTPUT FORMAT (JSON, TIDAK ADA TEKS LAIN)

{{
  "hooks": [
    {{
      "audit_finding": "...",
      "hook_text": "...",
      "recommended_service": "...",
      "confidence": 0.0
    }}
  ]
}}
"""


def build_hook_prompt(
    *,
    company_name: str,
    industry: str | None,
    location: str | None,
    website: str | None,
    pains: list[dict],
    tech: dict | None,
) -> tuple[str, str]:
    """
    Build (system, user) prompt tuple for hook generation.

    Returns the system prompt and the user prompt.
    """
    pains_block = _format_pains(pains)
    tech_block = _format_tech(tech)
    user = HOOK_GENERATION_USER_TEMPLATE.format(
        company_name=company_name,
        industry=industry or "tidak diketahui",
        location=location or "tidak diketahui",
        website=website or "tidak ada",
        pains_block=pains_block,
        tech_block=tech_block,
    )
    return HOOK_GENERATION_SYSTEM, user


def _format_pains(pains: list[dict]) -> str:
    if not pains:
        return "(tidak ada pain points yang terdeteksi)"
    lines = []
    for i, p in enumerate(pains, 1):
        sev = p.get("severity", "?")
        kind = p.get("kind", "?")
        title = p.get("title", "")
        desc = p.get("description", "")
        lines.append(f"{i}. **[{sev}/100] {kind}** — {title}\n   {desc}")
    return "\n\n".join(lines)


def _format_tech(tech: dict | None) -> str:
    if not tech:
        return "(tidak ada data tech stack)"
    parts: list[str] = []
    cms = tech.get("cms")
    if cms:
        parts.append(f"- CMS: {cms}")
    framework = tech.get("framework")
    if framework:
        parts.append(f"- Framework: {framework}")
    hosting = tech.get("hosting_provider")
    if hosting:
        parts.append(f"- Hosting: {hosting}")
    ssl = tech.get("has_ssl")
    if ssl is True:
        parts.append("- SSL: ✓ aktif")
    elif ssl is False:
        parts.append("- SSL: ✗ tidak aktif (security risk)")
    speed = tech.get("page_speed_score")
    if speed is not None:
        parts.append(f"- PageSpeed score: {speed}/100")
    issues = tech.get("issues", [])
    if issues:
        parts.append(f"- Issues: {', '.join(issues)}")
    return "\n".join(parts) if parts else "(tidak ada info tech stack)"


# --- Pain analysis (richer) ---

PAIN_ANALYSIS_SYSTEM = (
    "Anda adalah digital marketing analyst untuk UMKM Indonesia. "
    "Anda ahli dalam mengidentifikasi masalah operasional, digital "
    "presence, dan growth blockers. Output HARUS JSON valid."
)

PAIN_ANALYSIS_USER_TEMPLATE = """\
# PROSPECT

{company_name} ({industry}, {location})
Website: {website}

# DATA YANG SUDAH DIKUMPULKAN

{existing_pains}

# TUGAS

Berdasarkan data di atas, identifikasi 2-4 pain points tambahan yang TIDAK
tertangkap oleh heuristic. Berikan:
- "kind": identifier machine
- "title": judul Bahasa Indonesia
- "description": 1-2 kalimat kenapa ini penting
- "severity": 0-100
- "recommended_service": layanan kami yang cocok

# OUTPUT (JSON only, no prose)

{{
  "additional_pains": [
    {{"kind": "...", "title": "...", "description": "...", "severity": 0, "recommended_service": "..."}}
  ]
}}
"""


def build_pain_analysis_prompt(
    *,
    company_name: str,
    industry: str | None,
    location: str | None,
    website: str | None,
    existing_pains: list[dict],
) -> tuple[str, str]:
    user = PAIN_ANALYSIS_USER_TEMPLATE.format(
        company_name=company_name,
        industry=industry or "?",
        location=location or "?",
        website=website or "tidak ada",
        existing_pains=_format_pains(existing_pains),
    )
    return PAIN_ANALYSIS_SYSTEM, user


# --- Outreach email (T6 prep) ---

OUTREACH_SYSTEM = (
    "Anda adalah copywriter untuk pesan outreach B2B Indonesia. "
    "Tulis pesan yang sopan, ringkas, tidak salesy, dan value-driven. "
    "Bahasa Indonesia yang natural dan profesional."
)

OUTREACH_EMAIL_USER_TEMPLATE = """\
# PROSPECT

{company_name}, {industry}, {location}

# HOOK YANG DIPILIH

{hook_text}

# PAIN POINTS

{pains_block}

# TUGAS

Tulis email outreach (subject + body) berdasarkan hook di atas.
- Subject: max 60 karakter, jangan clickbait
- Body: max 150 kata, paragraf pendek, 1 CTA
- Tone: santai tapi profesional (seperti peer yang punya insight)
- Akhiri dengan signature: "Salam,\nTim ClientFinder"

# OUTPUT (JSON only)

{{
  "subject": "...",
  "body": "..."
}}
"""


def build_outreach_email_prompt(
    *,
    company_name: str,
    industry: str | None,
    location: str | None,
    hook_text: str,
    pains: list[dict],
) -> tuple[str, str]:
    user = OUTREACH_EMAIL_USER_TEMPLATE.format(
        company_name=company_name,
        industry=industry or "tidak diketahui",
        location=location or "tidak diketahui",
        hook_text=hook_text,
        pains_block=_format_pains(pains),
    )
    return OUTREACH_SYSTEM, user


# --- Social Signal Classification (T9.0 / Sprint 2 sub-task 2.4) ---

SOCIAL_SIGNAL_CLASSIFICATION_SYSTEM = (
    "Anda adalah social signal detector untuk sales prospecting. "
    "Tugas Anda: dari daftar post Twitter/Threads publik, identifikasi "
    "post yang menunjukkan orang atau bisnis MEMBUTUHKAN SOFTWARE "
    "(developer, automation, AI, web, mobile, ERP/CRM, dsb). "
    "Output HARUS JSON valid dengan schema yang diberikan."
)

SOCIAL_SIGNAL_KINDS = [
    "hiring_developer",       # Posting lowongan / cari developer / butuh web baru
    "need_software",           # Cari software / aplikasi / tools baru
    "need_automation",         # Mengeluh proses manual / cari automation
    "need_ai",                 # Butuh AI / integrasi AI
    "need_website",            # Website lama / tidak ada / perlu redesign
    "complaint_manual",        # Mengeluh proses repetitif / manual
    "launching_product",       # Sedang launching produk / fitur baru
    "expansion",               # Buka cabang / ekspansi
    "funding",                 # Sedang cari investor / funding
    "digital_transformation",  # Digital transformation announcement
    "other",                   # Sinyal lain yang relevan
]


def build_social_signal_classification_prompt(
    posts: list[dict],
) -> tuple[str, str]:
    """Build the (system, user) prompt pair for LLM signal classification.

    `posts` is a list of {text, author_handle, url, timestamp, language}
    dicts (typically SocialPost.to_dict() output).
    """
    import json as _json
    kinds_list = _json.dumps(SOCIAL_SIGNAL_KINDS, ensure_ascii=False)
    posts_block = _json.dumps(
        [{"i": i, **p} for i, p in enumerate(posts)],
        ensure_ascii=False,
        indent=2,
    )
    user = f"""\
# TUGAS

Dari daftar {len(posts)} post publik di bawah, identifikasi post yang
menunjukkan SINYAL KEBUTUHAN SOFTWARE. Untuk setiap sinyal, output
JSON dengan field:

- i: index post (0-based)
- kind: salah satu dari {kinds_list}
- severity: 0-100 (confidence + strength of the signal)
- evidence_text: kutipan langsung dari post (1-2 kalimat)
- rationale: kenapa ini sinyal yang relevan

Hanya output post yang BENAR-BENAR menunjukkan kebutuhan software.
Lewati post yang tidak relevan (chit-chat, promosi, opini, dll).

# POSTS

{posts_block}

# OUTPUT (JSON array, no other text)
"""
    return SOCIAL_SIGNAL_CLASSIFICATION_SYSTEM, user
