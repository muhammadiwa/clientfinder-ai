"""
Backfill homepage enrichment for existing prospects (T8.6).

Idempotent. Finds prospects with a website but missing contact fields,
runs HomepageEnricher on each, and updates the row with the extracted
data. Re-running is a no-op once all prospects are enriched.

Usage:
    docker compose exec backend python -m scripts.backfill_enrichment
    docker compose exec backend python -m scripts.backfill_enrichment --dry-run
    docker compose exec backend python -m scripts.backfill_enrichment --source google --limit 50
    docker compose exec backend python -m scripts.backfill_enrichment --source all

Flags:
    --source SOURCE    'all' (default), 'google', or 'maps'
    --limit N          Process at most N prospects (default: unlimited)
    --dry-run          Preview the list of prospects + estimated time, no fetches

See docs/SCOUT_ENRICHMENT_SPEC.md section 6.3 for the design rationale.
"""
import argparse
import asyncio
import logging
import random
import sys
import time
from typing import Any

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.prospect import Prospect
from app.services.scraper.base import ScrapedResult
from app.services.scraper.enricher import HomepageEnricher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("clientfinder.scripts.backfill_enrichment")


def needs_enrichment(p: Prospect) -> bool:
    """A prospect is backfill-eligible if it has a website and at least
    one contact field is missing/empty. The spec (section 6.3) uses
    this exact filter.
    """
    if not p.website:
        return False
    if not p.phone:
        return True
    if not p.email:
        return True
    raw = p.raw_data or {}
    if not raw.get("location_address"):
        return True
    if not p.social_links:
        return True
    return False


def source_filter(source: str):
    """Build a SQL filter for the --source flag."""
    if source == "all":
        return None
    return Prospect.source == source


async def list_candidates(
    source: str, limit: int | None
) -> list[Prospect]:
    """Return all prospects that need enrichment, ordered by created_at DESC."""
    async with AsyncSessionLocal() as db:
        q = select(Prospect).where(
            Prospect.deleted_at.is_(None),
            Prospect.website.is_not(None),
            or_(
                Prospect.phone.is_(None),
                Prospect.email.is_(None),
            ),
        )
        sf = source_filter(source)
        if sf is not None:
            q = q.where(sf)
        q = q.order_by(Prospect.created_at.desc())
        if limit is not None:
            q = q.limit(limit)
        rows = (await db.execute(q)).scalars().all()
        # Python-side filter for raw_data.social_links (JSONB empty
        # check is awkward in SQL; spec says this is fine for v1)
        return [p for p in rows if needs_enrichment(p)]


async def enrich_one(
    enricher: HomepageEnricher, prospect: Prospect
) -> dict[str, Any]:
    """Run enricher on a single prospect; update the row; return result summary."""
    start = time.monotonic()
    raw = dict(prospect.raw_data or {})
    result = ScrapedResult(
        company_name=prospect.company_name,
        website=prospect.website,
        phone=prospect.phone,
        email=prospect.email,
        location_address=raw.get("location_address"),
        source=prospect.source or "manual",
        source_url=prospect.source_url,
        description=prospect.description,
        extra=raw,
    )
    try:
        await enricher.enrich_batch([result])
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "status": "error",
            "error": str(e),
            "ms": int((time.monotonic() - start) * 1000),
        }

    new_socials = result.extra.get("social") or {}
    updates: list[str] = []
    if result.phone and result.phone != prospect.phone:
        prospect.phone = result.phone
        updates.append("phone")
    if result.email and result.email != prospect.email:
        prospect.email = result.email
        updates.append("email")
    if result.location_address and not raw.get("location_address"):
        raw["location_address"] = result.location_address
        prospect.raw_data = raw
        updates.append("address")
    if new_socials:
        merged = {**(prospect.social_links or {}), **new_socials}
        prospect.social_links = merged
        updates.append("socials")
    if updates:
        async with AsyncSessionLocal() as db:
            db.add(prospect)
            await db.commit()
    return {
        "ok": True,
        "status": result.extra.get("enrichment_status", "no_data"),
        "updates": updates,
        "ms": int((time.monotonic() - start) * 1000),
    }


async def run(args: argparse.Namespace) -> int:
    source = args.source
    limit = args.limit
    dry_run = args.dry_run

    candidates = await list_candidates(source, limit)
    print(f"Found {len(candidates)} prospect(s) needing enrichment (source={source})")

    if not candidates:
        return 0

    # Estimate time: 3-8s per prospect (scraper_request_delay_min/max)
    delay_min = settings.scraper_request_delay_min
    delay_max = settings.scraper_request_delay_max
    est_s = len(candidates) * ((delay_min + delay_max) / 2)
    print(
        f"Estimated time: ~{est_s:.0f}s "
        f"(at {delay_min}-{delay_max}s/prospect, per scraper_request_delay)"
    )

    if dry_run:
        print("\nDry run — no fetches. Sample (first 5):")
        for p in candidates[:5]:
            print(
                f"  {p.id}  source={p.source or '?':10}  "
                f"website={p.website[:60]}"
            )
        if len(candidates) > 5:
            print(f"  ... and {len(candidates) - 5} more")
        return 0

    enricher = HomepageEnricher(
        page_timeout_s=settings.scout_enrichment_page_timeout_s,
        batch_timeout_s=settings.scout_enrichment_overall_timeout_s,
    )

    summary = {
        "attempted": 0,
        "ok": 0,
        "no_data": 0,
        "error": 0,
        "timeout": 0,
        "field_hits": {"phone": 0, "email": 0, "address": 0, "socials": 0},
    }
    print("\nStarting enrichment...")
    overall_start = time.monotonic()
    for i, p in enumerate(candidates, start=1):
        result = await enrich_one(enricher, p)
        summary["attempted"] += 1
        status = result.get("status", "error")
        summary[status] = summary.get(status, 0) + 1
        for f in result.get("updates", []):
            summary["field_hits"][f] = summary["field_hits"].get(f, 0) + 1
        if i % 10 == 0 or i == len(candidates):
            elapsed = time.monotonic() - overall_start
            rate = i / elapsed if elapsed else 0
            remaining = (len(candidates) - i) / rate if rate else 0
            print(
                f"  [{i}/{len(candidates)}] "
                f"ok={summary['ok']} no_data={summary['no_data']} "
                f"error={summary['error']} timeout={summary['timeout']} | "
                f"~{remaining:.0f}s left"
            )
        # Respect scraper_request_delay_min/max between fetches
        if i < len(candidates):
            await asyncio.sleep(random.uniform(delay_min, delay_max))

    total_ms = int((time.monotonic() - overall_start) * 1000)
    print("\n=== Backfill complete ===")
    print(f"Attempted: {summary['attempted']}")
    print(f"  ok:       {summary['ok']}")
    print(f"  no_data:  {summary['no_data']}")
    print(f"  error:    {summary['error']}")
    print(f"  timeout:  {summary['timeout']}")
    print(f"Field updates: {summary['field_hits']}")
    print(f"Total time: {total_ms / 1000:.1f}s")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill homepage enrichment for existing prospects (T8.6)"
    )
    parser.add_argument(
        "--source",
        choices=["all", "google", "maps"],
        default="all",
        help="Filter by prospect source (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max prospects to process (default: unlimited)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the list without making any HTTP requests",
    )
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
