"""
Pain detection — heuristic rules for Indonesian UMKM (T5, A29).

Detects:
  - no_website: no URL at all (high pain)
  - stale_website: website but no SSL or looks old (medium)
  - slow_site: response time > 3s (medium)
  - no_booking_system: industry would benefit but no online booking
  - no_wa_business: no WhatsApp link in website
  - no_pos: F&B / retail but no POS hint
  - no_gbp: Google Business Profile missing (we don't check this
    here, but the rule exists for future enrichment)
  - no_email: no business email listed
  - no_phone: no phone number
  - no_mobile_friendly: no <meta name="viewport"> tag (Sprint 1 / Phase 1.2)
  - has_console_errors: JS console errors on the page (Sprint 1 / Phase 1.2)
  - no_payment_system: no payment gateway detected on the site
    (Sprint 1 / Phase 1.2)

Each pain has:
  - kind: machine identifier
  - severity: 0-100 (how bad)
  - title: human title
  - description: why this matters
  - recommended_service: what we'd offer to fix
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Pain:
    """A single detected pain point."""

    kind: str
    severity: int
    title: str
    description: str
    recommended_service: str
    evidence: dict = field(default_factory=dict)


def detect_pains(
    *,
    website: str | None,
    industry: str | None,
    location_city: str | None,
    has_phone: bool,
    has_email: bool,
    has_wa_business: bool = False,
    has_booking_system: bool = False,
    has_pos: bool = False,
    response_time_ms: int | None = None,
    has_ssl: bool = True,
    # Sprint 1 / Phase 1.2 — 3 new audit signals
    has_viewport_meta: bool = True,
    payment_gateways: list[str] | None = None,
    console_errors: list[str] | None = None,
) -> list[dict]:
    """
    Run heuristic pain detection on a prospect.

    Returns a list of pain dicts ready to insert into the
    `pain_points` table.
    """
    pains: list[Pain] = []
    industry_key = (industry or "").lower().strip()
    payment_gateways = payment_gateways or []
    console_errors = console_errors or []

    # Rule 1: No website at all
    if not website:
        pains.append(
            Pain(
                kind="no_website",
                severity=90,
                title="Tidak punya website",
                description=(
                    "Bisnis tanpa website kehilangan ~70% calon pelanggan "
                    "yang mencari online. Kompetitor Anda sudah punya."
                ),
                recommended_service="web_dev",
                evidence={},
            )
        )
    else:
        # Rule 2: No SSL (http://, not https://)
        if not has_ssl:
            pains.append(
                Pain(
                    kind="no_ssl",
                    severity=40,
                    title="Website tanpa SSL",
                    description=(
                        "Browser modern menampilkan 'Not Secure' untuk HTTP. "
                        "Menurunkan trust + SEO ranking."
                    ),
                    recommended_service="web_dev",
                    evidence={"url": website},
                )
            )
        # Rule 3: Slow site
        if response_time_ms is not None and response_time_ms > 3000:
            pains.append(
                Pain(
                    kind="slow_site",
                    severity=50,
                    title="Website lambat",
                    description=(
                        f"Response time {response_time_ms}ms (target <1000ms). "
                        "53% pengunjung mobile meninggalkan situs yang >3 detik."
                    ),
                    recommended_service="perf_optimization",
                    evidence={"response_time_ms": response_time_ms},
                )
            )
        # Rule 4: No WA link
        if not has_wa_business:
            pains.append(
                Pain(
                    kind="no_wa_business",
                    severity=55,
                    title="Tidak ada WhatsApp Business",
                    description=(
                        "WA adalah channel utama customer service di Indonesia. "
                        "Tanpa WA business link, pelanggan tidak bisa hubungi Anda."
                    ),
                    recommended_service="wa_business_setup",
                    evidence={},
                )
            )

    # Rule 5: No booking system (for service industries)
    service_industries = {"klinik", "salon", "spa", "fitness", "bengkel"}
    if any(k in industry_key for k in service_industries) and not has_booking_system:
        pains.append(
            Pain(
                kind="no_booking_system",
                severity=65,
                title="Booking masih manual",
                description=(
                    f"Untuk industri {industry}, sistem booking online "
                    "mengurangi no-show 40% dan节省 staff time."
                ),
                recommended_service="booking_app",
                evidence={"industry": industry},
            )
        )

    # Rule 6: No POS (for F&B / retail)
    pos_industries = {"restoran", "kafe", "fnb", "minimarket", "apotek", "toko"}
    if any(k in industry_key for k in pos_industries) and not has_pos:
        pains.append(
            Pain(
                kind="no_pos",
                severity=60,
                title="Tidak pakai POS system",
                description=(
                    f"Bisnis {industry} tanpa POS kehilangan visibility "
                    "atas inventory + sales. Manual bookkeeping = error 8-12%."
                ),
                recommended_service="pos_system",
                evidence={"industry": industry},
            )
        )

    # Rule 7: No email listed
    if not has_email:
        pains.append(
            Pain(
                kind="no_email",
                severity=30,
                title="Email bisnis tidak tersedia",
                description=(
                    "Email profesional (e.g. info@bisnis.com) penting untuk "
                    "B2B communication, invoice, dan branding."
                ),
                recommended_service="email_setup",
                evidence={},
            )
        )

    # Rule 8: No phone
    if not has_phone:
        pains.append(
            Pain(
                kind="no_phone",
                severity=25,
                title="Nomor telepon tidak ada",
                description=(
                    "Bisnis tanpa nomor telepon sulit ditemukan di Google Maps "
                    "dan direktori lokal."
                ),
                recommended_service="gmb_setup",
                evidence={},
            )
        )

    # ----- Sprint 1 / Phase 1.2: 3 new audit signals -----

    # Rule 9: No mobile-friendly viewport meta tag
    # Default to True so legacy callers (without the new param) don't
    # trip the rule by accident. When called with has_viewport_meta=False,
    # we add the pain.
    if not has_viewport_meta:
        pains.append(
            Pain(
                kind="no_mobile_friendly",
                severity=70,
                title="Website tidak mobile-friendly",
                description=(
                    "Tanpa <meta name='viewport'>, website tidak responsive di mobile. "
                    "75% traffic UMKM Indonesia dari HP, dan bounce rate naik "
                    "3x lipat untuk site yang tidak mobile-friendly."
                ),
                recommended_service="responsive_redesign",
                evidence={"signal": "no_viewport_meta"},
            )
        )

    # Rule 10: Console errors detected on the page
    # Only fire if there are multiple (1 transient error is normal;
    # 3+ suggests a broken page)
    if len(console_errors) >= 3:
        pains.append(
            Pain(
                kind="has_console_errors",
                severity=45,
                title=f"{len(console_errors)} console errors",
                description=(
                    f"Halaman memunculkan {len(console_errors)} error JavaScript. "
                    "Kemungkinan: resource 404, library conflict, atau "
                    "script error. Menurunkan trust + UX."
                ),
                recommended_service="frontend_debug",
                evidence={
                    "n_errors": len(console_errors),
                    "sample": console_errors[:5],
                },
            )
        )

    # Rule 11: No payment gateway detected (for relevant industries)
    # E-commerce / F&B / retail benefit from online payment. If they
    # have a website but no payment gateway, they're losing potential
    # online sales.
    ecommerce_industries = {
        "restoran", "kafe", "fnb", "minimarket", "toko", "klinik",
        "salon", "spa", "fitness", "apotek", "retail", "online",
    }
    if (
        any(k in industry_key for k in ecommerce_industries)
        and not payment_gateways
    ):
        pains.append(
            Pain(
                kind="no_payment_system",
                severity=60,
                title="Tidak ada payment gateway",
                description=(
                    f"Bisnis {industry} tanpa payment gateway online "
                    "(Midtrans, Xendit, Stripe, dll) kehilangan customer "
                    "yang mau bayar via QRIS / e-wallet / transfer."
                ),
                recommended_service="payment_integration",
                evidence={"industry": industry, "gateways_found": []},
            )
        )

    return [
        {
            "kind": p.kind,
            "severity": p.severity,
            "title": p.title,
            "description": p.description,
            "recommended_service": p.recommended_service,
            "evidence": p.evidence,
        }
        for p in pains
    ]


def summarize_pains(pains: Iterable[dict]) -> dict:
    """Aggregate stats for UI display."""
    ps = list(pains)
    if not ps:
        return {"count": 0, "avg_severity": 0, "max_severity": 0}
    sevs = [p.get("severity", 0) for p in ps]
    return {
        "count": len(ps),
        "avg_severity": round(sum(sevs) / len(sevs), 1),
        "max_severity": max(sevs),
    }
