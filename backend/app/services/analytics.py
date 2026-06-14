"""
Analytics service — computes KPIs for T7.

Drives the analytics dashboard with all 4 KPI categories
(Lead Gen, Outreach, Pipeline, Operational).

Most aggregations are done in SQL for performance.
LLM cost is estimated from activity log details.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import String, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.activity import Activity
from app.models.outreach import Message
from app.models.prospect import Prospect
from app.models.system import ScrapingJob
from app.schemas.analytics import (
    ActivityCount,
    AnalyticsOverview,
    AnalyticsRange,
    ApprovalFunnelStats,
    ConversionRate,
    DailyPipeline,
    GradeDistribution,
    LeadSourceQuality,
    LLMUsageStats,
    OutreachChannelStats,
    PipelineStageCount,
    TimeToEnrichStats,
)

logger = logging.getLogger("clientfinder.analytics")


async def get_analytics_overview(days: int = 30) -> AnalyticsOverview:
    """
    Compute the full analytics overview for the given lookback period.

    All 4 KPI categories (Lead Gen, Outreach, Pipeline, Operational)
    in one response. Single round-trip from the dashboard.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    rng = AnalyticsRange(days=days, start=start, end=end)

    async with AsyncSessionLocal() as db:
        # === A. Lead Gen ===
        total_leads_q = select(func.count(Prospect.id)).where(
            Prospect.discovered_at >= start,
            Prospect.deleted_at.is_(None),
        )
        total_leads = (await db.execute(total_leads_q)).scalar() or 0

        # Grade distribution
        grade_q = select(
            Prospect.quality_grade,
            func.count(Prospect.id),
        ).where(
            Prospect.discovered_at >= start,
            Prospect.deleted_at.is_(None),
        ).group_by(Prospect.quality_grade)
        grade_rows = (await db.execute(grade_q)).all()
        grade_dist = GradeDistribution(unscored=total_leads)
        for grade, count in grade_rows:
            if grade in ("A", "B", "C", "D"):
                setattr(grade_dist, grade, count)
            else:
                grade_dist.unscored += count
        # If we missed any (e.g. some unscored slipped in), subtract
        accounted = grade_dist.A + grade_dist.B + grade_dist.C + grade_dist.D
        if grade_dist.unscored > total_leads - accounted:
            grade_dist.unscored = total_leads - accounted

        # Avg lead score
        avg_score_q = select(func.avg(Prospect.score_total)).where(
            Prospect.discovered_at >= start,
            Prospect.deleted_at.is_(None),
            Prospect.score_total.is_not(None),
        )
        avg_lead_score = (await db.execute(avg_score_q)).scalar()

        # Leads by source (with avg score + A-grade %)
        leads_by_source_q = (
            select(
                Prospect.source,
                func.count(Prospect.id).label("count"),
                func.avg(Prospect.score_total).label("avg_score"),
                func.sum(
                    case((Prospect.quality_grade == "A", 1), else_=0)
                ).label("a_count"),
            )
            .where(
                Prospect.discovered_at >= start,
                Prospect.deleted_at.is_(None),
            )
            .group_by(Prospect.source)
            .order_by(desc("count"))
        )
        source_rows = (await db.execute(leads_by_source_q)).all()
        leads_by_source: list[LeadSourceQuality] = []
        for source, count, avg_s, a_count in source_rows:
            a_pct = (a_count or 0) / count * 100 if count > 0 else 0
            leads_by_source.append(
                LeadSourceQuality(
                    source=source or "unknown",
                    count=count,
                    avg_score=float(avg_s) if avg_s is not None else None,
                    grade_a_pct=round(a_pct, 1),
                )
            )

        # Time-to-enrich (discovered → enriched status)
        # We approximate: discovered_at → first analysis_completed activity
        # (a bit fuzzy but works for v1)
        time_to_enrich = await _compute_time_to_enrich(db, start)

        # === B. Outreach ===
        sent_statuses = ["sent", "delivered", "opened", "clicked", "replied"]
        # Total sent
        total_sent_q = select(func.count(Message.id)).where(
            Message.sent_at >= start,
            Message.status.in_(sent_statuses),
        )
        total_messages_sent = (await db.execute(total_sent_q)).scalar() or 0

        # By channel
        outreach_by_channel: list[OutreachChannelStats] = []
        for ch in ("email", "whatsapp", "threads"):
            ch_q = select(
                func.sum(case((Message.status == "sent", 1), else_=0)).label("sent"),
                func.sum(
                    case((Message.status == "delivered", 1), else_=0)
                ).label("delivered"),
                func.sum(
                    case((Message.status == "opened", 1), else_=0)
                ).label("opened"),
                func.sum(
                    case((Message.status == "replied", 1), else_=0)
                ).label("replied"),
                func.sum(
                    case((Message.status == "bounced", 1), else_=0)
                ).label("bounced"),
                func.sum(
                    case((Message.status == "failed", 1), else_=0)
                ).label("failed"),
                func.sum(
                    case((Message.status.in_(
                        ("approved", "sent", "delivered", "opened", "clicked", "replied")
                    ), 1), else_=0)
                ).label("approved_or_better"),
                func.sum(
                    case((Message.status.in_(
                        ("draft", "pending_approval", "rejected", "approved",
                         "sent", "delivered", "opened", "clicked", "replied")
                    ), 1), else_=0)
                ).label("considered"),
            ).where(
                Message.created_at >= start,
                Message.channel == ch,
            )
            row = (await db.execute(ch_q)).one()
            outreach_by_channel.append(
                OutreachChannelStats(
                    channel=ch,
                    sent=int(row.sent or 0),
                    delivered=int(row.delivered or 0),
                    opened=int(row.opened or 0),
                    replied=int(row.replied or 0),
                    bounced=int(row.bounced or 0),
                    failed=int(row.failed or 0),
                    approval_rate=round(
                        (row.approved_or_better or 0)
                        / max(row.considered or 1, 1)
                        * 100,
                        1,
                    ),
                )
            )

        # Approval funnel
        funnel_q = select(
            func.sum(case((Message.status == "draft", 1), else_=0)).label("drafts"),
            func.sum(
                case((Message.status == "pending_approval", 1), else_=0)
            ).label("pending_approval"),
            func.sum(case((Message.status == "approved", 1), else_=0)).label("approved"),
            func.sum(
                case((Message.status == "sent", 1), else_=0)
            ).label("sent"),
            func.sum(
                case((Message.status == "delivered", 1), else_=0)
            ).label("delivered"),
            func.sum(
                case((Message.status == "replied", 1), else_=0)
            ).label("replied"),
        ).where(Message.created_at >= start)
        funnel_row = (await db.execute(funnel_q)).one()
        drafts_count = int(funnel_row.drafts or 0)
        pending_count = int(funnel_row.pending_approval or 0)
        approved_count = int(funnel_row.approved or 0)
        sent_count = int(funnel_row.sent or 0)
        delivered_count = int(funnel_row.delivered or 0)
        replied_count = int(funnel_row.replied or 0)
        approval_funnel = ApprovalFunnelStats(
            drafts=drafts_count,
            pending_approval=pending_count,
            approved=approved_count,
            sent=sent_count,
            delivered=delivered_count,
            replied=replied_count,
            approval_rate=round(
                approved_count / max(pending_count + drafts_count, 1) * 100,
                1,
            ),
        )

        # Daily volume (sparkline)
        daily_volume = await _compute_daily_volume(db, start)

        # === C. Pipeline ===
        pipeline_q = (
            select(Prospect.status, func.count(Prospect.id))
            .where(Prospect.deleted_at.is_(None))
            .group_by(Prospect.status)
        )
        pipeline_rows = (await db.execute(pipeline_q)).all()
        total_in_pipeline = sum(c for _, c in pipeline_rows) or 1
        pipeline_by_stage: list[PipelineStageCount] = []
        for s, c in pipeline_rows:
            pipeline_by_stage.append(
                PipelineStageCount(
                    status=s,
                    count=c,
                    pct=round(c / total_in_pipeline * 100, 1),
                )
            )
        pipeline_by_stage.sort(key=lambda x: x.count, reverse=True)

        total_won = next(
            (c for s, c in pipeline_rows if s == "won"), 0
        )
        total_lost = next(
            (c for s, c in pipeline_rows if s == "lost"), 0
        )
        win_rate = (
            total_won / (total_won + total_lost)
            if (total_won + total_lost) > 0
            else None
        )
        won_q = select(func.avg(Prospect.score_total)).where(
            Prospect.status == "won",
            Prospect.score_total.is_not(None),
        )
        avg_deal_proxy = (await db.execute(won_q)).scalar()

        # === D. Operational ===
        activity_q = select(
            Activity.action, func.count(Activity.id)
        ).where(
            Activity.created_at >= start,
        ).group_by(Activity.action).order_by(desc(func.count(Activity.id)))
        activity_rows = (await db.execute(activity_q)).all()
        recent_24h_q = select(
            Activity.action, func.count(Activity.id)
        ).where(
            Activity.created_at >= end - timedelta(hours=24),
        ).group_by(Activity.action)
        recent_rows = (await db.execute(recent_24h_q)).all()
        recent_map = {a: c for a, c in recent_rows}
        activity_counts: list[ActivityCount] = []
        for action, count in activity_rows:
            activity_counts.append(
                ActivityCount(
                    action=action,
                    count=count,
                    last_24h=recent_map.get(action, 0),
                )
            )

        # LLM usage (estimated from activity log details — LLM calls
        # are logged with details.llm_call = true or hook generation events)
        llm_q = select(func.count(Activity.id)).where(
            Activity.action.in_(
                [
                    "prospect_enriched",
                    "message_sent",
                    "message_generated",
                ]
            ),
            Activity.created_at >= start,
        )
        total_llm_calls = (await db.execute(llm_q)).scalar() or 0
        llm_24h_q = select(func.count(Activity.id)).where(
            Activity.action.in_(
                [
                    "prospect_enriched",
                    "message_sent",
                    "message_generated",
                ]
            ),
            Activity.created_at >= end - timedelta(hours=24),
        )
        last_24h_calls = (await db.execute(llm_24h_q)).scalar() or 0
        llm_usage = LLMUsageStats(
            total_calls=total_llm_calls,
            total_tokens=total_llm_calls * 1200,  # rough estimate per call
            last_24h_calls=last_24h_calls,
        )

        # Celery success rate (from scraping job status)
        celery_q = select(
            func.sum(
                case((ScrapingJob.status == "completed", 1), else_=0)
            ).label("ok"),
            func.count(ScrapingJob.id).label("total"),
        ).where(ScrapingJob.created_at >= start)
        celery_row = (await db.execute(celery_q)).one()
        celery_success = (
            (celery_row.ok or 0) / max(celery_row.total or 1, 1) * 100
            if celery_row.total
            else None
        )

        scraping_success = celery_success  # alias — same data source

        return AnalyticsOverview(
            range=rng,
            total_leads=total_leads,
            leads_by_source=leads_by_source,
            grade_distribution=grade_dist,
            avg_lead_score=float(avg_lead_score) if avg_lead_score else None,
            time_to_enrich=time_to_enrich,
            total_messages_sent=total_messages_sent,
            outreach_by_channel=outreach_by_channel,
            approval_funnel=approval_funnel,
            daily_volume=daily_volume,
            pipeline_by_stage=pipeline_by_stage,
            total_won=total_won,
            win_rate=win_rate,
            avg_deal_size_proxy=float(avg_deal_proxy) if avg_deal_proxy else None,
            activity_counts=activity_counts,
            llm_usage=llm_usage,
            celery_success_rate=celery_success,
            scraping_success_rate=scraping_success,
        )


async def _compute_time_to_enrich(
    db: AsyncSession, start: datetime
) -> TimeToEnrichStats:
    """Approximate: for each prospect, the time from discovered_at
    to their first analysis_completed activity. Returns avg + percentiles.
    """
    # Get all (prospect_id, discovered_at) pairs in range
    p_q = select(
        Prospect.id, Prospect.discovered_at
    ).where(
        Prospect.discovered_at >= start,
        Prospect.deleted_at.is_(None),
        Prospect.discovered_at.is_not(None),
    )
    prospects = (await db.execute(p_q)).all()
    if not prospects:
        return TimeToEnrichStats(avg_hours=None, p50_hours=None, p90_hours=None, n=0)
    # For each, find first analysis_completed activity
    hours_list: list[float] = []
    for pid, disc_at in prospects[:500]:  # cap for perf
        a_q = select(Activity.created_at).where(
            Activity.prospect_id == pid,
            Activity.action == "analysis_completed",
        ).order_by(Activity.created_at).limit(1)
        first = (await db.execute(a_q)).scalar_one_or_none()
        if first and disc_at:
            delta = (first - disc_at).total_seconds() / 3600
            if delta >= 0:
                hours_list.append(delta)
    if not hours_list:
        return TimeToEnrichStats(avg_hours=None, p50_hours=None, p90_hours=None, n=0)
    hours_list.sort()
    n = len(hours_list)
    avg = sum(hours_list) / n
    p50 = hours_list[n // 2]
    p90 = hours_list[int(n * 0.9)] if n > 1 else p50
    return TimeToEnrichStats(
        avg_hours=round(avg, 1),
        p50_hours=round(p50, 1),
        p90_hours=round(p90, 1),
        n=n,
    )


async def _compute_daily_volume(
    db: AsyncSession, start: datetime
) -> list[DailyPipeline]:
    """Prospect pipeline activity per day.

    T8.5+++++++ (telemetry fix): this now tracks
    PROSPECT pipeline events (not outreach message
    events) since the 'Aktivitas pipeline' chart on
    the Dashboard is for the prospect pipeline
    (Klinik/F&B → scored → contacted → won), not the
    outreach message pipeline.

    Source of truth: the 'activities' table (audit log
    of prospect + outreach events).

    4 series mapped to prospect pipeline stages:
    - baru (new): prospect_created action
    - dinilai (scored): analysis_completed +
      prospect_enriched actions (T5 analyst pipeline)
    - dihubungi (contacted): prospect_updated action
      with details.status='contacted'
    - menang (won): prospect_updated action with
      details.status='won'

    Returns 1 entry per day in range, with 0s when
    no activity.
    """
    end = datetime.now(timezone.utc)
    days: list[datetime] = []
    cur = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    while cur <= end:
        days.append(cur)
        cur = cur + timedelta(days=1)

    # Query 1: baru (new) — prospect_created actions
    baru_q = select(
        func.date(Activity.created_at).label("d"),
        func.count(Activity.id).label("count"),
    ).where(
        Activity.created_at >= start,
        Activity.action == "prospect_created",
    ).group_by(func.date(Activity.created_at))
    baru_rows = (await db.execute(baru_q)).all()
    # Query 2: dinilai (scored) — analysis_completed +
    # prospect_enriched actions
    dinilai_q = select(
        func.date(Activity.created_at).label("d"),
        func.count(Activity.id).label("count"),
    ).where(
        Activity.created_at >= start,
        Activity.action.in_(("analysis_completed", "prospect_enriched")),
    ).group_by(func.date(Activity.created_at))
    dinilai_rows = (await db.execute(dinilai_q)).all()
    # Query 3: dihubungi (contacted) — prospect_updated
    # actions where details->>'status' = 'contacted'.
    # Postgres JSONB path: details::text LIKE '%...%' is
    # fragile; use ->> operator.
    dihubungi_q = select(
        func.date(Activity.created_at).label("d"),
        func.count(Activity.id).label("count"),
    ).where(
        Activity.created_at >= start,
        Activity.action == "prospect_updated",
        # Cast to text + LIKE for cross-DB compatibility
        # (SQLite test DB, Postgres prod). For Postgres
        # production, use func.jsonb_extract_path_text.
        func.cast(Activity.details, String).like('%"status": "contacted"%'),
    ).group_by(func.date(Activity.created_at))
    try:
        dihubungi_rows = (await db.execute(dihubungi_q)).all()
    except Exception:
        # Fallback: skip this series (set all to 0)
        dihubungi_rows = []
    # Query 4: menang (won) — prospect_updated actions
    # where details->>'status' = 'won'
    menang_q = select(
        func.date(Activity.created_at).label("d"),
        func.count(Activity.id).label("count"),
    ).where(
        Activity.created_at >= start,
        Activity.action == "prospect_updated",
        func.cast(Activity.details, String).like('%"status": "won"%'),
    ).group_by(func.date(Activity.created_at))
    try:
        menang_rows = (await db.execute(menang_q)).all()
    except Exception:
        menang_rows = []
    # Merge into per-day dict
    by_date: dict[str, dict[str, int]] = {}
    for d, count in baru_rows:
        by_date[str(d)] = {"baru": int(count or 0), "dinilai": 0, "dihubungi": 0, "menang": 0}
    for d, count in dinilai_rows:
        by_date.setdefault(str(d), {"baru": 0, "dinilai": 0, "dihubungi": 0, "menang": 0})
        by_date[str(d)]["dinilai"] = int(count or 0)
    for d, count in dihubungi_rows:
        by_date.setdefault(str(d), {"baru": 0, "dinilai": 0, "dihubungi": 0, "menang": 0})
        by_date[str(d)]["dihubungi"] = int(count or 0)
    for d, count in menang_rows:
        by_date.setdefault(str(d), {"baru": 0, "dinilai": 0, "dihubungi": 0, "menang": 0})
        by_date[str(d)]["menang"] = int(count or 0)
    # Build output for every day in range (fill missing with 0)
    out: list[DailyPipeline] = []
    for d in days:
        v = by_date.get(d.strftime("%Y-%m-%d"), {"baru": 0, "dinilai": 0, "dihubungi": 0, "menang": 0})
        out.append(
            DailyPipeline(
                date=d.strftime("%Y-%m-%d"),
                baru=v["baru"],
                dinilai=v["dinilai"],
                dihubungi=v["dihubungi"],
                menang=v["menang"],
            )
        )
    return out


# --- Sprint 3B carryover: tier distribution for the dashboard ---

# Canonical tier display order (for stable UI rendering)
TIER_DISPLAY_ORDER = ["smb", "mid", "enterprise", "unknown"]

# Colors matched to the TierBadge component in the frontend
TIER_COLORS = {
    "smb": "#10b981",        # emerald-500
    "mid": "#f59e0b",        # amber-500
    "enterprise": "#8b5cf6", # violet-500
    "unknown": "#71717a",    # zinc-500
}


async def get_tier_distribution(
    days: int = 30,
) -> dict[str, int]:
    """Tier distribution for the dashboard.

    Per the Sprint 3B tier-classification design, this returns
    the count of prospects per tier (smb/mid/enterprise/unknown)
    in the lookback period. The 'unclassified' bucket covers
    prospects with tier IS NULL (pre-Sprint 3B or not yet
    auto-classified).

    Used by the Dashboard's TierDonut widget.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        # Count per tier, including NULL as 'unclassified'
        rows = (
            await db.execute(
                select(
                    Prospect.tier,
                    func.count(Prospect.id),
                ).where(
                    Prospect.discovered_at >= start,
                    Prospect.deleted_at.is_(None),
                ).group_by(Prospect.tier)
            )
        ).all()
        # Initialize the canonical 5 buckets (smb/mid/enterprise/unknown/unclassified)
        dist: dict[str, int] = {tier: 0 for tier in TIER_DISPLAY_ORDER}
        dist["unclassified"] = 0
        for tier, count in rows:
            if tier in dist:
                dist[tier] = count
            else:
                # NULL tier → unclassified bucket
                dist["unclassified"] = count
        dist["total"] = sum(dist.values())
    return dist
