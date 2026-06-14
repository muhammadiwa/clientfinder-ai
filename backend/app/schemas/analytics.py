"""
Pydantic schemas for T7 Analytics
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Lead Gen KPIs ---

class LeadSourceQuality(BaseModel):
    """Avg score per source — for A. Source quality KPI."""

    source: str
    count: int
    avg_score: float | None
    grade_a_pct: float  # % of leads from this source that are A-grade


class GradeDistribution(BaseModel):
    """Count of prospects by quality_grade (A/B/C/D)."""

    A: int = 0
    B: int = 0
    C: int = 0
    D: int = 0
    unscored: int = 0


class TimeToEnrichStats(BaseModel):
    """Avg + P50 + P90 from discovered_at to enriched."""

    avg_hours: float | None
    p50_hours: float | None
    p90_hours: float | None
    n: int


# --- Outreach KPIs ---

class OutreachChannelStats(BaseModel):
    """Per-channel message counts."""

    channel: str
    sent: int
    delivered: int
    opened: int
    replied: int
    bounced: int
    failed: int
    approval_rate: float  # approved / (drafts + pending)


class DailyVolume(BaseModel):
    """Volume per day for the last N days (sparkline data)."""

    date: str  # YYYY-MM-DD
    sent: int
    replied: int


class ApprovalFunnelStats(BaseModel):
    """Drafts → Pending → Approved → Sent → Replied."""

    drafts: int
    pending_approval: int
    approved: int
    sent: int
    delivered: int
    replied: int
    approval_rate: float  # approved / total pending


# --- Pipeline KPIs ---

class PipelineStageCount(BaseModel):
    """Count of prospects in each pipeline stage."""

    status: str
    count: int
    pct: float  # % of total prospects


class ConversionRate(BaseModel):
    """Stage-to-stage conversion rate."""

    from_status: str
    to_status: str
    count: int
    rate: float  # count_from / count_to


# --- Operational KPIs ---

class ActivityCount(BaseModel):
    """Count of activity log entries by action type."""

    action: str
    count: int
    last_24h: int


class LLMUsageStats(BaseModel):
    """LLM token usage (estimated from activity log details)."""

    total_calls: int
    total_tokens: int  # estimated
    last_24h_calls: int


# --- Top-level Analytics Response ---

class AnalyticsRange(BaseModel):
    """Common date range used in analytics responses."""

    days: int = Field(30, ge=1, le=365, description="Lookback period in days")
    start: datetime
    end: datetime


class AnalyticsOverview(BaseModel):
    """All KPIs in one response — drives the analytics dashboard."""

    range: AnalyticsRange

    # Lead Gen (A)
    total_leads: int
    leads_by_source: list[LeadSourceQuality]
    grade_distribution: GradeDistribution
    avg_lead_score: float | None
    time_to_enrich: TimeToEnrichStats

    # Outreach (B)
    total_messages_sent: int
    outreach_by_channel: list[OutreachChannelStats]
    approval_funnel: ApprovalFunnelStats
    daily_volume: list[DailyVolume]  # last 30 days for sparkline

    # Pipeline (C)
    pipeline_by_stage: list[PipelineStageCount]
    total_won: int
    win_rate: float | None  # won / (won + lost)
    avg_deal_size_proxy: float | None  # avg score_total for won

    # Operational (D)
    activity_counts: list[ActivityCount]
    llm_usage: LLMUsageStats
    celery_success_rate: float | None
    scraping_success_rate: float | None
