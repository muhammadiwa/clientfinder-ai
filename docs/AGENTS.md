# ClientFinder AI Agent — Complete Agent Specifications

> Spec lengkap untuk 8 agent yang menyusun ClientFinder AI Agent.
> Agent 1–6 sudah ada di brief awal (lihat [ARCHITECTURE.md](ARCHITECTURE.md)).
> **Dokumen ini fokus ke Agent 7–10** yang belum di-spec.

---

## Daftar Agent

| # | Agent | Status | Phase |
|---|---|---|---|
| 1 | Data Collection Agent | ✅ Spec | T4 |
| 2 | Lead Discovery Agent | ✅ Spec | T4 |
| 3 | Website Audit Agent | ✅ Spec | T4–T5 |
| 4 | Social Signal Agent | ✅ Spec | T4–T5 |
| 5 | Lead Qualification Agent | ✅ Spec | T5 |
| 6 | Lead Scoring Agent | ✅ Spec | T5 |
| **7** | **Outreach Personalization Agent** | ✅ **Spec** | **T6** |
| **8** | **CRM Agent** | ✅ **Spec** | **T2, T7** |
| **9** | **Follow-Up Agent** | ✅ **Spec** | **T6** |
| **10** | **Reporting Agent** | ✅ **Spec** | **T7** |

---

# Agent 7: Outreach Personalization Agent

## Tujuan
Mengubah data prospek + audit findings + lead score menjadi pesan outreach yang personal dan siap kirim, dengan tone yang tepat per channel.

## Arsitektur Internal

```
ProspectContext
  ├── company info (nama, industri, lokasi, size)
  ├── tech audit findings (issues, opportunities)
  ├── pain points (extracted)
  ├── lead score breakdown
  ├── recommended hook(s)
  └── previous interactions (kalau ada)

        │
        ▼

Template Engine
  ├── Email templates (formal, semi-formal)
  ├── WhatsApp templates (semi-formal, conversational)
  └── Threads templates (casual, short)

        │
        ▼

LLM Personalization Layer
  ├── Primary: Groq (Llama 3.1 70B)
  ├── Fallback: Gemini 1.5 Flash
  └── Prompt: Indonesia-first, anti-spam, value-first

        │
        ▼

Quality Gate
  ├── Length check (WA < 300 chars, Email < 150 words)
  ├── Spam trigger detection (no "FREE!", no all caps)
  ├── Personalization score (must reference prospect-specific data)
  └── Human approval flag (always on for MVP)

        │
        ▼

Message Output
  ├── subject (email only)
  ├── body
  ├── personalization_score (0-1)
  ├── reasoning (why this angle)
  └── approval_required: true
```

## Input

```python
class PersonalizationRequest(BaseModel):
    prospect_id: UUID
    channel: Literal["email", "whatsapp", "threads"]
    template_id: UUID | None  # kalau None, auto-pick best template
    hook_ids: list[UUID]       # dari hook library
    context_override: dict | None  # manual override
    locale: str = "id-ID"      # default Indonesian
```

## Output

```python
class PersonalizedMessage(BaseModel):
    prospect_id: UUID
    channel: str
    subject: str | None        # email only
    body: str
    personalization_score: float  # 0-1
    reasoning: str             # kenapa approach ini
    tokens_used: int
    model: str
    generation_time_ms: int
    requires_human_approval: bool = True
    metadata: dict  # {variables_used, hook_referenced, etc}
```

## Prompt Strategy

### Email Prompt (Bahasa Indonesia, formal)
```
Kamu adalah Business Development Specialist yang handal. Tulis email
outreach dalam Bahasa Indonesia yang sopan, profesional, dan value-first.

PROSPEK:
- Bisnis: {company_name}
- Industri: {industry}
- Lokasi: {location}
- Size: {employee_count}
- Website: {website_url}

AUDIT FINDINGS:
- Issue utama: {top_issue}
- Opportunity: {top_opportunity}

LEAD SCORE: {score}/100 ({grade})

PESAN STRUKTUR:
1. Subjek: personal, refer ke industri mereka (max 60 char)
2. Opening: reference spesifik ke bisnis mereka (bukan generic)
3. Pain: sebutkan 1-2 issue konkret dari audit
4. Value: tawarkan 1 insight / mini-audit / case study
5. CTA: low-friction (balas email / 15 menit call / download PDF)
6. Signature: nama, role, kontak

CONSTRAINTS:
- Max 150 kata
- Hindari: "FREE", "DISCOUNT", "URGENT", all caps, emoji berlebihan
- Tone: kayak ngobrol sama kolega, bukan sales pitch
- Bahasa: natural Indonesia, tidak terlalu formal/kaku

OUTPUT: JSON dengan {subject, body, reasoning}
```

### WhatsApp Prompt (semi-formal, pendek)
```
Kamu outreach via WhatsApp ke owner bisnis. Tulis pesan yang natural,
tidak terasa template, max 300 karakter (3-4 kalimat).

PROSPEK: {company_name}, {industry}, {location}
AUDIT: {top_finding}
HOOK: {personalization_hook}

STRUKTUR:
- Sapa (hormat tapi casual, "Halo Pak/Bu {name}" atau "Halo tim {company}")
- Konteks 1 kalimat (kenapa hubungi)
- Value 1 kalimat (insight gratis / case study)
- CTA 1 kalimat (buka chat / lihat link)

JANGAN:
- Pakai "Selamat pagi/sore" (terlalu formal)
- Pakai emoji lebih dari 1
- Hard-sell
- Mention "AI" atau "agent" (jaga-jaga)
```

### Threads Prompt (casual, ultra-pendek)
```
Kamu reply ke Threads post atau DM. Tone: casual, kayak anak muda
ngobrol. Max 200 karakter.

PROSPEK: {company_name} baru post soal: {post_excerpt}

STRUKTUR:
- Acknowledge post mereka (1 kalimat)
- Pivot ke insight / value (1 kalimat)
- CTA soft (1 kalimat, optional)
```

## LLM Model Selection

| Tier | Model | Use Case | Cost |
|---|---|---|---|
| Primary | Groq Llama 3.1 70B | Email (kompleks) | Free tier |
| Primary | Groq Llama 3.1 8B | WhatsApp/Threads (pendek) | Free tier |
| Fallback | Gemini 1.5 Flash | Backup semua | Free tier |

**Daily limits (Groq free):** ~14,400 req/day. Cukup untuk 200 leads/hari dengan 3 channels.

## Quality Metrics

Setiap output diukur:

- **Personalization Score (0-1):** berapa banyak referensi spesifik ke prospek (bukan template)
- **Length Compliance:** sesuai limit per channel
- **Spam Probability:** detection dari kata-kata spam
- **Token Cost:** untuk monitoring

Threshold minimum sebelum bisa auto-approve (kalau user set):
- Personalization score > 0.7
- Spam probability < 0.1
- Length compliance OK

**Default MVP: SELALU butuh human approval.** Auto-approve di v2 setelah track record terbukti.

---

# Agent 8: CRM Agent

## Tujuan
Menyimpan, mengorganisir, dan melacak semua interaksi dengan prospek/lead/client dalam satu tempat terpusat, dengan pipeline management dan audit trail.

## Data Model (existing di DB schema)

Core tables (sudah di blueprint):
- `prospects` — master data
- `messages` — semua outreach (in/out)
- `sequences` — multi-step campaign
- `sequence_enrollments` — prospek di sequence
- `activities` — audit log
- `users` — multi-user ready
- `settings` — key-value config

## Pipeline Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  DISCOVERED │───►│  ENRICHED   │───►│   SCORED    │
│  (raw lead) │    │ (with data) │    │ (A/B/C/D)   │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   WON 🎉    │◄───│  REPLIED    │◄───│  CONTACTED  │
│  (client)   │    │  (engaged)  │    │ (outreach)  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       │                  ▼                  ▼
       │           ┌─────────────┐    ┌─────────────┐
       │           │   LOST      │    │ NO_REPLY    │
       │           │ (rejected)  │    │ (sequence   │
       │           │             │    │  ended)     │
       │           └─────────────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│  PROJECT    │  ◄── New stage (post-MVP)
│  ACTIVE     │
└─────────────┘
```

## Fitur CRM

### A. Prospect Management
- Create, read, update, soft-delete
- Bulk import (CSV)
- Bulk export
- Tags (custom labels)
- Owner assignment (kalau multi-user)
- Notes (timestamped, by user)
- Custom fields (key-value)

### B. Search & Filter
- Full-text search (PostgreSQL `tsvector` Bahasa Indonesia)
- Filter: status, grade, source, industry, location, score range, date range, tags
- Saved filters (presets)
- Segment builder (visual filter UI)

### C. Interaction Tracking
- Auto-log semua: view, edit, status change, message sent, reply received
- Manual note tambah
- Attachment (MinIO) — proposal PDF, contract scan, dll
- Timeline view per prospek

### D. Pipeline Management
- Kanban view (drag & drop status change)
- Bulk status change
- Stage-specific actions (e.g., "Mark as Won" → trigger project intake)
- Win/loss reason tracking

### E. Multi-User & Permissions
- Roles: owner, admin, member
- Per-prospect owner
- Activity feed (siapa ngapain)
- Mention/assign (kalau tim)

### F. Data Retention & Backup
- Auto-backup ke MinIO (encrypted)
- Soft-delete dengan retention 90 hari
- GDPR/UU PDP compliance: right to be forgotten
- Data export per prospek (JSON)

## API Endpoints (high-level)

```
GET    /api/v1/prospects                       # list + filter + paginate
POST   /api/v1/prospects                       # create
GET    /api/v1/prospects/{id}                  # detail
PATCH  /api/v1/prospects/{id}                  # update
DELETE /api/v1/prospects/{id}                  # soft delete
POST   /api/v1/prospects/{id}/restore          # restore from soft delete
POST   /api/v1/prospects/bulk/import           # CSV import
POST   /api/v1/prospects/bulk/export           # CSV/JSON export
POST   /api/v1/prospects/{id}/tags             # add/remove tags
POST   /api/v1/prospects/{id}/notes            # add note
GET    /api/v1/prospects/{id}/activities       # activity log
POST   /api/v1/prospects/{id}/assign           # assign owner
POST   /api/v1/prospects/{id}/status           # change pipeline status

GET    /api/v1/pipeline/kanban                 # kanban view data
GET    /api/v1/tags                            # list of all tags
GET    /api/v1/filters                         # saved filters
POST   /api/v1/filters                         # save filter

POST   /api/v1/prospects/{id}/gdpr-erase       # right to be forgotten
GET    /api/v1/prospects/{id}/data-export      # download all data
```

## UI Pages

- `/prospects` — list dengan filter & bulk action
- `/prospects/:id` — detail dengan tabs (Overview, Messages, Activities, Notes, Files)
- `/pipeline` — Kanban view
- `/tags` — tag management
- `/filters` — saved filter management

---

# Agent 9: Follow-Up Agent

## Tujuan
Mengelola multi-step sequence campaign: kirim pesan berikutnya di waktu yang tepat, stop kalau sudah reply, dan re-engage kalau ada trigger baru.

## Arsitektur

```
Sequence Definition
  ├── Steps: ordered list
  │    └── {day_offset, channel, template_id, conditions}
  ├── Targeting: {grade, source, tags, custom_filter}
  ├── Schedule: business hours, timezone
  └── Status: draft, active, paused, archived

        │
        ▼

Per-Prospect Enrollment
  ├── prospect_id
  ├── sequence_id
  ├── current_step: 0, 1, 2, ...
  ├── next_action_at: timestamp
  ├── status: active, paused, completed, stopped
  └── variables: runtime state

        │
        ▼

Scheduler (Celery Beat)
  ├── Every 5 min: scan enrollments due
  ├── Check conditions (replied? blocked? valid?)
  ├── Generate message via Agent 7
  ├── Queue for human approval
  └── Log activity

        │
        ▼

State Machine
  ┌─────────┐
  │  DRAFT  │
  └────┬────┘
       │ activate
       ▼
  ┌─────────┐  ┌──────────────┐  ┌─────────────┐
  │ ACTIVE  │─►│ step_n + 1   │─►│ step_n + 2  │ ...
  │ (loop)  │  │ send & wait  │  │             │
  └────┬────┘  └──────┬───────┘  └─────────────┘
       │              │
       │              ▼ (replied)
       │         ┌─────────┐
       │         │ STOPPED │
       │         └─────────┘
       │
       └──► (sequence end) → COMPLETED
```

## Sequence Definition Schema

```python
class SequenceStep(BaseModel):
    order: int                          # 0, 1, 2, ...
    channel: Literal["email", "whatsapp", "threads"]
    template_id: UUID | None            # kalau None, AI generate
    day_offset: int                     # days from enrollment start
    send_time: str | None               # "09:00" or None (= business hour)
    conditions: SequenceConditions

class SequenceConditions(BaseModel):
    skip_if_replied: bool = True
    skip_if_status_in: list[str] = []   # ["won", "lost", "unsubscribed"]
    skip_if_score_below: int | None
    skip_if_no_contact: bool = False
    only_if_tag: list[str] = []

class Sequence(BaseModel):
    id: UUID
    name: str
    description: str
    target_grade: list[str] | None      # ["A", "B"] or None
    target_source: list[str] | None     # ["google_maps", "twitter"] or None
    target_industry: list[str] | None
    steps: list[SequenceStep]
    is_active: bool
    daily_send_cap: int = 50            # max sends per day across all enrollments
    created_at: datetime
    updated_at: datetime
```

## Default Sequence (Template)

```
"Nurture Sequence v1" — 6 steps, 14 hari total
Target: Grade A & B, source apapun

Step 0 (Day 0, Email)
  - Template: first_touch_email
  - Subject: "Quick question about {company_name}'s website"
  - Body: audit finding + value offer + soft CTA

Step 1 (Day 2, WhatsApp)
  - Template: first_touch_wa
  - Short version, mention email sebelumnya
  - CTA: balas chat ini

Step 2 (Day 5, Email)
  - Template: value_email
  - Subject: "Re: {original_subject}"
  - Body: case study dari industri sama

Step 3 (Day 8, WhatsApp)
  - Template: bump_wa
  - Very short, "btw sudah liat email gw?"
  - Optional: kirim mini-audit PDF via WA

Step 4 (Day 14, Email)
  - Template: breakup_email
  - Subject: "Closing the loop"
  - Body: soft goodbye, "kalau nanti butuh, here's my WA"

Step 5 (Day 30, Email, conditional)
  - Template: re_engage_email
  - Subject: "Picked this up again — {company_name}"
  - Body: reference trigger baru (e.g., "I see you just opened a new branch")
  - Condition: only if prospect_score > 50 still
```

## State Transitions

| From | To | Trigger |
|---|---|---|
| DRAFT | ACTIVE | user activates |
| ACTIVE | PAUSED | user pause, or system detect anomaly |
| PAUSED | ACTIVE | user resume |
| ACTIVE | COMPLETED | all steps done |
| ACTIVE | STOPPED | replied, won, lost, unsubscribed, manual stop |
| STOPPED | (terminal) | no auto-resume |
| COMPLETED | (terminal) | ready for new sequence enrollment |

## Re-engagement Trigger

System bisa auto-enroll prospek ke sequence lagi kalau:
- Ada signal baru (e.g., new funding event, hiring spike)
- Time-based re-engagement (90/180/365 hari setelah last contact)
- User manually re-enrolls

Configurable di settings: `FOLLOWUP_REENGAGE_DAYS`, `FOLLOWUP_AUTO_REENGAGE`.

## API Endpoints

```
GET    /api/v1/sequences
POST   /api/v1/sequences
GET    /api/v1/sequences/{id}
PATCH  /api/v1/sequences/{id}
DELETE /api/v1/sequences/{id}
POST   /api/v1/sequences/{id}/activate
POST   /api/v1/sequences/{id}/pause
POST   /api/v1/sequences/{id}/clone          # duplicate for A/B test

POST   /api/v1/sequences/{id}/enroll        # enroll prospect(s)
GET    /api/v1/enrollments                   # list active enrollments
GET    /api/v1/enrollments/{id}
POST   /api/v1/enrollments/{id}/pause
POST   /api/v1/enrollments/{id}/resume
POST   /api/v1/enrollments/{id}/stop
POST   /api/v1/enrollments/{id}/restart     # back to step 0

POST   /api/v1/prospects/{id}/detect-reply  # manual trigger reply check
```

## UI Pages

- `/sequences` — list & builder UI
- `/sequences/:id` — sequence detail with step editor
- `/sequences/:id/enrollments` — per-sequence enrollments
- `/enrollments` — global enrollments list

---

# Agent 10: Reporting Agent

## Tujuan
Menghasilkan insight dari data operasional: lead generation performance, outreach effectiveness, conversion funnel, dan anomaly detection.

## KPI Categories

### A. Lead Generation KPIs
- Total leads discovered (period, by source, by industry)
- Lead grade distribution (A/B/C/D %)
- Avg lead score (overall, by source)
- Time-to-enrich (discover → enriched)
- Time-to-score (enriched → scored)
- Source quality (avg score per source)
- Duplicate rate

### B. Outreach KPIs
- Total messages sent (by channel, by template)
- Send volume vs daily cap
- Approval rate (% of AI drafts approved without edit)
- Time-to-approval (draft → approved)
- Send success rate (delivered / sent)
- Bounce rate
- Open rate (email)
- Reply rate (by channel, by template)
- Reply time (avg hours to first reply)
- Unsubscribe rate

### C. Pipeline KPIs
- Pipeline value (count × avg deal size, by stage)
- Conversion rate (stage to stage)
- Velocity (avg days per stage)
- Win rate
- Avg deal size
- Avg sales cycle (first touch → won)
- Loss reasons distribution

### D. Operational KPIs
- Celery task success rate (by task type)
- LLM cost (tokens × $)
- API rate limit hits
- Scraping success rate (per source)
- Data quality score (completeness %)

## Reports

### Daily Report (auto, jam 8 pagi)
- Yesterday's lead discovery
- Outreach sent & replies
- Hot leads baru
- Anomaly alerts (kalau ada)
- Top performing source today

### Weekly Report (auto, Senin jam 8)
- Week-over-week comparison
- Best performing template (per channel)
- Source quality trend
- Pipeline movement
- Goal tracking (kalau ada target)

### Monthly Report (auto, tanggal 1)
- Full month summary
- Cohort analysis
- Source ROI
- Channel ROI
- Forecast next month

### On-Demand Reports
- Custom date range
- Custom filter
- Export to CSV / PDF / JSON

## Anomaly Detection

System monitor & alert kalau ada:
- Sudden drop in lead discovery (50%+ vs avg)
- Sudden drop in reply rate
- High bounce rate (>10%)
- Many scraping failures (source blocked)
- LLM cost spike
- Many tasks failed in Celery
- High unsubscribe rate (potential ToS issue)

Alert channels:
- In-app notification
- Email (kalau setup)
- Optional: webhook (Slack, Discord, Telegram)

## Dashboard UI

Top-level cards:
- Today's Hot Leads
- This Week's Reply Rate
- Pipeline Value
- Top Source This Month

Charts:
- Lead discovery trend (line, daily)
- Grade distribution (pie)
- Channel performance (bar)
- Funnel (waterfall)
- Source comparison (horizontal bar)
- Reply time distribution (histogram)

Filters: date range, source, channel, grade, industry

## Export

- CSV (raw data)
- PDF (formatted report with charts)
- JSON (programmatic)
- Google Sheets integration (optional, v2)

## API Endpoints

```
GET /api/v1/analytics/dashboard              # overview cards + key charts
GET /api/v1/analytics/funnel                 # conversion funnel
GET /api/v1/analytics/source-performance     # per source breakdown
GET /api/v1/analytics/channel-performance    # per channel
GET /api/v1/analytics/template-performance   # A/B test results
GET /api/v1/analytics/cohort                 # cohort analysis
GET /api/v1/analytics/leaderboard            # top prospects (score, value)
GET /api/v1/analytics/timeseries             # time series data (configurable)
GET /api/v1/analytics/anomalies              # detected anomalies

GET /api/v1/reports/daily                    # daily report
GET /api/v1/reports/weekly                   # weekly report
GET /api/v1/reports/monthly                  # monthly report
GET /api/v1/reports/custom                   # custom date range

GET /api/v1/reports/{id}/export              # export specific report
POST /api/v1/reports/schedule                # schedule custom report
```

## Reporting Engine Implementation

```
PostgreSQL Materialized Views
  ├── mv_daily_leads          (refresh daily)
  ├── mv_daily_outreach       (refresh hourly)
  ├── mv_source_grade_stats   (refresh daily)
  └── mv_conversion_funnel    (refresh daily)

Celery Beat Tasks
  ├── recompute_daily_stats   (00:05 daily)
  ├── recompute_weekly_stats  (Mon 00:10)
  ├── recompute_monthly_stats (1st 00:15)
  └── detect_anomalies        (every 6 hours)

Caching
  ├── Redis cache for dashboard data (TTL 5 min)
  └── Cache invalidation on message status change
```

## Anomaly Detection Algorithm

```python
# Simple z-score based detection
def detect_anomaly(metric_name, current_value, history_30_days):
    if len(history_30_days) < 7:
        return None  # not enough data
    
    mean = np.mean(history_30_days)
    std = np.std(history_30_days)
    if std == 0:
        return None
    
    z_score = (current_value - mean) / std
    if abs(z_score) > 2.5:  # > 2.5 std deviations
        return {
            "metric": metric_name,
            "current": current_value,
            "expected_range": (mean - 2*std, mean + 2*std),
            "z_score": z_score,
            "severity": "high" if abs(z_score) > 3.5 else "medium"
        }
    return None
```

## UI Pages

- `/analytics` — main dashboard
- `/analytics/funnel` — funnel detail
- `/analytics/sources` — source comparison
- `/analytics/templates` — template A/B test
- `/reports` — list scheduled + historical reports
- `/reports/:id` — view specific report

---

# Integrasi Antar Agent

```
Discovery (T4)        Qualification (T5)       Outreach (T6)         CRM (T2/T7)
   │                        │                       │                    │
   │  new prospect          │                       │                    │
   ├───────────────────────►│                       │                    │
   │                        │ score + grade         │                    │
   │                        ├──────────────────────►│                    │
   │                        │                       │ generate message   │
   │                        │                       │ (Agent 7)          │
   │                        │                       │                    │
   │                        │                       │ save to CRM        │
   │                        │                       ├───────────────────►│
   │                        │                       │                    │
   │                        │                       │ ◄──── enroll ──────┤
   │                        │                       │      sequence      │
   │                        │                       │      (Agent 9)     │
   │                        │                       │                    │
   │                        │                       │ reply detection    │
   │                        │                       ├───────────────────►│
   │                        │                       │                    │
   │                        │                       │                    │ log to activities
   │                        │                       │                    │
   │                        │                       │       Reporting (T7)
   │                        │                       │            │
   │                        │                       │  daily rollup ──►│
   │                        │                       │            │
   │                        │                       │            ▼
   │                        │                       │       dashboard
```

---

# Tech Stack untuk 4 Agent Ini

| Agent | Tech |
|---|---|
| Outreach Personalization | Groq/Gemini + Jinja2 template + Pydantic validation |
| CRM | SQLAlchemy + PostgreSQL + Redis cache + MinIO (files) |
| Follow-Up | Celery + Redis scheduler + state machine (custom) |
| Reporting | PostgreSQL materialized views + Pandas (untuk kalkulasi) + Celery beat (scheduled) |

---

# Effort Estimation

| Agent | LOC (est) | Durasi |
|---|---|---|
| Outreach Personalization | ~800 | 3-4 hari |
| CRM | ~1,500 | 5-7 hari |
| Follow-Up | ~1,200 | 4-5 hari |
| Reporting | ~1,000 | 3-4 hari |
| **Total** | **~4,500** | **2-3 minggu** |

Split per phase:
- T2: CRM Agent (foundation) — 5-7 hari
- T6: Outreach + Follow-Up — 1-1.5 minggu
- T7: Reporting Agent — 3-4 hari

---

# Scout → Prospect Flow (Sprint 4 — v1 contract)

> Updated 2026-06-14. The flow was redesigned in 4 PRs (#115, #116, #117, #118) after the user meta-correction in turn 57 ("flow nya salah, kita kembali ke fitur scout dan prospect dulu, kita brainstorming dlu"). The redesign implements the hybrid (C) 2-layer display pattern from the 4-perspective analysis in turn 60.

## 3-source v1 registry

The Scout pipeline uses **3 active sources** (`backend/app/services/scraper/__init__.py:33-49`):

| Source | Type | Soft-fail? | Notes |
|---|---|---|---|
| `maps` | Google Maps (Playwright) | No | The only structured business data source |
| `twitter` | Twikit + cookies | Yes | Zero results without cookies |
| `threads` | Playwright + cookies | Yes | Zero results without cookies |

**Deactivated sources (4)**: `google` (SearXNG, was 67% noise per the 2026-06-14 audit), `google_places`, `yelp`, `tokopedia`. **Code kept** with `DEPRECATED 2026-06-14` banner. Re-enable is one config flip (registry + Literal + SOURCES + kill switch). This is the "deactivate-not-delete" pattern.

## Auto-enrich is OFF by default

The orchestrator's `enrich_prospect()` no longer auto-fires `social_scan_and_persist` (T9.0 social scan) or `classify_and_persist` (Sprint 3B tier/industry classifier). The auto-fire is gated by `scout_auto_enrich_enabled: bool = False` in `backend/app/core/config.py`. The per-prospect "Enrich" button in the UI is the only way to trigger enrichment by default. This matches the user spec: "hapus dulu proses enrich otomatis kita ulang dari awal lagi".

## max_results cap is lifted

`GoogleMapsScraper.MAX_HARD_CAP = 1000` (was 50). `DEFAULT_LIMIT = 200`. The cap is a Celery runaway guard, not a feature limit. Operator can pass `max_results` in the scout job query to set a lower bound.

## ScoutResult model: Q1=C (reuse prospects 1:1)

**No new ScoutResult table for v1.** A scout result is a virtual view: all prospects with `scout_run_id = :id` plus the full `raw_data` JSONB. For v2, can promote ScoutResult to a real table if operator-pick UX is needed.

The FK is `prospects.scout_run_id → scraping_jobs.id` (ON DELETE SET NULL). Migration: `backend/alembic/versions/9b8f3c4e2a1d_add_scout_run_fk_and_raw_data_index.py`. Index: `ix_prospects_scout_run_id` (btree) + `ix_prospects_raw_data_gin` (GIN, for future `raw_data @> '{"rating": "4.5"}'` queries).

## Maps full raw_data dump

`GoogleMapsScraper._parse_card` now extracts: `rating`, `review_count` (handles `rb`/`ribu`/`k` suffix and ID-locale `.` thousand separator), `hours` ("Buka 24 jam" / "Buka ⋅ Tutup pukul 21.00" / "Tutup permanen"), `price_range` ("$$" / "Rp 50.000–100.000"), `service_options` (Makan di tempat / Bawa pulang / Pesan antar, deduped). All fields go into `extra` → `prospects.raw_data` JSONB. The `HomepageEnricher` merges its keys (`enrichment_ms`, `enrichment_status`, `social`) into the same `extra` dict, so final `raw_data` has BOTH Maps data AND enrichment data.

## 2-layer hybrid C display (Q2/Q3/Q4)

| Layer | Surface | URL | Size |
|---|---|---|---|
| Layer 1 | ProspectDetail breadcrumb | inline | 1 line |
| Layer 2 | ScoutRunResults page | `/scout-runs/:id/results` | paginated, 25/page |

The ProspectDetail page shows a 1-line `ScoutRunBreadcrumb` ("📍 Ditemukan dari ScoutRun #X [Lihat →]"). Click → the dedicated ScoutRunResults page with the full raw data, paginated, sortable. Row click on the table → `/prospects/:id`. The "Link, don't load" pattern (Linear/Notion/Salesforce).

## API surface (v1)

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/scraping/jobs` | List all ScoutRuns (paginated, newest first) |
| `POST /api/v1/scraping/jobs` | Create a new ScoutRun |
| `GET /api/v1/scraping/jobs/{id}` | Get single ScoutRun status (for polling) |
| `POST /api/v1/scraping/jobs/{id}/retry` | Reset + re-enqueue a failed ScoutRun |
| `DELETE /api/v1/scraping/jobs/{id}` | Delete a ScoutRun (sets prospect.scout_run_id to NULL via ON DELETE SET NULL) |
| `GET /api/v1/scraping/scout-runs/{run_id}/results` | **PR 3 (Sprint 4)** — paginated prospects for a ScoutRun. IDOR-safe (filters by `created_by == current_user.id`). Filters soft-deleted prospects. Stable secondary sort by `Prospect.id`. |
| `GET /api/v1/scraping/presets` | Quick-start presets |

## Testing pattern (v1)

The codebase uses **source-inspection tests** (no async client fixtures) for endpoint contract tests. Example: `backend/app/tests/api/test_scout_run_results.py` verifies the endpoint is registered, has the right signature, returns 400/404 for invalid input, and uses `ProspectOut.model_dump(mode="json")`. The `model_validate` approach is used for schema tests. **No e2e Playwright tests for the scout→prospect flow yet** (the `frontend/tests/a11y/` dir exists for axe-core a11y tests, but the breadcrumb click flow is not covered). Add coverage in a future polish PR.

## Known deferred items (post-Sprint 4)

- **CONCURRENTLY for GIN index**: at v1 scale (hundreds of prospects) the `ACCESS EXCLUSIVE` lock during CREATE INDEX is negligible. At >100k rows, the migration should be split into a non-transactional `CREATE INDEX CONCURRENTLY` variant.
- **Persisted `inserted` over-count after IntegrityError fallback**: pre-existing in `persist_scraped_to_prospects` (`backend/app/services/scraper/__init__.py:114-135`). Not caused by this redesign.
- **Concurrent `_run_job` for the same `job_id`**: pre-existing. No `SELECT ... FOR UPDATE` claim on the job row.
- **Fallback re-attempt skips pre-check**: pre-existing. The unique index catches the race, but the pre-check should re-run inside the fallback.
