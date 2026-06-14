# Scout Homepage Enrichment — Spec

> **Status**: Approved design (T8.6) · **Author**: T8.6 group · **Target release**: post-T8.5, T8.6 cycle
> **Spec trail**: This document captures the design agreed between Juragan and the implementation agent on 2026-06-14. It supersedes any earlier inline discussion in chat. Changes to this spec require a code review.

---

## 1. Problem

The Scout module's job is to discover Indonesian UMKM (Klinik Gigi, Klinik Kecantikan, F&B chain — per ICP lock D22) that may need software services, persist them as `prospect` rows, and feed them into the analyzer → scorer → outreach pipeline. Without contact information on each prospect, the pipeline cannot advance to outreach.

**Current state** (audited 2026-06-14):

| Source | URL | Phone | Email | Address | Socials |
|---|---|---|---|---|---|
| Google Search (SearXNG) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Google Maps (Playwright) | ✅ | ✅ (regex) | ❌ | ✅ (regex) | ❌ |

The Maps scraper (`backend/app/services/scraper/maps.py:201-215`) extracts phone and address heuristically from card text. The Google scraper (`google.py`) captures only the URL and search snippet. **Neither source captures email or social links.**

**Impact**: a prospect with only `company_name` + `website` cannot be contacted by the T6 Outreach module, which requires `prospect.email` (Email channel) or `prospect.phone` (WhatsApp channel) per R9 and D116.

## 2. Goal

For every prospect produced by any Scout source (Google Search, Google Maps, future Twitter/Threads), automatically augment the record with **phone, email, address, and social links** by fetching the prospect's homepage and extracting the values. **Zero manual work** — this is core to the "sales team in a box" value proposition (per `MEMORY.md ## Project context`).

## 3. Non-goals

- **No multi-page crawl**. The homepage alone is the source. `/contact` and `/about` are out of scope (v2).
- **No LLM-based extraction**. Heuristics only — deterministic, no API cost, no rate limit coupling.
- **No social-network enrichment**. We capture the link, not the follower count or content.
- **No Twitter/Threads enrichment in this PR**. Their source pages (tweet permalinks) don't follow the homepage pattern. Defer to v2.
- **No schema migration**. Reuse existing `Prospect` columns + `social_links` JSONB.
- **No proxy rotation**. The current `scraper_request_delay_min/max` config is sufficient for solo Juragan scale.

## 4. Solution Architecture

### 4.1 Pipeline (new step highlighted)

```
Scraper (Google/Maps)
       │
       ▼  ← search() returns list[ScrapedResult{company_name, website, ...}]
list[ScrapedResult]
       │
       ▼  ← NEW: HomepageEnricher.enrich_batch(results)
list[ScrapedResult{phone, email, location_address, social_links}]
       │
       ▼
persist_scraped_to_prospects() — best-effort, never blocks on enrichment failure
       │
       ▼
T5 auto-enrichment (existing) → T5 scoring → T6 outreach (R10 approval)
```

### 4.2 Module layout

**New file**: `backend/app/services/scraper/enricher.py`

```python
class HomepageEnricher:
    """Fetch a homepage + extract phone, email, address, social links.

    One instance per Celery task. Reuses a single Playwright
    browser across the batch to amortize launch overhead.
    All extractors are pure functions on the page HTML — unit-testable
    without a browser.
    """
    PAGE_TIMEOUT_MS = 12_000
    SETTLE_MS = 1_500
    BATCH_TIMEOUT_S = 240.0

    async def enrich_batch(
        self, results: list[ScrapedResult]
    ) -> list[ScrapedResult]: ...

    async def _enrich_one(
        self, page, r: ScrapedResult
    ) -> ScrapedResult: ...

    # --- Pure-function extractors (unit-testable) ---
    @staticmethod
    def extract_phones(html: str, visible_text: str) -> list[str]: ...
    @staticmethod
    def extract_emails(html: str) -> list[str]: ...
    @staticmethod
    def extract_address(html: str, visible_text: str) -> str | None: ...
    @staticmethod
    def extract_socials(html: str) -> dict[str, str]: ...
```

Enrichment is **not a `BaseScraper` subclass** because the contracts differ:
- `BaseScraper.search(query) -> list[ScrapedResult]` (creates new prospects)
- `HomepageEnricher.enrich_batch(results) -> results` (augments existing)

### 4.3 Extraction heuristics

| Field | Strategy | Priority |
|---|---|---|
| **phone** | (1) `tel:` hrefs, (2) `wa.me/<digits>` and `whatsapp.com/send?phone=` URLs, (3) regex `(\+?\d[\d\s\-\.\(\)]{7,}\d)` on visible text. Keep first 3 unique. Accept only if 8-16 digits, prefer `+62` or `0` prefix. | tel: > wa.me > +62 regex > generic regex |
| **email** | (1) `mailto:` hrefs, (2) RFC-5322 regex on body. **Filter out**: `noreply@`, `no-reply@`, `admin@`, `webmaster@`, `postmaster@`, `abuse@`, `privacy@`, `support@example.*`, `*@example.com`, `*@sentry.io`, `*@yourdomain.com`. | mailto: > body regex |
| **address** | (1) Schema.org `<[itemprop="address"]>`, (2) OpenGraph `business:contact_data:street_address`, (3) footer regex: `Jl\.\|Jalan\|Ruko\|Komp\.\|Blok\|Kel\.\|Kec\.` (Indonesian street markers). 8-200 chars. | microdata > OG > footer regex |
| **socials** | Scan all `<a href>` for: `instagram.com/[^/]+`, `facebook.com/[^/]+`, `twitter.com\|x.com/[^/]+`, `linkedin.com/(company\|in)/[^/]+`, `tiktok.com/@[^/]+`, `youtube.com/(c/\|@\|channel/)[^/]+`, `wa.me/`, `t.me/`, `whatsapp.com/`. First occurrence per platform wins. | First match per platform |

**Phone & email normalization** (deferred to v2): E.164 canonicalization, `+62 21 555-1234` ↔ `(021) 5551234` merging. For v1 we just take the first good match.

**Social link key normalization**:
- `instagram.com/...` → `instagram`
- `facebook.com/...` → `facebook`
- `twitter.com/X` and `x.com/X` both → `twitter`
- LinkedIn company → `linkedin`
- `tiktok.com/@X` → `tiktok`
- YouTube channel → `youtube`
- `wa.me/X` / `whatsapp.com/...` → `whatsapp`
- `t.me/X` → `telegram`

### 4.4 Status tracking

Every enriched result gets `extra.enrichment_status` (one of `ok`, `no_data`, `timeout`, `error`) + `extra.enrichment_ms` (int). The status is **non-blocking** — the prospect is persisted regardless, with whatever fields were extracted. This is critical: enrichment is best-effort, but the prospect is the deliverable.

## 5. Configuration

**Add to `backend/app/core/config.py`** (lines 121-126 block):

```python
# Scout enrichment (T8.6)
scout_enrichment_enabled: bool = True                # global kill switch
scout_enrichment_page_timeout_s: int = 12           # per-page fetch
scout_enrichment_overall_timeout_s: int = 240       # per-batch cap
scout_enrichment_max_concurrent: int = 1            # sequential per worker (Playwright)
```

**Add to `.env.example`**:
```
# Scout enrichment (T8.6)
SCOUT_ENRICHMENT_ENABLED=true
SCOUT_ENRICHMENT_PAGE_TIMEOUT_S=12
SCOUT_ENRICHMENT_OVERALL_TIMEOUT_S=240
SCOUT_ENRICHMENT_MAX_CONCURRENT=1
```

The Celery worker has `celery_task_time_limit: 600` (10 min). The default `OVERALL_TIMEOUT_S=240` (4 min) leaves a 6-min buffer. If a Scout job hits the limit, it gets killed and the partial enrichment is lost (acceptable: prospects still have name+URL from the search step).

## 6. Integration Points

### 6.1 `backend/app/tasks/scraping_tasks.py` — auto-trigger in Scout job

Insert between line 53 (`results = await scraper.search(query)`) and line 54 (`inserted = await persist_scraped_to_prospects(db, results)`):

```python
results = await scraper.search(query)

# T8.6: enrich with phone/email/address/socials from homepage
if settings.scout_enrichment_enabled and results:
    try:
        enricher = HomepageEnricher(
            page_timeout_s=settings.scout_enrichment_page_timeout_s,
            batch_timeout_s=settings.scout_enrichment_overall_timeout_s,
        )
        results = await enricher.enrich_batch(results)
    except Exception as e:
        logger.warning("Enrichment batch failed (continuing): %s", e)
        for r in results:
            r.extra.setdefault("enrichment_status", "error")

inserted = await persist_scraped_to_prospects(db, results)
```

**Critical**: the `try/except` is the safety net. Enrichment is best-effort; a 100% failure must not fail the job.

### 6.2 New endpoint — per-prospect re-enrich

**New file** `backend/app/api/v1/enrichment.py` (or add to `prospects.py` if the user prefers single file):

```
POST /api/v1/prospects/{prospect_id}/enrich
Auth: required
Response: {status: "ok"|"no_data"|"timeout"|"error", fields: {phone, email, address, socials}}
```

This is the user-facing "Refresh kontak" button on the Prospect detail page. Idempotent: re-running just re-fetches and overwrites. Existing fields are overwritten with newer data (if the page has changed since the first enrichment).

### 6.3 Backfill script

**New file** `backend/scripts/backfill_enrichment.py`:

```bash
docker compose exec backend python -m scripts.backfill_enrichment --source all
# or
docker compose exec backend python -m scripts.backfill_enrichment --source google
# or
docker compose exec backend python -m scripts.backfill_enrichment --dry-run
```

Behavior:
- Query: `SELECT * FROM prospects WHERE website IS NOT NULL AND (email IS NULL OR phone IS NULL OR location_address IS NULL OR social_links IS NULL OR social_links = '{}'::jsonb)`
- For each row, run `HomepageEnricher.enrich_batch([as_scraped_result])` (one at a time, no batching)
- Sleep 3-8s between fetches (reuse `scraper_request_delay_min/max`)
- Update row with extracted fields
- Log per-row status + final summary
- **Idempotent**: second run finds nothing to do (all fields populated)
- **Rate-limit friendly**: respects `scraper_request_delay_min/max`
- **CLI flags**: `--source google|maps|all` (default `all`), `--limit N` (default unlimited), `--dry-run` (preview only)

## 7. Failure Handling Matrix

| Failure | Detection | Behavior | Logging |
|---|---|---|---|
| Network error (DNS, conn reset, 5xx) | httpx / Playwright exception | `enrichment_status="error"`, continue | warning with URL |
| Page timeout (>12s) | Playwright `TimeoutError` | `enrichment_status="timeout"`, continue | info with URL |
| 4xx (403 Cloudflare, 404 dead site) | HTTP status | `enrichment_status="no_data"`, continue | debug with status code |
| 200 but empty body / pure JS | inner_text() returns `<noscript>` only | `enrichment_status="no_data"`, continue | debug |
| No fields extracted (all None) | post-extract check | `enrichment_status="ok"`, all fields None | info "no contact info" |
| Playwright crash mid-batch | exception in `_enrich_one` | mark that one `"error"`, continue batch | warning with URL |
| Whole batch crashes | exception at `enrich_batch` top level | catch at integration point, mark ALL in-flight `"error"`, persist original results | warning with summary |
| Celery soft limit (9 min) | Celery signal | job killed, partial results lost (prospects still have name+URL) | Celery log |

**Hard rule**: no failure mode blocks `persist_scraped_to_prospects()`. The prospect is the deliverable; enrichment is gravy.

## 8. Observability

**Per-job log** (info):
```
Enrichment: attempted=20 ok=14 no_data=4 error=2 timeout=0
Fields: phone=65% email=45% address=30% socials=70% avg_ms=2300
```

**Per-result log** (debug): URL, status, ms, fields extracted (truncated for readability).

**`scraping_job_completed.details` JSON** (no schema change, just extra fields):
```json
{
  "source": "google",
  "results": 20,
  "new_prospects": 18,
  "enrichment": {
    "attempted": 20,
    "ok": 14,
    "no_data": 4,
    "error": 2,
    "timeout": 0,
    "field_rates": {
      "phone": 0.65,
      "email": 0.45,
      "address": 0.30,
      "socials": 0.70
    },
    "avg_ms": 2300
  }
}
```

No new analytics endpoint — visible via existing `GET /api/v1/analytics/overview` once jobs finish. No dashboard widget for v1 (could be added in T7 polish if useful).

## 9. Data Model

**No migration.** Reuse existing `Prospect` fields:

| Field | Type | Source extractor | Maps replacement? |
|---|---|---|---|
| `phone` | `str \| None` | `extract_phones` | Yes — homepage is more authoritative than card text |
| `email` | `str \| None` | `extract_emails` | New field (Maps never had it) |
| `location_address` | stored in `raw_data.location_address` (T4 limitation; will migrate when field is added) | `extract_address` | Yes |
| `social_links` | `JSONB` | `extract_socials` | New field (Maps never had it) |
| `description` | (unchanged) | SearXNG snippet | No |
| `extra` | `JSONB` | `enrichment_status`, `enrichment_ms` | Plus existing fields |

For Maps-source prospects: `phone` and `location_address` may be re-populated by the homepage enricher (more authoritative). The Maps card-text values are preserved in `extra` if the enrichment overwrites them. **Re-enrich preserves the most recent value, not a "first wins" rule** — homepage is canonical.

## 10. Testing Strategy

| Layer | Test | File |
|---|---|---|
| Unit | `extract_phones` for `+62 21 555-1234`, `(021) 5551234`, `wa.me/6281234567890`, generic `0812-3456-7890`, and noise (`Rp 50.000`, dates) | `tests/services/scraper/test_enricher_phones.py` |
| Unit | `extract_emails` picks `mailto:` over body regex, filters `noreply@`, `admin@`, `example.com`, `yourdomain.com`, `sentry.io` | `tests/services/scraper/test_enricher_emails.py` |
| Unit | `extract_address` for "Jl. Sudirman No. 45, Jakarta Selatan", "Ruko Blok B-12", and rejects non-address lines | `tests/services/scraper/test_enricher_address.py` |
| Unit | `extract_socials` for each platform: Instagram, Facebook, X/Twitter, LinkedIn, TikTok, YouTube, WhatsApp, Telegram. First-occurrence wins. | `tests/services/scraper/test_enricher_socials.py` |
| Unit | `enrich_batch` error handling: one bad URL doesn't kill the batch | `tests/services/scraper/test_enricher_batch.py` |
| Integration | Spin up `aiohttp` test server with fixture HTML (WordPress-like, WiX-like, custom HTML, "no contact info" page); `enrich_one` against each, assert fields | `tests/integration/test_enricher_live.py` |
| E2E (manual) | Run real Scout on "klinik Jakarta" + "rumah makan Bandung"; spot-check 5 prospects in UI; verify Composer T6 has email/phone available | Manual checklist |
| Backfill | Run `python -m scripts.backfill_enrichment --dry-run` → count; then without `--dry-run` → field rates | Manual run |

**Coverage target**: >80% for the 4 extractors (pure functions); >50% for `enrich_batch` (async + Playwright, harder to test without fixtures).

## 11. Rollout

| Phase | Scope | Gate to next |
|---|---|---|
| **1** | Code complete + unit + integration tests pass. Flag `scout_enrichment_enabled=False` in dev so existing behavior is unchanged. | Internal review of this spec + PR diff |
| **2** | Enable in dev (`scout_enrichment_enabled=True`). Manual smoke: 5 real prospects, verify all 4 fields where applicable. | User sign-off after visual check |
| **3** | Enable in prod. Monitor 1 week via per-job logs. | Field rate ≥50% phone, ≥30% email in 7-day window |
| **4** | (Optional, no v1 commitment) Add re-enrichment UI polish + dashboard widget for field rate trends | TBD based on v1 signal |

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Indonesian sites are JS-heavy SPAs (Tokopedia, WordPress Elementor) | High | Medium | `domcontentloaded` + 1.5s settle is enough for contact info; no full network-idle wait |
| Cloudflare / anti-bot 403s | Medium | Low | Fall back: log + `enrichment_status="no_data"`; don't retry (avoids throttling) |
| Phone number false positives (CSS counters, prices) | Medium | Medium | Require `tel:` OR `+62/0` prefix OR `wa.me`; 8-16 digit range |
| Multi-language sites (English + Indonesian) | Low | Low | Regex is language-agnostic; address regex handles both |
| Playwright load slows Celery worker | Medium | Medium | Sequential per batch, `OVERALL_TIMEOUT_S=240` cap; if it becomes a bottleneck, separate "enrichment" Celery queue (T8.7+) |
| Backfill accidentally rate-limits upstream | Low | Medium | Reuse `scraper_request_delay_min/max` (3-8s); `--limit N` flag for testing |
| Email false positives (privacy emails on the page) | Low | Low | Filter list covers the common offenders; user can review/edit in UI |
| Social link key collision (`facebook.com` vs `fb.me`) | Low | Low | v1 only matches `facebook.com/...` (most common); `fb.me` deferred |

## 13. Out of Scope (v2+ candidates)

- **Multi-page crawl** (`/contact`, `/about`, `/kontak`) — would double phone/email rate but explode timeout budget
- **LLM-based extraction fallback** for sites with weird markup (the noisy last 10%)
- **Deduplication of phone variants** (`+62 21 555…` vs `(021) 555…`) into canonical E.164
- **WhatsApp link validation** (extract URL, ping WhatsApp to confirm it's a real business)
- **Social link enrichment** (follow Instagram → follower count, business category, etc.)
- **Twitter/Threads source enrichment** (their landing pages don't have phone/email reliably)
- **Per-ICP prioritization** (klinik fields might differ from F&B — config-driven extractor tuning)
- **Cache layer** (Redis) for homepage content to avoid re-fetching on re-enrich

## 14. Effort Estimate & Commit Breakdown

**Total: ~950 LOC, ~3.5 hours wall time, 5 commits on `feature/scout-enrichment` → 1 PR to develop**

| Commit | Description | LOC | Time |
|---|---|---|---|
| 1 | `docs: add Scout homepage enrichment spec` | ~250 (this file) | 15-20 min |
| 2 | `feat(scraper): HomepageEnricher + unit tests` | ~500 (enricher + 4 test files) | 1-1.5 h |
| 3 | `feat(tasks): integrate enrichment into Scout job + new POST /prospects/{id}/enrich endpoint + integration test` | ~100 (tasks edit + endpoint + test) | 30 min |
| 4 | `feat(scripts): backfill_enrichment.py one-shot script` | ~120 | 30 min |
| 5 | `feat(ui): Refresh kontak button on ProspectDetail` | ~20 | 15 min |

After merge:
- E2E verification: real Scout run, UI spot-check (15 min)
- Backfill: run `python -m scripts.backfill_enrichment --source all` (~1-2 min for 10 existing prospects)

## 15. References

- `MEMORY.md` — `R8` (scraping scope v1), `R9` (outreach scope v1: Email + WhatsApp only), `D22` (ICP lock), `D116` (T6 channels = Email + WhatsApp)
- `backend/app/services/scraper/base.py:18-31` — `ScrapedResult` schema (fields already declared, just unpopulated for Google)
- `backend/app/services/scraper/maps.py:62-151` — Playwright pattern reference (same launch flags, same timeout wrapper)
- `backend/app/services/scraper/google.py:36-84` — current SearXNG integration (where enrichment is inserted)
- `backend/app/tasks/scraping_tasks.py:53-54` — exact insertion point for the enrichment call
- `backend/app/core/config.py:121-126` — existing scraper config block (enrichment settings added alongside)
- `.env.example` — env var template (add 4 new keys)
- `backend/scripts/create_admin.py` — pattern for one-shot script in `backend/scripts/`
